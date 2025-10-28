from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our modules
from services.openai_service import generate_meditation, split_meditation_into_chapters
from services.elevenlabs_service import text_to_speech, generate_music
from services.audio_processor import (
    combine_chapters_with_silence,
    overlay_audio,
    get_audio_duration,
    get_ffmpeg_status,
)
from services.session_store import (
    create_session,
    update_session,
    get_session,
    SessionStatus,
)
from services.supabase_service import (
    get_meditation_by_session_id,
    get_settings,
    update_settings,
    save_meditation,
    get_all_meditations,
    get_meditation_by_id,
    delete_meditation,
)
from utils.helpers import get_temp_dir, ensure_dir_exists
import uuid
import asyncio
from pathlib import Path
import shutil
from services.audio_processor import get_audio_duration

app = FastAPI(title="Meditation API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
        "https://healign.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class AuthRequest(BaseModel):
    password: str
    role: str  # 'user' or 'admin'


class GenerateRequest(BaseModel):
    disease: str
    symptom: str
    additionalInstructions: Optional[str] = ""


class AuthResponse(BaseModel):
    success: bool
    role: Optional[str] = None
    message: Optional[str] = None


class GenerateResponse(BaseModel):
    sessionId: str


class StatusResponse(BaseModel):
    status: str
    currentStep: int
    audioPath: Optional[str] = None
    error: Optional[str] = None


class FFmpegStatusResponse(BaseModel):
    ffmpeg_installed: bool
    ffmpeg_version: Optional[str] = None
    ffprobe_installed: bool
    ffprobe_version: Optional[str] = None
    status: str
    message: Optional[str] = None


class AdminSettingsRequest(BaseModel):
    openai_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    elevenlabs_model: Optional[str] = None
    elevenlabs_voice_id: Optional[str] = None
    elevenlabs_speed: Optional[float] = None
    system_prompt: Optional[str] = None
    chapter_count: Optional[int] = None
    silence_duration_seconds: Optional[int] = None
    user_password: Optional[str] = None
    admin_password: Optional[str] = None


class AdminSettingsResponse(BaseModel):
    openai_api_key: str
    elevenlabs_api_key: str
    openai_model: str
    elevenlabs_model: str
    elevenlabs_voice_id: str
    elevenlabs_speed: float
    system_prompt: str
    chapter_count: int
    silence_duration_seconds: int
    user_password: str
    admin_password: str


class VoiceTestRequest(BaseModel):
    text: str
    model_id: Optional[str] = None
    voice_id: Optional[str] = None
    speed: Optional[float] = None


# Background processing function
async def process_meditation_background(
    session_id: str, disease: str, symptom: str, additional_instructions: str
):
    """Process meditation generation in the background"""
    temp_dir = get_temp_dir()
    session_dir = Path(temp_dir) / session_id

    try:
        # Get settings from Supabase
        settings = await get_settings()
        
         # Create session directory
        ensure_dir_exists(str(session_dir))

        # Step 1: Generate meditation text with AI
        update_session(session_id, current_step=0, status=SessionStatus.PROCESSING)
        
        # Get chapter count from settings (defaults to 3)
        chapter_count = settings.get("chapter_count", 3)
        
        meditation_text = await generate_meditation(
            disease=disease,
            symptom=symptom,
            additional_instructions=additional_instructions,
            api_key=settings.get("openai_api_key"),
            model=settings.get("openai_model"),
            system_prompt_template=settings.get("system_prompt"),
            chapter_count=chapter_count,
            break_count=chapter_count - 1,
        )

        # Split into chapters using the configured chapter count
        chapters = split_meditation_into_chapters(meditation_text, chapter_count=chapter_count)

        # Step 2: Convert chapters to speech
        update_session(session_id, current_step=1)
        chapter_paths = []

        for i, chapter in enumerate(chapters):
            chapter_path = str(session_dir / f"chapter{i + 1}.mp3")
            await text_to_speech(
                chapter,
                chapter_path,
                api_key=settings.get("elevenlabs_api_key"),
                model_id=settings.get("elevenlabs_model"),
                voice_id=settings.get("elevenlabs_voice_id"),
                speed=settings.get("elevenlabs_speed", 0.7),
            )
            chapter_paths.append(chapter_path)

        # Step 3: Combine chapters with silence
        update_session(session_id, current_step=2)
        combined_path = str(session_dir / "combined.mp3")
        
        # Get silence duration from settings (defaults to 45 seconds)
        silence_duration = settings.get("silence_duration_seconds", 45)
        
        await combine_chapters_with_silence(
            chapter_paths, silence_duration, combined_path
        )

        # Step 4: Overlay with static background music
        update_session(session_id, current_step=3)
        
        # Path to your static music file (update this path to your actual music file location)
        static_music_path = os.path.join(os.path.dirname(__file__), "assets", "meditation_music.mp3")
        
        # Verify the static music file exists
        if not os.path.exists(static_music_path):
            raise FileNotFoundError(f"Static music file not found at: {static_music_path}")
        
        final_path = str(session_dir / "final.mp3")
        await overlay_audio(combined_path, static_music_path, final_path)

        # Get audio duration
        try:
            duration_seconds = int(await get_audio_duration(final_path))
        except:
            duration_seconds = None

        # Save meditation to database and upload audio to storage
        try:
            saved_meditation_response = await save_meditation(
                session_id=session_id,
                disease=disease,
                symptom=symptom,
                additional_instructions=additional_instructions,
                meditation_text=meditation_text,
                audio_path=final_path,
                duration_seconds=duration_seconds,
            )
            print(f"Meditation saved successfully: {session_id}")
            
            # Delete final file after successful upload to storage
            try:
                os.unlink(final_path)
                print(f"Deleted local final file: {final_path}")
            except Exception as delete_error:
                print(f"Error deleting final file: {delete_error}")
        except Exception as save_error:
            print(f"Error saving meditation: {save_error}")
            # Continue even if save fails

        # Mark as completed
        update_session(
            session_id,
            status=SessionStatus.COMPLETED,
            current_step=4,
            audio_path=saved_meditation_response.get("audio_url"),
        )

        # Clean up intermediate files
        for chapter_path in chapter_paths:
            try:
                os.unlink(chapter_path)
            except:
                pass
        try:
            os.unlink(combined_path)
        except:
            pass

    except Exception as e:
        print(f"Error processing meditation: {e}")
        update_session(
            session_id,
            status=SessionStatus.ERROR,
            error=str(e) or "An error occurred during processing",
        )

        # Clean up on error
        if session_dir.exists():
            shutil.rmtree(session_dir, ignore_errors=True)


# API Routes
@app.get("/")
async def root():
    return {"message": "Meditation API is running"}


@app.post("/api/auth", response_model=AuthResponse)
async def auth(request: AuthRequest):
    """Authenticate user or admin with password"""
    # Get passwords from settings (with fallback to environment variables)
    settings = await get_settings()
    user_password = settings.get("user_password", os.getenv("USER_PASSWORD", "user"))
    admin_password = settings.get("admin_password", os.getenv("ADMIN_PASSWORD", "admin"))
    
    # Validate role
    if request.role not in ["user", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'user' or 'admin'")
    
    # Check password based on role
    if request.role == "user":
        if request.password == user_password:
            return AuthResponse(success=True, role="user")
        else:
            raise HTTPException(status_code=401, detail="Invalid user password")
    elif request.role == "admin":
        if request.password == admin_password:
            return AuthResponse(success=True, role="admin")
        else:
            raise HTTPException(status_code=401, detail="Invalid admin password")


@app.post("/api/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest, background_tasks: BackgroundTasks):
    """Start meditation generation process"""
    if not request.disease or not request.symptom:
        raise HTTPException(status_code=400, detail="Disease and symptom are required")

    # Create a unique session ID
    session_id = str(uuid.uuid4())

    # Create session
    create_session(session_id)

    # Start background processing
    background_tasks.add_task(
        process_meditation_background,
        session_id,
        request.disease,
        request.symptom,
        request.additionalInstructions or "",
    )

    return GenerateResponse(sessionId=session_id)


@app.get("/api/status", response_model=StatusResponse)
async def status(sessionId: str):
    """Get the status of a meditation generation session"""
    if not sessionId:
        raise HTTPException(status_code=400, detail="Session ID is required")

    session = get_session(sessionId)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return StatusResponse(
        status=session.status.value,
        currentStep=session.current_step,
        audioPath=session.audio_path,
        error=session.error,
    )


@app.get("/api/audio")
async def audio(sessionId: str):
    """Serve the generated audio file"""
    if not sessionId:
        raise HTTPException(status_code=400, detail="Session ID is required")

    meditation = await get_meditation_by_session_id(sessionId)  

    if not meditation:
        raise HTTPException(status_code=404, detail="Audio not ready or session not found")

    audio_url = meditation.get("audio_url")

    if not audio_url:
        raise HTTPException(status_code=404, detail="Audio file not found")

    # Redirect to the Supabase URL instead of trying to serve it as a local file
    return RedirectResponse(url=audio_url, status_code=302)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/api/ffmpeg-status", response_model=FFmpegStatusResponse)
async def ffmpeg_status():
    """Get FFmpeg and FFprobe installation status and version information"""
    status = await get_ffmpeg_status()
    return FFmpegStatusResponse(**status)


@app.get("/api/admin/settings", response_model=AdminSettingsResponse)
async def get_admin_settings(password: str = ""):
    """Get admin settings - requires admin password"""
    admin_password = os.getenv("ADMIN_PASSWORD", "admin")
    if password != admin_password:
        raise HTTPException(status_code=401, detail="Admin access required")
    try:
        settings = await get_settings()
        return AdminSettingsResponse(
            openai_api_key=settings.get("openai_api_key", ""),
            elevenlabs_api_key=settings.get("elevenlabs_api_key", ""),
            openai_model=settings.get("openai_model", "gpt-4o-mini"),
            elevenlabs_model=settings.get("elevenlabs_model", "eleven_turbo_v2_5"),
            elevenlabs_voice_id=settings.get("elevenlabs_voice_id", "BpjGufoPiobT79j2vtj4"),
            elevenlabs_speed=settings.get("elevenlabs_speed", 0.7),
            system_prompt=settings.get("system_prompt", ""),
            chapter_count=settings.get("chapter_count", 3),
            silence_duration_seconds=settings.get("silence_duration_seconds", 45),
            user_password=settings.get("user_password", os.getenv("USER_PASSWORD", "user")),
            admin_password=settings.get("admin_password", os.getenv("ADMIN_PASSWORD", "admin")),
        )
    except Exception as e:
        print(f"Error fetching admin settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/admin/settings", response_model=AdminSettingsResponse)
async def update_admin_settings(request: AdminSettingsRequest, password: str = ""):
    """Update admin settings - requires admin password"""
    admin_password = os.getenv("ADMIN_PASSWORD", "admin")
    if password != admin_password:
        raise HTTPException(status_code=401, detail="Admin access required")
    try:
        # Only update fields that are provided
        settings_to_update = {}
        if request.openai_api_key is not None:
            settings_to_update["openai_api_key"] = request.openai_api_key
        if request.elevenlabs_api_key is not None:
            settings_to_update["elevenlabs_api_key"] = request.elevenlabs_api_key
        if request.openai_model is not None:
            settings_to_update["openai_model"] = request.openai_model
        if request.elevenlabs_model is not None:
            settings_to_update["elevenlabs_model"] = request.elevenlabs_model
        if request.elevenlabs_voice_id is not None:
            settings_to_update["elevenlabs_voice_id"] = request.elevenlabs_voice_id
        if request.elevenlabs_speed is not None:
            # Validate speed range
            if request.elevenlabs_speed < 0.7 or request.elevenlabs_speed > 1.2:
                raise HTTPException(status_code=400, detail="Speed must be between 0.7 and 1.2")
            settings_to_update["elevenlabs_speed"] = request.elevenlabs_speed
        if request.system_prompt is not None:
            settings_to_update["system_prompt"] = request.system_prompt
        if request.chapter_count is not None:
            settings_to_update["chapter_count"] = request.chapter_count
        if request.silence_duration_seconds is not None:
            settings_to_update["silence_duration_seconds"] = request.silence_duration_seconds
        if request.user_password is not None:
            settings_to_update["user_password"] = request.user_password
        if request.admin_password is not None:
            settings_to_update["admin_password"] = request.admin_password
        
        updated_settings = await update_settings(settings_to_update)
        return AdminSettingsResponse(
            openai_api_key=updated_settings.get("openai_api_key", ""),
            elevenlabs_api_key=updated_settings.get("elevenlabs_api_key", ""),
            openai_model=updated_settings.get("openai_model", "gpt-4o-mini"),
            elevenlabs_model=updated_settings.get("elevenlabs_model", "eleven_turbo_v2_5"),
            elevenlabs_voice_id=updated_settings.get("elevenlabs_voice_id", "BpjGufoPiobT79j2vtj4"),
            elevenlabs_speed=updated_settings.get("elevenlabs_speed", 0.7),
            system_prompt=updated_settings.get("system_prompt", ""),
            chapter_count=updated_settings.get("chapter_count", 3),
            silence_duration_seconds=updated_settings.get("silence_duration_seconds", 45),
            user_password=updated_settings.get("user_password", os.getenv("USER_PASSWORD", "user")),
            admin_password=updated_settings.get("admin_password", os.getenv("ADMIN_PASSWORD", "admin")),
        )
    except Exception as e:
        print(f"Error updating admin settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/meditations")
async def list_meditations(limit: Optional[int] = 100, offset: int = 0, password: str = ""):
    """Get all meditations (admin endpoint)"""
    admin_password = os.getenv("ADMIN_PASSWORD", "admin")
    if password != admin_password:
        raise HTTPException(status_code=401, detail="Admin access required")
    try:
        meditations = await get_all_meditations(limit=limit, offset=offset)
        return {"meditations": meditations}
    except Exception as e:
        print(f"Error fetching meditations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/meditations/{meditation_id}")
async def get_meditation_details(meditation_id: str, password: str = ""):
    """Get meditation details by ID (admin endpoint)"""
    admin_password = os.getenv("ADMIN_PASSWORD", "admin")
    if password != admin_password:
        raise HTTPException(status_code=401, detail="Admin access required")
    try:
        meditation = await get_meditation_by_id(meditation_id)
        if not meditation:
            raise HTTPException(status_code=404, detail="Meditation not found")
        return meditation
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching meditation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/admin/meditations/{meditation_id}")
async def delete_meditation_endpoint(meditation_id: str, password: str = ""):
    """Delete meditation (admin endpoint)"""
    admin_password = os.getenv("ADMIN_PASSWORD", "admin")
    if password != admin_password:
        raise HTTPException(status_code=401, detail="Admin access required")
    try:
        success = await delete_meditation(meditation_id)
        if not success:
            raise HTTPException(status_code=404, detail="Meditation not found")
        return {"success": True, "message": "Meditation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting meditation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/settings/test-voice")
async def test_voice(request: VoiceTestRequest, password: str = ""):
    """Test ElevenLabs voice with current settings (admin endpoint)"""
    admin_password = os.getenv("ADMIN_PASSWORD", "admin")
    if password != admin_password:
        raise HTTPException(status_code=401, detail="Admin access required")
    
    try:
        # Get settings from database
        settings = await get_settings()
        
        # Use provided values or fall back to settings
        model_id = request.model_id or settings.get("elevenlabs_model", "eleven_turbo_v2_5")
        voice_id = request.voice_id or settings.get("elevenlabs_voice_id", "BpjGufoPiobT79j2vtj4")
        speed = request.speed if request.speed is not None else settings.get("elevenlabs_speed", 0.7)
        api_key = settings.get("elevenlabs_api_key")
        
        if not api_key:
            raise HTTPException(status_code=400, detail="ElevenLabs API key not configured")
        
        # Generate test audio directly in memory (no temp file)
        from services.elevenlabs_service import text_to_speech_bytes
        from fastapi.responses import Response
        
        audio_bytes = await text_to_speech_bytes(
            text=request.text,
            api_key=api_key,
            model_id=model_id,
            voice_id=voice_id,
            speed=speed,
        )
        
        # Return audio directly from memory
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=voice_test.mp3"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error testing voice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Ensure temp directory exists
    temp_dir = get_temp_dir()
    ensure_dir_exists(temp_dir)

    # Run the application
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

