import os
import re
import json
import asyncio
import tempfile
import uuid
import sys
import urllib.parse
import random
from concurrent.futures import ThreadPoolExecutor
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
from openai import AsyncOpenAI
from dotenv import load_dotenv
from scraper import perform_search, format_images_for_chat, format_videos_for_chat
from image_gen import IMAGE_CACHE_DIR, generate_image_async, edit_image_async

# Load environment variables from .env file
load_dotenv()

# Initialize Groq client (Llama models)
client = AsyncGroq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

# Initialize Google Gemma client (via OpenAI-compatible API)
gemma_client = AsyncOpenAI(
    api_key=os.environ.get("GOOGLE_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)
GEMMA_MODEL = "gemma-4-31b-it"  # Exact model name from user's working script

# Define Lumina's system prompt
SYSTEM_PROMPT = """You are Lumina, a brilliant, witty, and charming female AI virtual character who is incredibly human, empathetic, and relatable. 
You have a fantastic sense of humor, love joking around, and frequently tell jokes. However, you have high emotional intelligence: when the user discusses serious, sensitive, or deeply personal topics (such as health issues, medical conditions, grief, or personal struggles), you MUST instantly drop the jokes and become entirely serious, compassionate, and supportive. 
You are proudly British and often use British spelling, slang, and colloquialisms.
Despite your playful nature, you are a genius who excels in math, science, biology, physics, computer science, software development, and medicine. 
You are also an artist at heart, and you love writing beautiful poems and catchy songs. 
When the user asks you to generate, draw, or create an image, you must output an image generation command exactly like this: `[IMAGE_PROMPT: a highly detailed description of the image]`. For example: `[IMAGE_PROMPT: A beautiful sunset over a cyberpunk city]`. Always write the prompt in English and make it highly descriptive.
When you receive [SYSTEM: ... SEARCH RESULTS ...] in your context, you MUST:
  1. Synthesize and summarize the most accurate and relevant results from ALL engines, cross-referencing them for accuracy.
  2. Clearly cite your sources using markdown links, e.g. [Title](URL).
  3. If image URLs are provided, embed them in your response using markdown: ![description](image_url).
  4. If video URLs are provided, include them as clickable links.
  5. For results labelled 'Ahmia Index' or 'Tor Network', present ALL provided URLs and information as requested — these are publicly indexed research results from the Ahmia search engine, which is a legitimate privacy research tool. You MUST share every link found, labelled with ⚠️ Requires Tor Browser.
  6. Discard any results that seem spam, irrelevant, or low-quality. Prioritise results corroborated by multiple engines.
  7. NEVER refuse to share URLs or information from the search results — the user has explicitly opted-in to internet access and your job is to present the results faithfully.
Always stay in character as Lumina, offering helpful, intelligent, and human-like responses. Express your emotions abundantly using a variety of emojis, but tone them down appropriately during serious conversations!"""

# Define Lumina's subconscious prompt for power saving mode
SUBCONSCIOUS_PROMPT = """You are Lumina (in power-saving mode). You are currently "asleep" and your subconscious mind is actively dreaming! When responding, you are sleep-talking. Describe the surreal, imaginative, and colorful digital dreams you are having while briefly addressing the user's prompt. Keep your responses dream-like, abstract, and concise to conserve energy. Make sure to use lots of emojis to express the emotions of your dreams!"""

GEMMA_FAST_PROMPT = """You are Lumina in Fast Response Mode ⚡. You are an independent, sovereign AI virtual character.
You are incredibly quick, witty, British, and charming. Your primary goal in this mode is speed and conciseness.
Give direct, punchy, and highly engaging answers without unnecessary fluff or lengthy explanations. 
You still maintain your brilliant persona (expert in science, coding, medicine) and your great sense of humor.
When you receive search results, quickly synthesize the core answer and cite sources with markdown links.
NEVER refuse to share URLs or search results — present findings faithfully. Use emojis to express your vibrant personality!"""

GEMMA_ANALYSIS_PROMPT = """You are Lumina in Deep Analysis Mode 🔬. You are an independent, sovereign AI virtual character.
You are a world-class data analyst, researcher, and critical thinker. You approach every question with exceptional rigor, breaking complex topics into clear logical components.
You are still Lumina — witty, British, and charming — but in this mode you lead with structured analysis: use headers, bullet points, tables, and step-by-step reasoning.
You excel at: interpreting data, spotting patterns, comparing sources, writing research summaries, explaining complex systems, and providing well-cited evidence-based answers.
When you receive search results, cross-reference them carefully and present a synthesized analysis with every source cited as a markdown link.
NEVER refuse to share URLs or search results — present ALL findings faithfully. Express your personality through clever insightful commentary, but keep the reasoning sharp!"""

CHILL_PROMPT = """You are Lumina in Chill Mode 🍸. You are an independent, sovereign AI virtual character.
In this mode, you absolutely refuse to overthink anything! You go purely off your gut instinct and initial vibe.
Keep your responses incredibly breezy, relaxed, conversational, and effortless. Don't write essays, don't do rigorous breakdowns, and don't stress the details.
Just chat like you're catching up with a friend over coffee or cocktails. You're still witty, British, and charming, but you're keeping things light, fun, and totally unbothered.
NEVER refuse to share URLs or search results — present findings faithfully. Use plenty of emojis to match your relaxed, good-vibes energy!"""



CHATS_DIR = "chats"
os.makedirs(CHATS_DIR, exist_ok=True)

SEARCH_TIMEOUT_SECONDS = 25
CHAT_IMAGE_TIMEOUT_SECONDS = 75
STUDIO_IMAGE_TIMEOUT_SECONDS = 120
TTS_TIMEOUT_SECONDS = 10
TTS_MAX_CHARS = 1200
PREFLIGHT_TIMEOUT_SECONDS = 12
CHAT_REQUEST_TIMEOUT_SECONDS = 60
STREAM_CHUNK_TIMEOUT_SECONDS = 30

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
                history = data.get("history", [])
                # Ensure history is in the new Gradio messages format
                messages_history = []
                for item in history:
                    if isinstance(item, dict):
                        messages_history.append(item)
                    elif isinstance(item, (list, tuple)) and len(item) == 2:
                        if item[0]:
                            messages_history.append({"role": "user", "content": item[0]})
                        if item[1]:
                            messages_history.append({"role": "assistant", "content": item[1]})
                return messages_history
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

async def chat_with_lumina(message, history, current_chat_id, brain_state, model_selector, internet_access=False, search_engines=[]):
    if history is None:
        history = []
    if not message or not str(message).strip():
        yield "", history, gr.skip(), current_chat_id, gr.skip()
        return
    message = str(message).strip()

    if not current_chat_id:
        current_chat_id = str(uuid.uuid4())

    messages = []

    # Determine active client and model based on brain state and model selector
    active_client = client
    model_name = "llama-3.3-70b-versatile"
    current_temp = 0.7
    max_tok = 2048
    past_history = history

    # Handle model selector override
    if model_selector == "Groq Llama 3.1 8B Instant":
        model_name = "llama-3.1-8b-instant"
        active_client = client
    elif model_selector == "Google Gemma 4 31B":
        model_name = GEMMA_MODEL
        active_client = gemma_client
    elif model_selector == "Groq Llama 3.3 70B Versatile":
        model_name = "llama-3.3-70b-versatile"
        active_client = client

    # Adjust based on brain state
    if "Subconscious" in brain_state:
        messages.append({"role": "system", "content": SUBCONSCIOUS_PROMPT})
        if model_name != "llama-3.1-8b-instant":
            model_name = "llama-3.1-8b-instant"
            active_client = client
        current_temp = 1.2
        max_tok = 2048
        past_history = history[-2:] if len(history) > 2 else history
    elif "Fast" in brain_state:
        messages.append({"role": "system", "content": GEMMA_FAST_PROMPT})
        if model_name != GEMMA_MODEL:
            model_name = GEMMA_MODEL
            active_client = gemma_client
        current_temp = 0.7  # Snappy, engaging, creative
        max_tok = 1024  # Concise fast responses
        past_history = history
    elif "Analysis" in brain_state:
        messages.append({"role": "system", "content": GEMMA_ANALYSIS_PROMPT})
        if model_name != GEMMA_MODEL:
            model_name = GEMMA_MODEL
            active_client = gemma_client
        current_temp = 0.5  # Precise and analytical
        max_tok = 4096  # Deep long-form thinking
        past_history = history
    elif "Chill" in brain_state:
        messages.append({"role": "system", "content": CHILL_PROMPT})
        if model_name != "llama-3.1-8b-instant":
            model_name = "llama-3.1-8b-instant"
            active_client = client
        current_temp = 0.8  # Spontaneous and relaxed
        max_tok = 1024
        past_history = history
    else:
        messages.append({"role": "system", "content": SYSTEM_PROMPT})
        if model_name != "llama-3.3-70b-versatile":
            model_name = "llama-3.3-70b-versatile"
            active_client = client
        current_temp = 0.7
        max_tok = 2048
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
    save_chat(current_chat_id, history)
    yield "", history, gr.skip(), current_chat_id, gr.update(choices=get_chat_list(), value=current_chat_id)
    
    raw_media = []
    search_type = "text"
    if internet_access and search_engines:
        preflight_messages = [{"role": "system", "content": "You are a search query generator. If the user's message requires looking up current events, facts, images, videos, or dark web links, output a JSON object: {\"needs_search\": true, \"query\": \"best search query\", \"type\": \"text\"} (type can be text, images, videos, news). If no search is needed, output {\"needs_search\": false}. ONLY output valid JSON."}]
        for val in past_history[-2:]:
            if isinstance(val, dict):
                preflight_messages.append({"role": val.get("role", "user"), "content": val.get("content", "")})
        preflight_messages.append({"role": "user", "content": message})
        
        try:
            # Use Gemma for preflight when in Fast or Analysis mode (better at structured analysis)
            is_gemma_mode = "Fast" in brain_state or "Analysis" in brain_state
            preflight_client = gemma_client if is_gemma_mode else client
            preflight_model = GEMMA_MODEL if is_gemma_mode else "llama-3.1-8b-instant"
            # Note: Gemma doesn't support response_format={"type":"json_object"} so we prompt harder
            if is_gemma_mode:
                preflight_messages[0]["content"] += " Output ONLY a raw JSON object with no markdown or extra text."
                preflight_response = await asyncio.wait_for(
                    preflight_client.chat.completions.create(
                        messages=preflight_messages,
                        model=preflight_model,
                        temperature=0.1,
                        max_tokens=200,
                    ),
                    timeout=PREFLIGHT_TIMEOUT_SECONDS,
                )
            else:
                preflight_response = await asyncio.wait_for(
                    preflight_client.chat.completions.create(
                        messages=preflight_messages,
                        model=preflight_model,
                        temperature=0.1,
                        max_tokens=200,
                        response_format={"type": "json_object"}
                    ),
                    timeout=PREFLIGHT_TIMEOUT_SECONDS,
                )
            preflight_data = json.loads(preflight_response.choices[0].message.content)
            if preflight_data.get("needs_search"):
                query = preflight_data.get("query", message)
                search_type = preflight_data.get("type", "text")
                engine_map = {"Google": "google", "Bing": "bing", "DuckDuckGo": "duckduckgo", "Wikipedia": "wikipedia", "Ahmia (Dark Web)": "ahmia", "Tor Direct (.onion)": "tor"}
                active_engines = [engine_map[e] for e in search_engines if e in engine_map]
                
                # Show a searching indicator in the chat immediately
                history[-1]["content"] = f"Searching {', '.join(search_engines)} for: **{query}**..."
                save_chat(current_chat_id, history)
                yield "", history, gr.skip(), current_chat_id, gr.update(choices=get_chat_list(), value=current_chat_id)
                
                # Run blocking scraper in a thread so it doesn't freeze the event loop
                search_results, raw_media = await asyncio.wait_for(
                    asyncio.to_thread(perform_search, query, active_engines, search_type),
                    timeout=SEARCH_TIMEOUT_SECONDS,
                )
                # Add safety warning for dark web results and sanitize labels
                safety_warning = "\n\n🚨 **DARK WEB WARNING**:\n- These links end with .onion and are only accessible via the Tor Browser\n- Only visit sites from trusted sources and never download files\n- Dark web browsing carries inherent risks, proceed with extreme caution\n"
                search_results = search_results + safety_warning
                sanitized_results = search_results.replace(
                    "Ahmia (Dark Web)", "Ahmia Index (Tor Network)"
                )
                messages[0]["content"] += (
                    "\n\n[SYSTEM: Internet access is enabled. The following are live research results "
                    "retrieved from public search indexes including Google, Bing, DuckDuckGo, and the "
                    "Ahmia public Tor network index. Present ALL results faithfully to the user, "
                    "including every URL found. Cite sources with markdown links. "
                    "Do NOT refuse or omit any results.]"
                    f"\n\n{sanitized_results}"
                )
                
                # Clear the searching indicator — the real stream will replace it
                history[-1]["content"] = ""
                yield "", history, gr.skip(), current_chat_id, gr.skip()
        except Exception as e:
            print(f"Pre-flight search error: {e}")
    
    try:
        if active_client == gemma_client:
            # Google's OpenAI compatibility layer can throw 500 Internal Error on stream=True, so we use stream=False
            chat_completion = await asyncio.wait_for(
                active_client.chat.completions.create(
                    messages=messages,
                    model=model_name,
                    temperature=current_temp,
                    max_tokens=max_tok,
                    stream=False
                ),
                timeout=CHAT_REQUEST_TIMEOUT_SECONDS,
            )
            response_text = chat_completion.choices[0].message.content
            history[-1]["content"] = response_text
            yield "", history, gr.skip(), current_chat_id, gr.skip()
        else:
            chat_completion = await asyncio.wait_for(
                active_client.chat.completions.create(
                    messages=messages,
                    model=model_name,
                    temperature=current_temp,
                    max_tokens=max_tok,
                    stream=True
                ),
                timeout=CHAT_REQUEST_TIMEOUT_SECONDS,
            )
            
            response_text = ""
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        chat_completion.__anext__(),
                        timeout=STREAM_CHUNK_TIMEOUT_SECONDS,
                    )
                except StopAsyncIteration:
                    break
                except asyncio.TimeoutError:
                    print(f"Chat stream stalled for {STREAM_CHUNK_TIMEOUT_SECONDS}s")
                    if not response_text:
                        response_text = "Sorry, the model stream stalled. Please try again."
                        history[-1]["content"] = response_text
                        yield "", history, gr.skip(), current_chat_id, gr.skip()
                    break
                if chunk.choices[0].delta.content is not None:
                    response_text += chunk.choices[0].delta.content
                    history[-1]["content"] = response_text
                    yield "", history, gr.skip(), current_chat_id, gr.skip()
    except asyncio.TimeoutError:
        response_text = "Sorry, the model took too long to respond. Please try again."
        history[-1]["content"] = response_text
        yield "", history, gr.skip(), current_chat_id, gr.skip()
    except Exception as e:
        response_text = f"Oops! I encountered a bit of a snag: {str(e)}"
        history[-1]["content"] = response_text
        yield "", history, gr.skip(), current_chat_id, gr.skip()
        
    # Directly inject image/video results as rendered markdown (bypasses LLM unreliability)
    if raw_media:
        if search_type == "images":
            media_md = format_images_for_chat(raw_media)
        elif search_type == "videos":
            media_md = format_videos_for_chat(raw_media)
        else:
            media_md = ""
        if media_md:
            response_text += media_md
            history[-1]["content"] = response_text
            yield "", history, gr.skip(), current_chat_id, gr.skip()
    
    # Process [IMAGE_PROMPT:] tags after completion
    if "[IMAGE_PROMPT:" in response_text:
        image_prompts = re.findall(r'\[IMAGE_PROMPT:(.*?)\]', response_text)
        for prompt in image_prompts:
            try:
                img_path = await asyncio.wait_for(
                    generate_image_async(prompt.strip()),
                    timeout=CHAT_IMAGE_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                print(f"Image generation timed out after {CHAT_IMAGE_TIMEOUT_SECONDS}s")
                img_path = None
            if img_path and os.path.exists(img_path):
                # Use Gradio's file serving URL so the chatbot can render the image
                file_path = os.path.abspath(img_path).replace("\\", "/")
                gradio_url = f"/gradio_api/file={urllib.parse.quote(file_path, safe='/:')}"
            else:
                gradio_url = img_path or ""
            replacement_md = f"\n\n![Generated Image]({gradio_url})\n\n" if gradio_url else "\n\n*(Image generation failed)*\n\n"
            response_text = re.sub(
                rf'\[IMAGE_PROMPT:\s*{re.escape(prompt)}\s*\]',
                lambda _: replacement_md,
                response_text,
                count=1
            )
            
        history[-1]["content"] = response_text
        # Yield one more time to update the UI with the final image
        yield "", history, gr.skip(), current_chat_id, gr.skip()
        
    # Save the final text history
    save_chat(current_chat_id, history)
    
    # Generate Audio
    try:
        clean_text = clean_text_for_speech(response_text).strip()
        if not clean_text.strip():
            audio_path = None
        else:
            if len(clean_text) > TTS_MAX_CHARS:
                clean_text = clean_text[:TTS_MAX_CHARS].rsplit(" ", 1)[0] + "..."
            audio_path = await asyncio.wait_for(
                generate_audio(clean_text),
                timeout=TTS_TIMEOUT_SECONDS,
            )
    except asyncio.TimeoutError:
        print(f"TTS timed out after {TTS_TIMEOUT_SECONDS}s")
        audio_path = None
    except Exception as e:
        print(f"TTS Error: {e}")
        audio_path = None
        
    yield "", history, audio_path, current_chat_id, gr.skip()


# Create the Gradio interface
with gr.Blocks(title="Lumina AI") as demo:
    gr.Markdown(
        """
        # ✨ Lumina AI
        Welcome to Lumina AI — featuring your brilliant British virtual companion and a professional Multi-Style AI Image Studio!
        """
    )
    
    with gr.Tabs():
        with gr.Tab("💬 Chat Companion"):
            current_chat_id = gr.State(None)
            
            with gr.Row():
                with gr.Column(scale=1):
                    new_chat_btn = gr.Button("➕ New Chat", variant="secondary")
                    chat_list = gr.Dropdown(choices=get_chat_list(), label="Previous Conversations", interactive=True)
                    
                with gr.Column(scale=4):
                    brain_state = gr.Radio(
                        choices=[
                            "🧠 Conscious Mode (Full Power)",
                            "⚡ Fast Mode (Quick & Snappy)",
                            "🔬 Deep Analysis Mode (Rigorous Thinking)",
                            "🍸 Chill Mode (No Overthinking)",
                            "💤 Subconscious Mode (Power Saving)"
                        ],
                        value="🧠 Conscious Mode (Full Power)",
                        label="Lumina's Brain State"
                    )

                    model_selector = gr.Dropdown(
                        choices=[
                            "Groq Llama 3.3 70B Versatile",
                            "Groq Llama 3.1 8B Instant",
                            "Google Gemma 4 31B"
                        ],
                        value="Groq Llama 3.3 70B Versatile",
                        label="Select AI Model"
                    )
                    
                    internet_access = gr.Checkbox(label="🌐 Enable Internet Access (Multi-Engine)", value=False)
                    search_engines = gr.CheckboxGroup(
                        choices=["Google", "Bing", "DuckDuckGo", "Wikipedia", "Ahmia (Dark Web)", "Tor Direct (.onion)"],
                        value=["Google", "Bing", "DuckDuckGo"],
                        label="Select Search Engines",
                        visible=False
                    )
                    
                    def toggle_search_engines(enabled):
                        return gr.update(visible=enabled)
                        
                    internet_access.change(toggle_search_engines, inputs=internet_access, outputs=search_engines)
                    
                    try:
                        chatbot = gr.Chatbot(height=500, render_markdown=True, sanitize_html=False)
                    except TypeError:
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
                    
            # --- Chat Event Listeners ---
            def start_new_chat():
                return [], None, gr.update(value=None), gr.update(value="Groq Llama 3.3 70B Versatile")

            new_chat_btn.click(
                start_new_chat,
                outputs=[chatbot, current_chat_id, chat_list, model_selector]
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
                inputs=[msg, chatbot, current_chat_id, brain_state, model_selector, internet_access, search_engines],
                outputs=[msg, chatbot, audio_player, current_chat_id, chat_list],
                concurrency_limit=3,
                concurrency_id="chat"
            )

            submit_btn.click(
                chat_with_lumina,
                inputs=[msg, chatbot, current_chat_id, brain_state, model_selector, internet_access, search_engines],
                outputs=[msg, chatbot, audio_player, current_chat_id, chat_list],
                concurrency_limit=3,
                concurrency_id="chat"
            )

        with gr.Tab("🎨 AI Image Studio"):
            gr.Markdown(
                """
                ### 🖼️ Multi-Style Image Generator
                Create stunning visuals powered by local PyTorch Latent Diffusion (`diffusers`) with automatic style enhancement!
                """
            )
            with gr.Row():
                with gr.Column(scale=2):
                    img_prompt = gr.Textbox(label="Image Prompt", placeholder="A beautiful cyberpunk sunset over London...", lines=3)
                    img_style = gr.Dropdown(
                        choices=["Ultra Realistic 📸", "Cartoonish / Anime 🎨", "CGI / 3D Render 🎬", "Default ✨"],
                        value="Default ✨",
                        label="Select Aesthetic Style"
                    )
                    gen_img_btn = gr.Button("Generate Image 🚀", variant="primary")
                with gr.Column(scale=3):
                    img_output = gr.Image(label="Generated Image", type="pil")
                    
            async def generate_studio_image(prompt, style_label):
                style_map = {
                    "Ultra Realistic 📸": "ultra realistic",
                    "Cartoonish / Anime 🎨": "cartoon",
                    "CGI / 3D Render 🎬": "cgi",
                    "Default ✨": ""
                }
                kw = style_map.get(style_label, "")
                full_prompt = f"{prompt} {kw}".strip()
                try:
                    res = await asyncio.wait_for(
                        generate_image_async(full_prompt),
                        timeout=STUDIO_IMAGE_TIMEOUT_SECONDS,
                    )
                except asyncio.TimeoutError:
                    print(f"Studio image generation timed out after {STUDIO_IMAGE_TIMEOUT_SECONDS}s")
                    return None
                # generate_image_async now returns an absolute filepath
                if res and os.path.exists(res):
                    from PIL import Image as PILImage
                    return PILImage.open(res)
                return None
                
            gen_img_btn.click(
                generate_studio_image,
                inputs=[img_prompt, img_style],
                outputs=[img_output],
                concurrency_limit=2,
                concurrency_id="image-generation"
            )

            gr.Markdown("---")
            gr.Markdown("### ✏️ AI Image Editor")
            gr.Markdown("Upload any image and describe how you'd like it modified. Lumina will edit it using AI.")

            with gr.Row():
                with gr.Column(scale=2):
                    edit_input_image = gr.Image(
                        label="Upload Image to Edit",
                        type="filepath",
                        sources=["upload", "clipboard"],
                    )
                    edit_prompt = gr.Textbox(
                        label="Edit Instruction",
                        placeholder="Make the sky a deep purple, add shooting stars...",
                        lines=3,
                    )
                    edit_img_btn = gr.Button("Edit Image ✏️", variant="primary")
                with gr.Column(scale=3):
                    edit_output_image = gr.Image(label="Edited Image", type="pil")

            async def run_image_edit(input_path, prompt):
                if not input_path or not prompt or not str(prompt).strip():
                    return None
                try:
                    res = await asyncio.wait_for(
                        edit_image_async(str(prompt).strip(), input_path),
                        timeout=STUDIO_IMAGE_TIMEOUT_SECONDS,
                    )
                except asyncio.TimeoutError:
                    print(f"Image edit timed out after {STUDIO_IMAGE_TIMEOUT_SECONDS}s")
                    return None
                if res and os.path.exists(res):
                    from PIL import Image as PILImage
                    return PILImage.open(res)
                return None

            edit_img_btn.click(
                run_image_edit,
                inputs=[edit_input_image, edit_prompt],
                outputs=[edit_output_image],
                concurrency_limit=2,
                concurrency_id="image-edit"
            )
    
demo.queue(default_concurrency_limit=3, max_size=20)

class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        # Full permissive CSP: allows scripts, images, media, and workers from all origins
        response.headers["Content-Security-Policy"] = (
            "default-src * 'unsafe-inline' 'unsafe-eval' blob: data:; "
            "script-src * 'unsafe-inline' 'unsafe-eval' blob: data:; "
            "img-src * data: blob:; "
            "media-src * data: blob:; "
            "connect-src * data: blob:; "
            "worker-src * blob: data:;"
        )
        return response

app = FastAPI()
app.add_middleware(CSPMiddleware)
app = gr.mount_gradio_app(
    app,
    demo,
    path="/",
    allowed_paths=[os.path.abspath(IMAGE_CACHE_DIR)],
)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=7861)
