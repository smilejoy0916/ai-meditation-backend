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


# Background processing function
async def process_meditation_background(
    session_id: str, disease: str, symptom: str, additional_instructions: str
):
    """Process meditation generation in the background"""
    temp_dir = get_temp_dir()
    session_dir = Path(temp_dir) / session_id

    try:
        # Create session directory
        ensure_dir_exists(str(session_dir))

        # Step 1: Generate meditation text with AI
        update_session(session_id, current_step=0, status=SessionStatus.PROCESSING)
        meditation_text = await generate_meditation(
            disease=disease, symptom=symptom, additional_instructions=additional_instructions
        )

        # Split into chapters
        chapters = split_meditation_into_chapters(meditation_text)

        # Step 2: Convert chapters to speech
        update_session(session_id, current_step=1)
        chapter_paths = []

        for i, chapter in enumerate(chapters):
            chapter_path = str(session_dir / f"chapter{i + 1}.mp3")
            await text_to_speech(chapter, chapter_path)
            chapter_paths.append(chapter_path)

        # Step 3: Combine chapters with silence
        update_session(session_id, current_step=2)
        combined_path = str(session_dir / "combined.mp3")
        await combine_chapters_with_silence(
            chapter_paths, 60, combined_path
        )  # 60 seconds of silence

        # Get duration for music generation
        meditation_duration = await get_audio_duration(combined_path)

        # Step 4: Generate and overlay meditation music
        update_session(session_id, current_step=3)
        music_path = str(session_dir / "music.mp3")

        # Generate music for the meditation duration (in milliseconds)
        # Add extra 30 seconds to ensure it's long enough
        await generate_music(int((meditation_duration + 30) * 1000), music_path)

        # Step 5: Overlay music with meditation
        update_session(session_id, current_step=4)
        final_path = str(session_dir / "final.mp3")
        await overlay_audio(combined_path, music_path, final_path)

        # Mark as completed
        update_session(
            session_id,
            status=SessionStatus.COMPLETED,
            current_step=5,
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
            os.unlink(music_path)
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


if __name__ == "__main__":
    # Ensure temp directory exists
    temp_dir = get_temp_dir()
    ensure_dir_exists(temp_dir)

    # Run the application
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

