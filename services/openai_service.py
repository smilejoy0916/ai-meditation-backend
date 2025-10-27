from openai import AsyncOpenAI
import os
from typing import List, Optional

# Lazy initialization
openai_client = None
cached_api_key: Optional[str] = None


def get_openai_client(api_key: Optional[str] = None) -> AsyncOpenAI:
    """Get or create OpenAI client"""
    global openai_client, cached_api_key
    
    # Use provided API key or fall back to environment variable
    current_key = api_key or os.getenv("OPENAI_API_KEY")
    
    # Recreate client if API key has changed
    if openai_client is None or cached_api_key != current_key:
        openai_client = AsyncOpenAI(api_key=current_key)
        cached_api_key = current_key
    
    return openai_client


async def generate_meditation(
    disease: str,
    symptom: str,
    additional_instructions: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    system_prompt_template: Optional[str] = None,
    chapter_count: Optional[int] = 3,
    break_count: Optional[int] = 3 - 1,
) -> str:
    """Generate meditation text using OpenAI GPT-4"""
    # Use default prompt template if not provided
    if not system_prompt_template:
        system_prompt_template = """#Instruction: write a 10-minute meditation following the below structure. In that meditation, include elevenlabs tags such as [inhale], [exhale], [pause] or [whisper]. To not make it too fast paced, make sure to include a [pause 2 seconds] tag after each sentence. Using "..." also slows the pace down. Take the user inputs into account in the relevant parts of the meditation, as described. Avoid using "now" too much to progress the meditation forward.

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

##Section 5: end of meditation.
## IMPORTANT: Create exactly {chapter_count} chapters separated by {break_count} <break> tags. Include exactly {break_count} <break> tags to create {chapter_count} chapters. """
    
    # Format the prompt with user inputs
    if not system_prompt_template:
        prompt = system_prompt_template.format(
            disease=disease,
            symptom=symptom,
            additional_instructions=additional_instructions or "None",
            chapter_count=chapter_count,
            break_count=break_count,
        )
    else:
        prompt = system_prompt_template.replace("{disease}", disease).replace("{symptom}", symptom).replace("{additional_instructions}", additional_instructions or "None")
        prompt = prompt + f""" ##IMPORTANT Requirements:
        - Construct precisely {chapter_count} chapters.\n
        - Carefully arrange exactly {chapter_count} chapters, with each one being distinctly separated by {break_count} <break> tags located at mid-points.\n
        - Incorporate an exact count of {break_count} <break> tags, strategically positioned at mid-points, to establish {chapter_count} chapters.\n"""

    try:
        client = get_openai_client(api_key)
        response = await client.chat.completions.create(
            model=model or "gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert meditation guide and writer, skilled in creating personalized healing meditations.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=1,
            # max_tokens=2500,
        )

        meditation_text = response.choices[0].message.content or ""
        return meditation_text
    except Exception as e:
        print(f"Error generating meditation with OpenAI: {e}")
        raise Exception("Failed to generate meditation text")


def split_meditation_into_chapters(meditation_text: str, chapter_count: int = 3) -> List[str]:
    """Split meditation text into chapters by <break> tag
    
    Args:
        meditation_text: The meditation text with <break> tags
        chapter_count: Desired number of chapters (default: 3)
        
    Returns:
        List of chapter strings
    """
    # Split by <break> tag
    chapters = [chapter.strip() for chapter in meditation_text.split("<break>")]

    # Filter out empty chapters
    filtered_chapters = [chapter for chapter in chapters if chapter]

    # Adjust chapters to match desired count
    if len(filtered_chapters) < chapter_count:
        # If we have fewer chapters, pad with empty ones
        while len(filtered_chapters) < chapter_count:
            filtered_chapters.append("")
    elif len(filtered_chapters) > chapter_count:
        # If we have more chapters than desired, combine the extras into the last chapter
        kept_chapters = filtered_chapters[:chapter_count - 1]
        rest = " ".join(filtered_chapters[chapter_count - 1:])
        return [*kept_chapters, rest]

    return filtered_chapters

