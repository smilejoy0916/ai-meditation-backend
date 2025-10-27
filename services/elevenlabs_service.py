import os
import aiohttp
from pathlib import Path
from typing import Optional


ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "BpjGufoPiobT79j2vtj4")


async def text_to_speech(text: str, output_path: str, api_key: Optional[str] = None, model_id: Optional[str] = None) -> None:
    """Convert text to speech using ElevenLabs API"""
    # Use provided API key or fall back to environment variable
    elevenlabs_api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
    # Use provided model ID or fall back to environment variable
    elevenlabs_model_id = model_id or os.getenv("ELEVENLABS_MODEL_ID", "eleven_turbo_v2_5")
    
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}?output_format=mp3_44100_128"
        headers = {
            "xi-api-key": elevenlabs_api_key,
            "Content-Type": "application/json",
        }
        data = {
            "text": text,
            "model_id": elevenlabs_model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.6,
                "speed": 0.7,
            },
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"ElevenLabs API error: {response.status}")

                # Ensure directory exists
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)

                # Write audio to file
                audio_data = await response.read()
                with open(output_path, "wb") as f:
                    f.write(audio_data)

    except Exception as e:
        print(f"Error converting text to speech: {e}")
        raise Exception("Failed to convert text to speech")


async def generate_music(music_length_ms: int, output_path: str, api_key: Optional[str] = None) -> None:
    """Generate meditation music using ElevenLabs API"""
    # Use provided API key or fall back to environment variable
    elevenlabs_api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
    
    try:
        url = "https://api.elevenlabs.io/v1/music?output_format=mp3_44100_128"
        headers = {
            "xi-api-key": elevenlabs_api_key,
            "Content-Type": "application/json",
        }
        data = {
            "prompt": "Create peaceful meditation music with gentle ambient sounds, soft piano, and calming nature sounds. Serene, tranquil, and relaxing atmosphere.",
            "music_length_ms": 60000,
            "model_id": "music_v1",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"ElevenLabs API error: {response.status}")

                # Ensure directory exists
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)

                # Write audio to file
                audio_data = await response.read()
                with open(output_path, "wb") as f:
                    f.write(audio_data)

    except Exception as e:
        print(f"Error generating music: {e}")
        raise Exception("Failed to generate meditation music")

