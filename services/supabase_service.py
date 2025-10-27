import os
from supabase import create_client, Client
from typing import Optional, Dict, Any
from dotenv import load_dotenv

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
            "system_prompt": get_default_system_prompt(),
        }
    except Exception as e:
        print(f"Error fetching settings from Supabase: {e}")
        # Fallback to environment variables
        return {
            "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
            "elevenlabs_api_key": os.getenv("ELEVENLABS_API_KEY", ""),
            "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "elevenlabs_model": os.getenv("ELEVENLABS_MODEL_ID", "eleven_turbo_v2_5"),
            "system_prompt": get_default_system_prompt(),
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

##Section 3: further relaxation. Choose any of common techniques to do so. Leave some extra time/silence at the end of this section to allow the user to relax further in silence. End this section with the following tag: <break>

##Section 4: visualisation. Introduce the visualisation technique, tie it to the disease, symptom and additional instruction of the user and to section 1 of the meditation and then start. Choose any of common visualisation techniques to do so.

##Section 5: end of meditation."""

