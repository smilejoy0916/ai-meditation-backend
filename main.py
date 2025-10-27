from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
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
from services.supabase_service import get_settings, update_settings
from utils.helpers import get_temp_dir, ensure_dir_exists
import uuid
import asyncio
from pathlib import Path
import shutil

app = FastAPI(title="Meditation API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class AuthRequest(BaseModel):
    password: str


class GenerateRequest(BaseModel):
    disease: str
    symptom: str
    additionalInstructions: Optional[str] = ""


class AuthResponse(BaseModel):
    success: bool
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
    system_prompt: Optional[str] = None


class AdminSettingsResponse(BaseModel):
    openai_api_key: str
    elevenlabs_api_key: str
    openai_model: str
    elevenlabs_model: str
    system_prompt: str


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
        meditation_text = await generate_meditation(
            disease=disease,
            symptom=symptom,
            additional_instructions=additional_instructions,
            api_key=settings.get("openai_api_key"),
            model=settings.get("openai_model"),
            system_prompt_template=settings.get("system_prompt"),
        )

        # Split into chapters
        chapters = split_meditation_into_chapters(meditation_text)

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
            )
            chapter_paths.append(chapter_path)

        # Step 3: Combine chapters with silence
        update_session(session_id, current_step=2)
        combined_path = str(session_dir / "combined.mp3")
        await combine_chapters_with_silence(
            chapter_paths, 60, combined_path
        )  # 60 seconds of silence

        # Step 4: Overlay with static background music
        update_session(session_id, current_step=3)
        
        # Path to your static music file (update this path to your actual music file location)
        static_music_path = os.path.join(os.path.dirname(__file__), "assets", "meditation_music.mp3")
        
        # Verify the static music file exists
        if not os.path.exists(static_music_path):
            raise FileNotFoundError(f"Static music file not found at: {static_music_path}")
        
        final_path = str(session_dir / "final.mp3")
        await overlay_audio(combined_path, static_music_path, final_path)

        # Mark as completed
        update_session(
            session_id,
            status=SessionStatus.COMPLETED,
            current_step=4,
            audio_path=final_path,
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
    """Authenticate user with password"""
    correct_password = os.getenv("APP_PASSWORD", "meditation")

    if request.password == correct_password:
        return AuthResponse(success=True)
    else:
        raise HTTPException(status_code=401, detail="Invalid password")


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

    session = get_session(sessionId)

    if not session or session.status != SessionStatus.COMPLETED:
        raise HTTPException(
            status_code=404, detail="Audio not ready or session not found"
        )

    audio_path = session.audio_path

    if not audio_path or not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "public, max-age=3600",
        },
    )


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
async def get_admin_settings():
    """Get admin settings"""
    try:
        settings = await get_settings()
        return AdminSettingsResponse(
            openai_api_key=settings.get("openai_api_key", ""),
            elevenlabs_api_key=settings.get("elevenlabs_api_key", ""),
            openai_model=settings.get("openai_model", "gpt-4o-mini"),
            elevenlabs_model=settings.get("elevenlabs_model", "eleven_turbo_v2_5"),
            system_prompt=settings.get("system_prompt", ""),
        )
    except Exception as e:
        print(f"Error fetching admin settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/admin/settings", response_model=AdminSettingsResponse)
async def update_admin_settings(request: AdminSettingsRequest):
    """Update admin settings"""
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
        if request.system_prompt is not None:
            settings_to_update["system_prompt"] = request.system_prompt
        
        updated_settings = await update_settings(settings_to_update)
        return AdminSettingsResponse(
            openai_api_key=updated_settings.get("openai_api_key", ""),
            elevenlabs_api_key=updated_settings.get("elevenlabs_api_key", ""),
            openai_model=updated_settings.get("openai_model", "gpt-4o-mini"),
            elevenlabs_model=updated_settings.get("elevenlabs_model", "eleven_turbo_v2_5"),
            system_prompt=updated_settings.get("system_prompt", ""),
        )
    except Exception as e:
        print(f"Error updating admin settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Ensure temp directory exists
    temp_dir = get_temp_dir()
    ensure_dir_exists(temp_dir)

    # Run the application
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

