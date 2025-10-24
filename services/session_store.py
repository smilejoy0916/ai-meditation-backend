from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, Dict
from dataclasses import dataclass, field
import threading


class SessionStatus(Enum):
    """Session status enumeration"""
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class SessionData:
    """Session data model"""
    status: SessionStatus
    current_step: int
    created_at: datetime = field(default_factory=datetime.now)
    audio_path: Optional[str] = None
    error: Optional[str] = None


# Simple in-memory session store
# In production, you might want to use Redis or a database
sessions: Dict[str, SessionData] = {}
session_lock = threading.Lock()


def create_session(session_id: str) -> SessionData:
    """Create a new session"""
    with session_lock:
        session_data = SessionData(
            status=SessionStatus.PROCESSING,
            current_step=0,
        )
        sessions[session_id] = session_data
        return session_data


def update_session(
    session_id: str,
    status: Optional[SessionStatus] = None,
    current_step: Optional[int] = None,
    audio_path: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    """Update an existing session"""
    with session_lock:
        session = sessions.get(session_id)
        if session:
            if status is not None:
                session.status = status
            if current_step is not None:
                session.current_step = current_step
            if audio_path is not None:
                session.audio_path = audio_path
            if error is not None:
                session.error = error


def get_session(session_id: str) -> Optional[SessionData]:
    """Get a session by ID"""
    with session_lock:
        return sessions.get(session_id)


def delete_session(session_id: str) -> None:
    """Delete a session"""
    with session_lock:
        if session_id in sessions:
            del sessions[session_id]


def cleanup_old_sessions():
    """Clean up sessions older than 1 hour"""
    with session_lock:
        one_hour_ago = datetime.now() - timedelta(hours=1)
        sessions_to_delete = [
            session_id
            for session_id, session in sessions.items()
            if session.created_at < one_hour_ago
        ]
        for session_id in sessions_to_delete:
            del sessions[session_id]


# Start a background thread to clean up old sessions
def start_cleanup_thread():
    """Start background cleanup thread"""
    import time

    def cleanup_loop():
        while True:
            time.sleep(15 * 60)  # Run every 15 minutes
            cleanup_old_sessions()

    thread = threading.Thread(target=cleanup_loop, daemon=True)
    thread.start()


# Start cleanup thread when module is imported
start_cleanup_thread()

