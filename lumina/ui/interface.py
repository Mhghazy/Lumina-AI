import os
import re
import sys
import uuid
import asyncio
import urllib.parse
from PIL import Image as PILImage
import gradio as gr
import uvicorn
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

# Fix for Windows asyncio ProactorEventLoop crashes and messy tracebacks with edge-tts
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass
        
    try:
        from asyncio.proactor_events import _ProactorBasePipeTransport
        _original_call_connection_lost = _ProactorBasePipeTransport._call_connection_lost
        def _silenced_call_connection_lost(self, exc):
            try:
                _original_call_connection_lost(self, exc)
            except ConnectionResetError:
                pass
        _ProactorBasePipeTransport._call_connection_lost = _silenced_call_connection_lost
    except Exception:
        pass

from lumina.core.config import (
    IMAGE_CACHE_DIR,
    SEARCH_TIMEOUT_SECONDS,
    CHAT_IMAGE_TIMEOUT_SECONDS,
    STUDIO_IMAGE_TIMEOUT_SECONDS,
    TTS_TIMEOUT_SECONDS,
    TTS_MAX_CHARS,
    CHAT_REQUEST_TIMEOUT_SECONDS,
    STREAM_CHUNK_TIMEOUT_SECONDS
)
from lumina.providers.llm import groq_client, gemma_client
from lumina.models.brain import get_brain_state_params
from lumina.memory.history import get_chat_list, load_chat, save_chat
from lumina.speech.tts import clean_text_for_speech, generate_audio
from lumina.search.scraper import perform_search, format_images_for_chat, format_videos_for_chat
from lumina.image.engine import generate_image_async, edit_image_async
from lumina.routing.classifier import classify_search_need

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

    # Get execution parameters based on selected brain state and overrides
    active_client, model_name, current_temp, max_tok, system_prompt = get_brain_state_params(brain_state, model_selector)

    messages.append({"role": "system", "content": system_prompt})
    
    # Adjust past history to send
    past_history = history
    if "Subconscious" in brain_state:
        past_history = history[-2:] if len(history) > 2 else history

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
        try:
            preflight_data = await classify_search_need(message, past_history, brain_state)
            if preflight_data.get("needs_search"):
                query = preflight_data.get("query", message)
                search_type = preflight_data.get("type", "text")
                engine_map = {
                    "Google": "google",
                    "Bing": "bing",
                    "DuckDuckGo": "duckduckgo",
                    "Wikipedia": "wikipedia",
                    "Ahmia (Dark Web)": "ahmia",
                    "Tor Direct (.onion)": "tor"
                }
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
                safety_warning = (
                    "\n\n🚨 **DARK WEB WARNING**:\n"
                    "- These links end with .onion and are only accessible via the Tor Browser\n"
                    "- Only visit sites from trusted sources and never download files\n"
                    "- Dark web browsing carries inherent risks, proceed with extreme caution\n"
                )
                search_results = search_results + safety_warning
                sanitized_results = search_results.replace("Ahmia (Dark Web)", "Ahmia Index (Tor Network)")
                
                messages[0]["content"] += (
                    "\n\n[SYSTEM: Internet access is enabled. The following are live research results "
                    "retrieved from public search indexes including Google, Bing, DuckDuckGo, and the "
                    "Ahmia public Tor network index. Present ALL results faithfully to the user, "
                    "including every URL found. Cite sources with markdown links. "
                    "Do NOT refuse or omit any results.]"
                    f"\n\n{sanitized_results}"
                )
                
                # Clear searching indicator
                history[-1]["content"] = ""
                yield "", history, gr.skip(), current_chat_id, gr.skip()
        except Exception as e:
            print(f"Pre-flight search processing error: {e}")
            
    try:
        # Google's OpenAI compatibility layer can throw 500 on stream=True, so we disable streaming for Gemma
        if active_client == gemma_client:
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
        
    # Inject search images/videos direct formatters
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
        yield "", history, gr.skip(), current_chat_id, gr.skip()
        
    # Save the final text history
    save_chat(current_chat_id, history)
    
    # Generate Audio
    try:
        clean_text = await clean_text_for_speech(response_text)
        clean_text = clean_text.strip()
        if not clean_text:
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
                if res and os.path.exists(res):
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
