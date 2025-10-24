import os
from pathlib import Path


def get_temp_dir() -> str:
    """
    Determine temp directory based on environment.
    In serverless environments (like AWS Lambda), use /tmp
    In local development or Docker, use ./temp
    """
    # Check if we're in a serverless environment
    is_serverless = (
        os.getenv("VERCEL")
        or os.getenv("AWS_LAMBDA_FUNCTION_NAME")
        or os.getenv("IS_SERVERLESS")
    )

    if is_serverless:
        return "/tmp"

    # For local development or Docker
    return str(Path.cwd() / "temp")


def ensure_dir_exists(directory: str) -> None:
    """Ensure a directory exists, create it if it doesn't"""
    Path(directory).mkdir(parents=True, exist_ok=True)

