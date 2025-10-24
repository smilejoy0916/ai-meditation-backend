import subprocess
import os
import math
from pathlib import Path
from typing import List, Dict, Optional
import json
import re


async def get_audio_duration(file_path: str) -> float:
    """Get the duration of an audio file in seconds using ffprobe"""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            file_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        duration = float(data["format"]["duration"])
        return duration
    except Exception as e:
        print(f"Error getting audio duration: {e}")
        return 0.0


async def create_silence(duration_seconds: int, output_path: str) -> None:
    """Create a silent audio file using ffmpeg"""
    try:
        cmd = [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=channel_layout=stereo:sample_rate=44100",
            "-t",
            str(duration_seconds),
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            "-y",  # Overwrite output file
            output_path,
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        # Try alternative method
        print(f"Error creating silence with lavfi: {e}, trying alternative method")
        try:
            cmd = [
                "ffmpeg",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency=1000:duration={duration_seconds}",
                "-af",
                "volume=0",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "128k",
                "-ac",
                "2",
                "-y",
                output_path,
            ]
            subprocess.run(cmd, check=True, capture_output=True)
        except Exception as e2:
            print(f"Error creating silence alternative: {e2}")
            raise Exception(
                "FFmpeg lavfi format not available. Please ensure FFmpeg is properly installed."
            )


async def concatenate_audio(input_files: List[str], output_path: str) -> None:
    """Concatenate multiple audio files using ffmpeg"""
    # Create a temporary file list for ffmpeg concat
    file_list_path = str(Path(output_path).parent / "filelist.txt")
    
    try:
        # Write file list
        with open(file_list_path, "w") as f:
            for file in input_files:
                # Use absolute paths and escape special characters
                abs_path = os.path.abspath(file).replace("\\", "/")
                f.write(f"file '{abs_path}'\n")

        # Run ffmpeg
        cmd = [
            "ffmpeg",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            file_list_path,
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            "-y",
            output_path,
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    finally:
        # Clean up file list
        try:
            os.unlink(file_list_path)
        except:
            pass


async def overlay_audio(
    main_audio_path: str, background_music_path: str, output_path: str
) -> None:
    """Overlay background music on main audio using ffmpeg"""
    try:
        # Get durations
        main_duration = await get_audio_duration(main_audio_path)
        music_duration = await get_audio_duration(background_music_path)

        if music_duration < main_duration:
            # Loop the music if it's shorter than the meditation
            loop_count = math.ceil(main_duration / music_duration)

            cmd = [
                "ffmpeg",
                "-stream_loop",
                str(loop_count - 1),
                "-i",
                background_music_path,
                "-i",
                main_audio_path,
                "-filter_complex",
                "[0:a]volume=0.3[music];[1:a][music]amix=inputs=2:duration=first:dropout_transition=2",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "128k",
                "-y",
                output_path,
            ]
            subprocess.run(cmd, check=True, capture_output=True)
        else:
            # Trim the music if it's longer than the meditation
            cmd = [
                "ffmpeg",
                "-i",
                main_audio_path,
                "-i",
                background_music_path,
                "-filter_complex",
                f"[1:a]atrim=0:{main_duration},volume=0.3[music];[0:a][music]amix=inputs=2:duration=first:dropout_transition=2",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "128k",
                "-y",
                output_path,
            ]
            subprocess.run(cmd, check=True, capture_output=True)

    except Exception as e:
        print(f"Error overlaying audio: {e}")
        raise


async def combine_chapters_with_silence(
    chapter_paths: List[str], silence_duration: int, output_path: str
) -> None:
    """Combine audio chapters with silence between them"""
    temp_dir = Path(chapter_paths[0]).parent
    silence_path = str(temp_dir / "silence.mp3")

    try:
        # Create silence audio
        await create_silence(silence_duration, silence_path)

        # Interleave chapters with silence
        files_to_concat = []
        for i, chapter_path in enumerate(chapter_paths):
            files_to_concat.append(chapter_path)
            if i < len(chapter_paths) - 1:
                files_to_concat.append(silence_path)

        # Concatenate all files
        await concatenate_audio(files_to_concat, output_path)

    finally:
        # Clean up silence file
        try:
            os.unlink(silence_path)
        except:
            pass


async def get_ffmpeg_status() -> Dict[str, any]:
    """Check FFmpeg and FFprobe installation and get version information"""
    status = {
        "ffmpeg_installed": False,
        "ffmpeg_version": None,
        "ffprobe_installed": False,
        "ffprobe_version": None,
        "status": "error",
        "message": None
    }
    
    try:
        # Check FFmpeg
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                status["ffmpeg_installed"] = True
                # Extract version from output
                version_match = re.search(r'ffmpeg version ([\S]+)', result.stdout)
                if version_match:
                    status["ffmpeg_version"] = version_match.group(1)
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            status["message"] = f"FFmpeg not found: {str(e)}"
        
        # Check FFprobe
        try:
            result = subprocess.run(
                ["ffprobe", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                status["ffprobe_installed"] = True
                # Extract version from output
                version_match = re.search(r'ffprobe version ([\S]+)', result.stdout)
                if version_match:
                    status["ffprobe_version"] = version_match.group(1)
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            if not status["message"]:
                status["message"] = f"FFprobe not found: {str(e)}"
            else:
                status["message"] += f" | FFprobe not found: {str(e)}"
        
        # Determine overall status
        if status["ffmpeg_installed"] and status["ffprobe_installed"]:
            status["status"] = "healthy"
            status["message"] = "FFmpeg and FFprobe are properly installed"
        elif status["ffmpeg_installed"] or status["ffprobe_installed"]:
            status["status"] = "partial"
            if not status["message"]:
                status["message"] = "Only one of FFmpeg/FFprobe is installed"
        else:
            status["status"] = "error"
            if not status["message"]:
                status["message"] = "FFmpeg and FFprobe are not installed"
                
    except Exception as e:
        status["status"] = "error"
        status["message"] = f"Error checking FFmpeg status: {str(e)}"
    
    return status

