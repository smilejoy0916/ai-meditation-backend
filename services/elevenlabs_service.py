import os
import aiohttp
from pathlib import Path


ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel voice


async def text_to_speech(text: str, output_path: str) -> None:
    """Convert text to speech using ElevenLabs API"""
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        }
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
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


async def generate_music(music_length_ms: int, output_path: str) -> None:
    """Generate meditation music using ElevenLabs API"""
    try:
        url = "https://api.elevenlabs.io/v1/music?output_format=mp3_44100_128"
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        }
        data = {
            "prompt": "Create peaceful meditation music with gentle ambient sounds, soft piano, and calming nature sounds. Serene, tranquil, and relaxing atmosphere.",
            "music_length_ms": 60000,
            "model_id": "music_v1",
        }

        print(ELEVENLABS_API_KEY)

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

