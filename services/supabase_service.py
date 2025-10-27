import os
from supabase import create_client, Client
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import base64
from datetime import datetime

load_dotenv()

# Lazy initialization
supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Get or create Supabase client"""
    global supabase_client
    if supabase_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        
        supabase_client = create_client(supabase_url, supabase_key)
    return supabase_client


async def get_settings() -> Dict[str, Any]:
    """Get admin settings from Supabase"""
    try:
        client = get_supabase_client()
        response = client.table("admin_settings").select("*").limit(1).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        
        # Return default settings if none exist
        return {
            "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
            "elevenlabs_api_key": os.getenv("ELEVENLABS_API_KEY", ""),
            "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "elevenlabs_model": os.getenv("ELEVENLABS_MODEL_ID", "eleven_turbo_v2_5"),
            "elevenlabs_voice_id": os.getenv("ELEVENLABS_VOICE_ID", "BpjGufoPiobT79j2vtj4"),
            "system_prompt": get_default_system_prompt(),
            "chapter_count": 3,
            "silence_duration_seconds": 45,
            "user_password": os.getenv("USER_PASSWORD", "user"),
            "admin_password": os.getenv("ADMIN_PASSWORD", "admin"),
        }
    except Exception as e:
        print(f"Error fetching settings from Supabase: {e}")
        # Fallback to environment variables
        return {
            "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
            "elevenlabs_api_key": os.getenv("ELEVENLABS_API_KEY", ""),
            "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "elevenlabs_model": os.getenv("ELEVENLABS_MODEL_ID", "eleven_turbo_v2_5"),
            "elevenlabs_voice_id": os.getenv("ELEVENLABS_VOICE_ID", "BpjGufoPiobT79j2vtj4"),
            "system_prompt": get_default_system_prompt(),
            "chapter_count": 3,
            "silence_duration_seconds": 45,
            "user_password": os.getenv("USER_PASSWORD", "user"),
            "admin_password": os.getenv("ADMIN_PASSWORD", "admin"),
        }


async def update_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Update admin settings in Supabase"""
    try:
        client = get_supabase_client()
        
        # Check if settings exist
        existing = client.table("admin_settings").select("id").limit(1).execute()
        
        if existing.data and len(existing.data) > 0:
            # Update existing settings
            response = client.table("admin_settings").update(settings).eq("id", existing.data[0]["id"]).execute()
        else:
            # Insert new settings
            response = client.table("admin_settings").insert(settings).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        
        raise Exception("Failed to update settings")
    except Exception as e:
        print(f"Error updating settings in Supabase: {e}")
        raise Exception(f"Failed to update settings: {str(e)}")


def get_default_system_prompt() -> str:
    """Get the default system prompt for meditation generation"""
    return """#Instruction: write a 10-minute meditation following the below structure. In that meditation, include elevenlabs tags such as [inhale], [exhale], [pause] or [whisper]. To not make it too fast paced, make sure to include a [pause 2 seconds] tag after each sentence. Using "..." also slows the pace down. Take the user inputs into account in the relevant parts of the meditation, as described. Avoid using "now" too much to progress the meditation forward.

#User input:
##Disease: {disease}
##Symptom: {symptom}
##Additional instruction: {additional_instructions}

#Output: output only the meditation itself with the relevant tags, without saying anything else or without including section titles

#Structure of the meditation with instructions for each section:
##Section 1: Introduction to the topic. The general topic is quantum healing. Select a topic at random addressed by Deepak Chopra in his Quantum Healing book without mentioning that book in the meditation. Tie in this general topic with the disease, symptom and additional instruction given by the user above. This part should be suitable for a meditation, yet scientific enough - without being too specific (e.g. there is a proven mind-body connection, but don't talk about peptides or other detailed processes, just give examples relevant to the disease and symptom)

##Section 2: start of the meditation, settle the user. Choose any of common techniques to do so (e.g. focus on breath, senses, body, etc.). Leave some extra time/silence at the end of this section to allow the user to relax further in silence. End this section with the following tag: <break>

##Section 3+: Progressive relaxation sections. Create additional relaxation sections as needed. Each section should use different relaxation techniques (e.g., body scan, breath work, progressive muscle relaxation, sensory awareness, etc.). Each of these sections should end with the <break> tag. The number of these sections can vary based on the chapter count.

##Final Section: visualisation and closing. Introduce the visualisation technique, tie it to the disease, symptom and additional instruction of the user and to section 1 of the meditation and then start. Choose any of common visualisation techniques to do so. Complete with a gentle closing to end the meditation.

Note: Use the <break> tag to separate chapters. The meditation will be split at these break points to insert periods of silence for deeper relaxation."""


async def save_meditation(
    session_id: str,
    disease: str,
    symptom: str,
    additional_instructions: str,
    meditation_text: str,
    audio_path: str,
    duration_seconds: Optional[int] = None,
) -> Dict[str, Any]:
    """Save meditation to database and upload audio to Supabase Storage"""
    try:
        client = get_supabase_client()
        
        # Upload audio to Supabase Storage
        audio_url = await upload_audio_to_storage(session_id, audio_path)
        
        # Prepare meditation data
        meditation_data = {
            "session_id": session_id,
            "disease": disease,
            "symptom": symptom,
            "additional_instructions": additional_instructions or None,
            "meditation_text": meditation_text,
            "audio_url": audio_url,
            "duration_seconds": duration_seconds,
            "status": "completed",
        }
        
        # Insert meditation into database
        response = client.table("meditations").insert(meditation_data).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        
        raise Exception("Failed to save meditation")
    except Exception as e:
        print(f"Error saving meditation: {e}")
        raise Exception(f"Failed to save meditation: {str(e)}")


async def upload_audio_to_storage(session_id: str, audio_path: str) -> str:
    """Upload audio file to Supabase Storage"""
    try:
        client = get_supabase_client()
        
        # Read audio file
        with open(audio_path, 'rb') as f:
            audio_data = f.read()
        
        # Define storage path
        bucket_name = "meditation-audio"
        file_name = f"{session_id}.mp3"
        storage_path = f"meditations/{file_name}"
        
        # Ensure bucket exists
        try:
            buckets = client.storage.list_buckets()
            bucket_exists = any(bucket.name == bucket_name for bucket in buckets)
            
            if not bucket_exists:
                # Create bucket if it doesn't exist
                client.storage.create_bucket(
                    bucket_name,
                    options={"public": True, "file_size_limit": 104857600}  # 100MB limit
                )
        except Exception as e:
            print(f"Bucket creation check error (may already exist): {e}")
        
        # Upload file
        upload_response = client.storage.from_(bucket_name).upload(
            storage_path,
            audio_data,
            file_options={"content-type": "audio/mpeg"}
        )
        
        # Get public URL
        url_response = client.storage.from_(bucket_name).get_public_url(storage_path)
        
        return url_response
    except Exception as e:
        print(f"Error uploading audio to storage: {e}")
        raise Exception(f"Failed to upload audio: {str(e)}")


async def get_all_meditations(limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
    """Get all meditations from database"""
    try:
        client = get_supabase_client()
        
        query = client.table("meditations").select("*").order("created_at", desc=True)
        
        if limit is not None:
            query = query.limit(limit).offset(offset)
        
        response = query.execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"Error fetching meditations: {e}")
        return []


async def get_meditation_by_id(meditation_id: str) -> Optional[Dict[str, Any]]:
    """Get meditation by ID"""
    try:
        client = get_supabase_client()
        response = client.table("meditations").select("*").eq("id", meditation_id).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        
        return None
    except Exception as e:
        print(f"Error fetching meditation: {e}")
        return None


async def get_meditation_by_session_id(session_id: str) -> Optional[Dict[str, Any]]:
    """Get meditation by session ID"""
    try:
        client = get_supabase_client()
        response = client.table("meditations").select("*").eq("session_id", session_id).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        
        return None
    except Exception as e:
        print(f"Error fetching meditation: {e}")
        return None


async def delete_meditation(meditation_id: str) -> bool:
    """Delete meditation from database and storage"""
    try:
        client = get_supabase_client()
        
        # Get meditation first
        meditation = await get_meditation_by_id(meditation_id)
        if not meditation:
            return False
        
        # Delete audio from storage
        if meditation.get("audio_url"):
            try:
                # Extract file path from URL
                bucket_name = "meditation-audio"
                file_name = meditation["session_id"] + ".mp3"
                storage_path = f"meditations/{file_name}"
                client.storage.from_(bucket_name).remove([storage_path])
            except Exception as e:
                print(f"Error deleting audio from storage: {e}")
        
        # Delete from database
        response = client.table("meditations").delete().eq("id", meditation_id).execute()
        
        return True
    except Exception as e:
        print(f"Error deleting meditation: {e}")
        return False

