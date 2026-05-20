import os
import re
import uuid
import edge_tts

async def clean_text_for_speech(text):
    """Remove markdown syntax and emojis that shouldn't be spoken."""
    # Remove image generation tag but replace with something natural
    text = re.sub(r'\[IMAGE_PROMPT:.*?\]', ' Here is the image you requested! ', text)
    # Remove markdown image tags if any snuck through
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'```.*?```', ' I have provided the code in the chat. ', text, flags=re.DOTALL)
    text = re.sub(r'`.*?`', '', text)
    text = re.sub(r'[*_]', '', text)
    text = re.sub(r'#+\s*', '', text)
    # Remove emojis using unicode ranges (most emojis)
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    # Remove some BMP emojis (symbols, dingbats)
    text = re.sub(r'[\u2600-\u27BF]', '', text)
    # Remove citation brackets like [1], [2][3] to prevent fabricated refs
    text = re.sub(r'\[\d+(?:\]\s*\[\d+)*\]', '', text)
    # Remove raw URLs that might hallucinate fake sources
    text = re.sub(r'https?://\S+', '', text)
    # Remove arXiv references
    text = re.sub(r'\b(?:arXiv|arxiv)\s*:\s*\S+', '', text)
    return text

async def generate_audio(text):
    """Generate audio using edge-tts and return the file path."""
    voice = "en-GB-SoniaNeural"
    communicate = edge_tts.Communicate(text, voice)
    
    os.makedirs("audio_cache", exist_ok=True)
    filename = f"lumina_{uuid.uuid4().hex[:8]}.mp3"
    filepath = os.path.join("audio_cache", filename)
    
    try:
        await communicate.save(filepath)
        return filepath
    except Exception as e:
        print(f"[TTS] Audio generation failed: {e}")
        return None
