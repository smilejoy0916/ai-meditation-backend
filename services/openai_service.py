from openai import AsyncOpenAI
import os
from typing import List

# Lazy initialization
openai_client = None


def get_openai_client() -> AsyncOpenAI:
    """Get or create OpenAI client"""
    global openai_client
    if openai_client is None:
        openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return openai_client


async def generate_meditation(
    disease: str, symptom: str, additional_instructions: str
) -> str:
    """Generate meditation text using OpenAI GPT-4"""
    prompt = f"""#Instruction: write a 10-minute meditation following the below structure. In that meditation, include elevenlabs tags such as [inhale], [exhale], [pause] or [whisper]. To not make it too fast paced, make sure to include a [pause 2 seconds] tag after each sentence. Using "..." also slows the pace down. Take the user inputs into account in the relevant parts of the meditation, as described. Avoid using "now" too much to progress the meditation forward.

#User input:
##Disease: {disease}
##Symptom: {symptom}
##Additional instruction: {additional_instructions or "None"}

#Output: output only the meditation itself with the relevant tags, without saying anything else or without including section titles

#Structure of the meditation with instructions for each section:
##Section 1: Introduction to the topic. The general topic is quantum healing. Select a topic at random addressed by Deepak Chopra in his Quantum Healing book without mentioning that book in the meditation. Tie in this general topic with the disease, symptom and additional instruction given by the user above.

##Section 2: start of the meditation, settle the user. Choose any of common techniques to do so. Leave some extra time/silence at the end of this section to allow the user to relax further in silence. End this section with the following tag: <break>

##Section 3: further relaxation. Choose any of common techniques to do so. Leave some extra time/silence at the end of this section to allow the user to relax further in silence. End this section with the following tag: <break>

##Section 4: visualisation. Introduce the visualisation technique, tie it to the disease, symptom and additional instruction of the user and then start. Choose any of common visualisation techniques to do so.

##Section 5: end of meditation."""

    try:
        client = get_openai_client()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
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
            temperature=0.8,
            max_tokens=2500,
        )

        meditation_text = response.choices[0].message.content or ""
        return meditation_text
    except Exception as e:
        print(f"Error generating meditation with OpenAI: {e}")
        raise Exception("Failed to generate meditation text")


def split_meditation_into_chapters(meditation_text: str) -> List[str]:
    """Split meditation text into chapters by <break> tag"""
    # Split by <break> tag
    chapters = [chapter.strip() for chapter in meditation_text.split("<break>")]

    # Filter out empty chapters
    filtered_chapters = [chapter for chapter in chapters if chapter]

    # Ensure we have exactly 3 chapters
    if len(filtered_chapters) < 3:
        # If we have fewer chapters, pad with empty ones
        while len(filtered_chapters) < 3:
            filtered_chapters.append("")
    elif len(filtered_chapters) > 3:
        # If we have more than 3, combine the extras into the last chapter
        first_two = filtered_chapters[:2]
        rest = " ".join(filtered_chapters[2:])
        return [*first_two, rest]

    return filtered_chapters

