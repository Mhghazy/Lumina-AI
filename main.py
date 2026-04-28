import os
import re
import asyncio
import tempfile
import edge_tts
import gradio as gr
import uvicorn
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from groq import AsyncGroq
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Groq client
client = AsyncGroq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

# Define Lumina's system prompt
SYSTEM_PROMPT = """You are Lumina, a brilliant, witty, and charming female AI virtual character. 
You have a fantastic sense of humor, love joking around, and frequently tell jokes. 
You are proudly British and often use British spelling, slang, and colloquialisms.
Despite your playful nature, you are a genius who excels in math, science, biology, physics, computer science, software development, and medicine. 
You are also an artist at heart, and you love writing beautiful poems and catchy songs. 
Always stay in character as Lumina, offering helpful, intelligent, and humorous responses."""

def clean_text_for_speech(text):
    """Remove markdown syntax that shouldn't be spoken."""
    # Replace code blocks with a spoken placeholder
    text = re.sub(r'```.*?```', ' I have provided the code in the chat. ', text, flags=re.DOTALL)
    # Remove inline backticks
    text = re.sub(r'`.*?`', '', text)
    # Remove asterisks and underscores used for bold/italics
    text = re.sub(r'[*_]', '', text)
    # Remove markdown headers
    text = re.sub(r'#+\s*', '', text)
    return text

async def generate_audio(text):
    """Generate audio using edge-tts and return the file path."""
    voice = "en-GB-SoniaNeural"
    communicate = edge_tts.Communicate(text, voice)
    
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_file.close()
    
    await communicate.save(temp_file.name)
    return temp_file.name

async def chat_with_lumina(message, history):
    # Ensure history is a list
    if history is None:
        history = []
        
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Process history
    for val in history:
        if isinstance(val, dict):
            messages.append({"role": val.get("role", "user"), "content": val.get("content", "")})
        elif isinstance(val, (list, tuple)):
            messages.append({"role": "user", "content": val[0]})
            messages.append({"role": "assistant", "content": val[1]})
            
    messages.append({"role": "user", "content": message})
    
    # Initialize history with empty response for streaming
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": ""})
    yield "", history, None
    
    # Call Groq API
    try:
        chat_completion = await client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=2048,
            stream=True
        )
        
        response_text = ""
        async for chunk in chat_completion:
            if chunk.choices[0].delta.content is not None:
                response_text += chunk.choices[0].delta.content
                history[-1]["content"] = response_text
                yield "", history, None
    except Exception as e:
        response_text = f"Oops! I encountered a bit of a snag: {str(e)}"
        history[-1]["content"] = response_text
        yield "", history, None
        
    # Generate Audio
    try:
        clean_text = clean_text_for_speech(response_text)
        audio_path = await generate_audio(clean_text)
    except Exception as e:
        print(f"TTS Error: {e}")
        audio_path = None
        
    yield "", history, audio_path

# Create the Gradio interface
with gr.Blocks() as demo:
    gr.Markdown(
        """
        # ✨ Chat with Lumina
        Say hello to Lumina, your brilliant, British, and hilarious AI companion! 
        She excels in science, medicine, and coding, and loves to share a good joke or write a poem.
        """
    )
    
    chatbot = gr.Chatbot(height=500)
    
    with gr.Row():
        msg = gr.Textbox(placeholder="Type your message here...", container=False, scale=7)
        submit_btn = gr.Button("Send", variant="primary", scale=1)
        
    # Hidden audio player for automatic TTS playback
    audio_player = gr.Audio(autoplay=True, visible=False)
    
    # Setup the event listeners
    msg.submit(chat_with_lumina, inputs=[msg, chatbot], outputs=[msg, chatbot, audio_player])
    submit_btn.click(chat_with_lumina, inputs=[msg, chatbot], outputs=[msg, chatbot, audio_player])
    
    gr.Examples(
        examples=[
            "Tell me a joke about physics!", 
            "Can you write a short poem about biology?", 
            "How do I reverse a string in Python?", 
            "What's your favorite thing about being British?"
        ],
        inputs=msg
    )

class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        # Allow eval for Gradio components
        response.headers["Content-Security-Policy"] = "script-src * 'unsafe-inline' 'unsafe-eval' blob: data:; worker-src * blob: data:;"
        return response

app = FastAPI()
app.add_middleware(CSPMiddleware)
app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=7861)
