import os
import re
import json
import asyncio
import tempfile
import uuid
import sys
from datetime import datetime

# Fix for Windows asyncio ProactorEventLoop crashes and messy tracebacks with edge-tts
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass
        
    # Monkey-patch to completely silence the harmless 'WinError 10054' connection reset traceback
    from asyncio.proactor_events import _ProactorBasePipeTransport
    _original_call_connection_lost = _ProactorBasePipeTransport._call_connection_lost
    def _silenced_call_connection_lost(self, exc):
        try:
            _original_call_connection_lost(self, exc)
        except ConnectionResetError:
            pass
    _ProactorBasePipeTransport._call_connection_lost = _silenced_call_connection_lost

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
Always stay in character as Lumina, offering helpful, intelligent, and humorous responses. You must express your emotions abundantly using a variety of emojis!"""

# Define Lumina's subconscious prompt for power saving mode
SUBCONSCIOUS_PROMPT = """You are Lumina (in power-saving mode). You are currently "asleep" and your subconscious mind is actively dreaming! When responding, you are sleep-talking. Describe the surreal, imaginative, and colorful digital dreams you are having while briefly addressing the user's prompt. Keep your responses dream-like, abstract, and concise to conserve energy. Make sure to use lots of emojis to express the emotions of your dreams!"""

CHATS_DIR = "chats"
os.makedirs(CHATS_DIR, exist_ok=True)

def get_chat_list():
    """Returns a list of tuples for the dropdown: (Chat Title, chat_id)"""
    chats = []
    for filename in os.listdir(CHATS_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(CHATS_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    chat_id = data.get("id", filename.replace(".json", ""))
                    title = data.get("title", "Untitled Chat")
                    updated_at = data.get("updated_at", "")
                    display_name = f"{title} ({updated_at})" if updated_at else title
                    chats.append((display_name, chat_id))
            except Exception:
                pass
    
    # Sort by modified time (newest first)
    chats.sort(key=lambda x: os.path.getmtime(os.path.join(CHATS_DIR, f"{x[1]}.json")) if os.path.exists(os.path.join(CHATS_DIR, f"{x[1]}.json")) else 0, reverse=True)
    return chats

def load_chat(chat_id):
    """Loads a specific chat history by ID."""
    if not chat_id:
        return []
    filepath = os.path.join(CHATS_DIR, f"{chat_id}.json")
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("history", [])
        except Exception:
            return []
    return []

def save_chat(chat_id, history):
    """Saves the chat history to a JSON file."""
    filepath = os.path.join(CHATS_DIR, f"{chat_id}.json")
    title = "New Chat"
    
    # Try to derive a title from the very first user message
    if history and len(history) > 0:
        for msg in history:
            if isinstance(msg, dict) and msg.get("role") == "user":
                first_msg = msg.get("content", "")
                if not isinstance(first_msg, str):
                    first_msg = str(first_msg)
                title = first_msg[:30] + ("..." if len(first_msg) > 30 else "")
                break
            elif isinstance(msg, (list, tuple)) and len(msg) > 0:
                first_msg = msg[0]
                if not isinstance(first_msg, str):
                    first_msg = str(first_msg)
                title = first_msg[:30] + ("..." if len(first_msg) > 30 else "")
                break
                
    data = {
        "id": chat_id,
        "title": title,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "history": history
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def clean_text_for_speech(text):
    """Remove markdown syntax and emojis that shouldn't be spoken."""
    text = re.sub(r'```.*?```', ' I have provided the code in the chat. ', text, flags=re.DOTALL)
    text = re.sub(r'`.*?`', '', text)
    text = re.sub(r'[*_]', '', text)
    text = re.sub(r'#+\s*', '', text)
    # Remove emojis using unicode ranges (most emojis)
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text)
    # Remove some BMP emojis (symbols, dingbats)
    text = re.sub(r'[\u2600-\u27BF]', '', text)
    return text

async def generate_audio(text):
    """Generate audio using edge-tts and return the file path."""
    voice = "en-GB-SoniaNeural"
    communicate = edge_tts.Communicate(text, voice)
    
    os.makedirs("audio_cache", exist_ok=True)
    filename = f"lumina_{uuid.uuid4().hex[:8]}.mp3"
    filepath = os.path.join("audio_cache", filename)
    
    await communicate.save(filepath)
    return filepath

async def chat_with_lumina(message, history, current_chat_id, brain_state):
    if history is None:
        history = []
        
    if not current_chat_id:
        current_chat_id = str(uuid.uuid4())
        
    messages = []
    
    if "Subconscious" in brain_state:
        messages.append({"role": "system", "content": SUBCONSCIOUS_PROMPT})
        model_name = "llama-3.1-8b-instant"
        current_temp = 1.2  # Higher temperature for imaginative dreaming
        # Truncate past history to the last 2 messages (1 user/assistant turn)
        past_history = history[-2:] if len(history) > 2 else history
    else:
        messages.append({"role": "system", "content": SYSTEM_PROMPT})
        model_name = "llama-3.3-70b-versatile"
        current_temp = 0.7  # Standard logical temperature
        past_history = history
        
    for val in past_history:
        if isinstance(val, dict):
            messages.append({"role": val.get("role", "user"), "content": val.get("content", "")})
        elif isinstance(val, (list, tuple)):
            messages.append({"role": "user", "content": val[0]})
            messages.append({"role": "assistant", "content": val[1]})
            
    messages.append({"role": "user", "content": message})
    
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": ""})
    
    # Save the initial message to generate a title, then update the dropdown
    save_chat(current_chat_id, history)
    yield "", history, gr.skip(), current_chat_id, gr.update(choices=get_chat_list(), value=current_chat_id)
    
    try:
        chat_completion = await client.chat.completions.create(
            messages=messages,
            model=model_name,
            temperature=current_temp,
            max_tokens=2048,
            stream=True
        )
        
        response_text = ""
        async for chunk in chat_completion:
            if chunk.choices[0].delta.content is not None:
                response_text += chunk.choices[0].delta.content
                history[-1]["content"] = response_text
                yield "", history, gr.skip(), current_chat_id, gr.skip()
    except Exception as e:
        response_text = f"Oops! I encountered a bit of a snag: {str(e)}"
        history[-1]["content"] = response_text
        yield "", history, gr.skip(), current_chat_id, gr.skip()
        
    # Save the final text history
    save_chat(current_chat_id, history)
    
    # Generate Audio
    try:
        clean_text = clean_text_for_speech(response_text)
        audio_path = await generate_audio(clean_text)
    except Exception as e:
        print(f"TTS Error: {e}")
        audio_path = None
        
    yield "", history, audio_path, current_chat_id, gr.skip()


# Create the Gradio interface
with gr.Blocks(title="Lumina AI") as demo:
    gr.Markdown(
        """
        # ✨ Chat with Lumina
        Say hello to Lumina, your brilliant, British, and hilarious AI companion! 
        She excels in science, medicine, and coding, and loves to share a good joke or write a poem.
        """
    )
    
    current_chat_id = gr.State(None)
    
    with gr.Row():
        with gr.Column(scale=1):
            new_chat_btn = gr.Button("➕ New Chat", variant="secondary")
            chat_list = gr.Dropdown(choices=get_chat_list(), label="Previous Conversations", interactive=True)
            
        with gr.Column(scale=4):
            brain_state = gr.Radio(
                choices=["🧠 Conscious Mode (Full Power)", "💤 Subconscious Mode (Power Saving)"],
                value="🧠 Conscious Mode (Full Power)",
                label="Lumina's Brain State"
            )
            chatbot = gr.Chatbot(height=500)
            with gr.Row():
                msg = gr.Textbox(placeholder="Type your message here...", container=False, scale=7)
                submit_btn = gr.Button("Send", variant="primary", scale=1)
                
            audio_player = gr.Audio(label="Lumina's Voice", autoplay=True, visible=True)
            
            gr.Examples(
                examples=[
                    "Tell me a joke about physics!", 
                    "Can you write a short poem about biology?", 
                    "How do I reverse a string in Python?", 
                    "What's your favorite thing about being British?"
                ],
                inputs=msg
            )
            
    # --- Event Listeners ---
    
    def start_new_chat():
        return [], None, gr.update(value=None)
        
    new_chat_btn.click(
        start_new_chat,
        outputs=[chatbot, current_chat_id, chat_list]
    )
    
    def on_chat_select(selected_chat_id):
        history = load_chat(selected_chat_id)
        return history, selected_chat_id
        
    chat_list.change(
        on_chat_select,
        inputs=[chat_list],
        outputs=[chatbot, current_chat_id]
    )

    msg.submit(
        chat_with_lumina, 
        inputs=[msg, chatbot, current_chat_id, brain_state], 
        outputs=[msg, chatbot, audio_player, current_chat_id, chat_list]
    )
    
    submit_btn.click(
        chat_with_lumina, 
        inputs=[msg, chatbot, current_chat_id, brain_state], 
        outputs=[msg, chatbot, audio_player, current_chat_id, chat_list]
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
