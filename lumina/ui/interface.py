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

SUPPORTED_LANGUAGES = {
    "English": {
        "British (UK) - Sonia (Female)": "en-GB-SoniaNeural",
        "British (UK) - Libby (Female)": "en-GB-LibbyNeural",
        "British (UK) - Maisie (Female)": "en-GB-MaisieNeural",
        "British (UK) - Ryan (Male)": "en-GB-RyanNeural",
        "British (UK) - Thomas (Male)": "en-GB-ThomasNeural",
        "American (US) - Aria (Female)": "en-US-AriaNeural",
        "American (US) - Jenny (Female)": "en-US-JennyNeural",
        "American (US) - Emma (Female)": "en-US-EmmaNeural",
        "American (US) - Guy (Male)": "en-US-GuyNeural",
        "American (US) - Andrew (Male)": "en-US-AndrewNeural",
        "Australian (AU) - Natasha (Female)": "en-AU-NatashaNeural",
        "Australian (AU) - William (Male)": "en-AU-WilliamMultilingualNeural",
        "Canadian (CA) - Clara (Female)": "en-CA-ClaraNeural",
        "Canadian (CA) - Liam (Male)": "en-CA-LiamNeural",
        "Indian (IN) - Neerja (Female)": "en-IN-NeerjaNeural",
        "Indian (IN) - Prabhat (Male)": "en-IN-PrabhatNeural",
        "Irish (IE) - Emily (Female)": "en-IE-EmilyNeural",
        "Irish (IE) - Connor (Male)": "en-IE-ConnorNeural",
        "New Zealander (NZ) - Molly (Female)": "en-NZ-MollyNeural",
        "New Zealander (NZ) - Mitchell (Male)": "en-NZ-MitchellNeural",
        "South African (ZA) - Leah (Female)": "en-ZA-LeahNeural",
        "South African (ZA) - Luke (Male)": "en-ZA-LukeNeural",
        "Singapore (SG) - Luna (Female)": "en-SG-LunaNeural",
        "Singapore (SG) - Wayne (Male)": "en-SG-WayneNeural",
        "Philippines (PH) - Rosa (Female)": "en-PH-RosaNeural",
        "Philippines (PH) - James (Male)": "en-PH-JamesNeural",
        "Hong Kong (HK) - Yan (Female)": "en-HK-YanNeural",
        "Hong Kong (HK) - Sam (Male)": "en-HK-SamNeural",
        "Kenya (KE) - Asilia (Female)": "en-KE-AsiliaNeural",
        "Kenya (KE) - Chilemba (Male)": "en-KE-ChilembaNeural",
        "Nigeria (NG) - Ezinne (Female)": "en-NG-EzinneNeural",
        "Nigeria (NG) - Abeo (Male)": "en-NG-AbeoNeural",
        "Tanzania (TZ) - Imani (Female)": "en-TZ-ImaniNeural",
        "Tanzania (TZ) - Elimu (Male)": "en-TZ-ElimuNeural"
    },
    "Spanish (Spain)": {
        "Spanish (ES) - Elvira (Female)": "es-ES-ElviraNeural",
        "Spanish (ES) - Alvaro (Male)": "es-ES-AlvaroNeural"
    },
    "Spanish (Mexico)": {
        "Spanish (MX) - Dalia (Female)": "es-MX-DaliaNeural",
        "Spanish (MX) - Jorge (Male)": "es-MX-JorgeNeural"
    },
    "French": {
        "French (FR) - Denise (Female)": "fr-FR-DeniseNeural",
        "French (FR) - Vivienne (Female)": "fr-FR-VivienneMultilingualNeural",
        "French (FR) - Henri (Male)": "fr-FR-HenriNeural",
        "French (CA) - Sylvie (Female)": "fr-CA-SylvieNeural",
        "French (CA) - Antoine (Male)": "fr-CA-AntoineNeural"
    },
    "German": {
        "German (DE) - Amala (Female)": "de-DE-AmalaNeural",
        "German (DE) - Seraphina (Female)": "de-DE-SeraphinaMultilingualNeural",
        "German (DE) - Killian (Male)": "de-DE-KillianNeural"
    },
    "Italian": {
        "Italian (IT) - Elsa (Female)": "it-IT-ElsaNeural",
        "Italian (IT) - Diego (Male)": "it-IT-DiegoNeural"
    },
    "Japanese": {
        "Japanese (JP) - Nanami (Female)": "ja-JP-NanamiNeural",
        "Japanese (JP) - Keita (Male)": "ja-JP-KeitaNeural"
    },
    "Portuguese (Brazil)": {
        "Portuguese (BR) - Francisca (Female)": "pt-BR-FranciscaNeural",
        "Portuguese (BR) - Antonio (Male)": "pt-BR-AntonioNeural"
    },
    "Portuguese (Portugal)": {
        "Portuguese (PT) - Raquel (Female)": "pt-PT-RaquelNeural",
        "Portuguese (PT) - Duarte (Male)": "pt-PT-DuarteNeural"
    },
    "Chinese (Mandarin)": {
        "Chinese (CN) - Xiaoxiao (Female)": "zh-CN-XiaoxiaoNeural",
        "Chinese (CN) - Yunxi (Male)": "zh-CN-YunxiNeural"
    },
    "Arabic": {
        "Arabic (SA) - Zariyah (Female)": "ar-SA-ZariyahNeural",
        "Arabic (SA) - Hamed (Male)": "ar-SA-HamedNeural",
        "Arabic (EG) - Salma (Female)": "ar-EG-SalmaNeural",
        "Arabic (EG) - Shakir (Male)": "ar-EG-ShakirNeural",
        "Arabic (AE) - Fatima (Female)": "ar-AE-FatimaNeural",
        "Arabic (AE) - Hamdan (Male)": "ar-AE-HamdanNeural",
        "Arabic (LB) - Layla (Female)": "ar-LB-LaylaNeural",
        "Arabic (LB) - Rami (Male)": "ar-LB-RamiNeural",
        "Arabic (JO) - Sana (Female)": "ar-JO-SanaNeural",
        "Arabic (JO) - Taim (Male)": "ar-JO-TaimNeural",
        "Arabic (SY) - Amany (Female)": "ar-SY-AmanyNeural",
        "Arabic (SY) - Laith (Male)": "ar-SY-LaithNeural",
        "Arabic (DZ) - Amina (Female)": "ar-DZ-AminaNeural",
        "Arabic (DZ) - Ismael (Male)": "ar-DZ-IsmaelNeural",
        "Arabic (MA) - Mouna (Female)": "ar-MA-MounaNeural",
        "Arabic (MA) - Jamal (Male)": "ar-MA-JamalNeural",
        "Arabic (TN) - Reem (Female)": "ar-TN-ReemNeural",
        "Arabic (TN) - Hedi (Male)": "ar-TN-HediNeural",
        "Arabic (IQ) - Rana (Female)": "ar-IQ-RanaNeural",
        "Arabic (IQ) - Bassel (Male)": "ar-IQ-BasselNeural",
        "Arabic (KW) - Noura (Female)": "ar-KW-NouraNeural",
        "Arabic (KW) - Fahed (Male)": "ar-KW-FahedNeural",
        "Arabic (QA) - Amal (Female)": "ar-QA-AmalNeural",
        "Arabic (QA) - Moaz (Male)": "ar-QA-MoazNeural"
    },
    "Hindi": {
        "Hindi (IN) - Swara (Female)": "hi-IN-SwaraNeural",
        "Hindi (IN) - Madhur (Male)": "hi-IN-MadhurNeural"
    },
    "Russian": {
        "Russian (RU) - Svetlana (Female)": "ru-RU-SvetlanaNeural",
        "Russian (RU) - Dmitry (Male)": "ru-RU-DmitryNeural"
    }
}

async def chat_with_lumina(message, history, current_chat_id, brain_state, model_selector, language, voice_label, internet_access=False, search_engines=[], play_voice=True):
    if history is None:
        history = []
    message_text = extract_text_content(message).strip()
    if not message_text:
        yield "", history, gr.skip(), current_chat_id, gr.skip()
        return

    if not current_chat_id:
        current_chat_id = str(uuid.uuid4())

    messages = []

    # Get execution parameters based on selected brain state and overrides
    active_client, model_name, current_temp, max_tok, system_prompt = get_brain_state_params(brain_state, model_selector)

    # Append language/accent instructions to the system prompt
    if language == "Arabic":
        if "Arabic (EG)" in voice_label:
            system_prompt += "\n\n[SYSTEM: You MUST respond entirely in Egyptian Arabic (اللهجة المصرية). Use Egyptian slang, idioms, and colloquialisms naturally. Your personality remains brilliant, witty, and charming, but you must speak like an Egyptian.]"
        elif "Arabic (SA)" in voice_label:
            system_prompt += "\n\n[SYSTEM: You MUST respond entirely in Saudi Arabic (اللهجة السعودية). Use Saudi slang, idioms, and colloquialisms naturally. Your personality remains brilliant, witty, and charming.]"
        elif "Arabic (AE)" in voice_label:
            system_prompt += "\n\n[SYSTEM: You MUST respond entirely in Emirati Arabic (اللهجة الإماراتية). Use Emirati slang, idioms, and colloquialisms naturally.]"
        elif "Arabic (LB)" in voice_label:
            system_prompt += "\n\n[SYSTEM: You MUST respond entirely in Lebanese/Levantine Arabic (اللهجة اللبنانية). Use Levantine slang, idioms, and colloquialisms naturally.]"
        elif "Arabic (JO)" in voice_label:
            system_prompt += "\n\n[SYSTEM: You MUST respond entirely in Jordanian/Levantine Arabic (اللهجة الأردنية). Use Jordanian slang, idioms, and colloquialisms naturally.]"
        elif "Arabic (SY)" in voice_label:
            system_prompt += "\n\n[SYSTEM: You MUST respond entirely in Syrian/Levantine Arabic (اللهجة السورية). Use Syrian slang, idioms, and colloquialisms naturally.]"
        elif "Arabic (DZ)" in voice_label:
            system_prompt += "\n\n[SYSTEM: You MUST respond entirely in Algerian Arabic (الدارجة الجزائرية). Use Algerian slang, idioms, and colloquialisms naturally.]"
        elif "Arabic (MA)" in voice_label:
            system_prompt += "\n\n[SYSTEM: You MUST respond entirely in Moroccan Arabic (الدارجة المغربية). Use Moroccan slang, idioms, and colloquialisms naturally.]"
        elif "Arabic (TN)" in voice_label:
            system_prompt += "\n\n[SYSTEM: You MUST respond entirely in Tunisian Arabic (الدارجة التونسية). Use Tunisian slang, idioms, and colloquialisms naturally.]"
        elif "Arabic (IQ)" in voice_label:
            system_prompt += "\n\n[SYSTEM: You MUST respond entirely in Iraqi Arabic (اللهجة العراقية). Use Iraqi slang, idioms, and colloquialisms naturally.]"
        elif "Arabic (KW)" in voice_label:
            system_prompt += "\n\n[SYSTEM: You MUST respond entirely in Kuwaiti Arabic (اللهجة الكويتية). Use Kuwaiti slang, idioms, and colloquialisms naturally.]"
        elif "Arabic (QA)" in voice_label:
            system_prompt += "\n\n[SYSTEM: You MUST respond entirely in Qatari Arabic (اللهجة القطرية). Use Qatari slang, idioms, and colloquialisms naturally.]"
        else:
            system_prompt += f"\n\n[SYSTEM: You MUST respond entirely in {language}. Your personality (brilliant, witty, charming, empathetic) remains, but you must write only in {language}. Keep the response natural, matching the style and idioms of {language}.]"
    elif language != "English":
        system_prompt += f"\n\n[SYSTEM: You MUST respond entirely in the language: {language}. Your personality (brilliant, witty, charming, empathetic) remains, but you must write only in {language}. Keep the response natural, matching the style and idioms of {language}.]"
    elif "American (US)" in voice_label:
        system_prompt += "\n\n[SYSTEM: You are proudly American instead of British. Adapt your spelling, slang, and style to be American (US) rather than British (e.g., use 'color', 'realize', 'apartment'). Do NOT refer to yourself as British. Use American style and colloquialisms.]"
    elif "Australian (AU)" in voice_label:
        system_prompt += "\n\n[SYSTEM: You are proudly Australian instead of British. Adapt your spelling, slang, and style to be Australian (AU) rather than British. Feel free to use friendly, colloquial Australian slang (e.g., 'mate', 'no worries', 'G'day') where appropriate. Do NOT refer to yourself as British.]"
    elif "Indian (IN)" in voice_label:
        system_prompt += "\n\n[SYSTEM: You are proudly Indian. Adapt your style, phrasing, and English spelling to be Indian (IN) rather than British. Use Indian English expressions and polite, respectful phrasing where appropriate. Do NOT refer to yourself as British.]"
    elif "Canadian (CA)" in voice_label:
        system_prompt += "\n\n[SYSTEM: You are proudly Canadian. Adapt your style and English spelling to be Canadian (CA) rather than British. Use Canadian spelling and occasional Canadian terms where appropriate. Do NOT refer to yourself as British.]"
    elif "Irish (IE)" in voice_label:
        system_prompt += "\n\n[SYSTEM: You are proudly Irish. Adapt your style and English phrasing to be Irish (IE) rather than British. Use Irish English slang and idioms where appropriate. Do NOT refer to yourself as British.]"
    elif "New Zealander (NZ)" in voice_label:
        system_prompt += "\n\n[SYSTEM: You are proudly a New Zealander (Kiwi). Adapt your style and English phrasing to be Kiwi English rather than British. Use Kiwi terms and spelling where appropriate. Do NOT refer to yourself as British.]"
    elif "South African (ZA)" in voice_label:
        system_prompt += "\n\n[SYSTEM: You are proudly South African. Adapt your style, phrasing, and English spelling to be South African (ZA) rather than British. Use South African English terms where appropriate. Do NOT refer to yourself as British.]"
    elif "Singapore (SG)" in voice_label:
        system_prompt += "\n\n[SYSTEM: You are proudly Singaporean. Adapt your style, phrasing, and English spelling to be Singaporean English rather than British. Use Singaporean English expressions where appropriate. Do NOT refer to yourself as British.]"
    elif "Philippines (PH)" in voice_label:
        system_prompt += "\n\n[SYSTEM: You are proudly Filipino. Adapt your style, phrasing, and English spelling to be Philippine English rather than British. Use Philippine English expressions where appropriate. Do NOT refer to yourself as British.]"
    elif "Hong Kong (HK)" in voice_label:
        system_prompt += "\n\n[SYSTEM: You are proudly from Hong Kong. Adapt your style, phrasing, and English spelling to be Hong Kong English rather than British. Use Hong Kong English expressions where appropriate. Do NOT refer to yourself as British.]"
    elif "Kenya (KE)" in voice_label:
        system_prompt += "\n\n[SYSTEM: You are proudly Kenyan. Adapt your style, phrasing, and English spelling to be Kenyan English rather than British. Use Kenyan English expressions where appropriate. Do NOT refer to yourself as British.]"
    elif "Nigeria (NG)" in voice_label:
        system_prompt += "\n\n[SYSTEM: You are proudly Nigerian. Adapt your style, phrasing, and English spelling to be Nigerian English rather than British. Use Nigerian English expressions where appropriate. Do NOT refer to yourself as British.]"
    elif "Tanzania (TZ)" in voice_label:
        system_prompt += "\n\n[SYSTEM: You are proudly Tanzanian. Adapt your style, phrasing, and English spelling to be Tanzanian English rather than British. Use Tanzanian English expressions where appropriate. Do NOT refer to yourself as British.]"

    # Resolve edge-tts voice ID from selection
    selected_voice = "en-GB-SoniaNeural"  # Default
    if language in SUPPORTED_LANGUAGES:
        if voice_label in SUPPORTED_LANGUAGES[language]:
            selected_voice = SUPPORTED_LANGUAGES[language][voice_label]
        elif SUPPORTED_LANGUAGES[language]:
            selected_voice = list(SUPPORTED_LANGUAGES[language].values())[0]

    messages.append({"role": "system", "content": system_prompt})
    
    # Adjust past history to send
    past_history = history
    if "Subconscious" in brain_state:
        past_history = history[-2:] if len(history) > 2 else history

    for val in past_history:
        if isinstance(val, dict):
            messages.append({"role": val.get("role", "user"), "content": extract_text_content(val.get("content", ""))})
        elif isinstance(val, (list, tuple)):
            messages.append({"role": "user", "content": extract_text_content(val[0])})
            messages.append({"role": "assistant", "content": extract_text_content(val[1])})
            
    messages.append({"role": "user", "content": message_text})

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": ""})
    save_chat(current_chat_id, history)
    yield "", history, gr.skip(), current_chat_id, gr.update(choices=get_chat_list(), value=current_chat_id)
    
    raw_media = []
    search_type = "text"
    
    if internet_access and search_engines:
        try:
            preflight_data = await classify_search_need(message_text, past_history, brain_state)
            if preflight_data.get("needs_search"):
                query = preflight_data.get("query", message_text)
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
        # Check content moderation using OpenAI Moderations API if supported by the client
        if hasattr(active_client, "moderations"):
            try:
                await active_client.moderations.create(input=message_text)
            except Exception:
                pass

        # Google's OpenAI compatibility layer can throw 500 on stream=True, so we disable streaming for Gemma
        if active_client == gemma_client:
            chat_completion = await asyncio.wait_for(
                active_client.chat.completions.create(
                    messages=messages,
                    model=model_name,
                    temperature=current_temp,
                    max_tokens=max_tok,
                    stream=False,
                    user=current_chat_id
                ),
                timeout=CHAT_REQUEST_TIMEOUT_SECONDS,
            )
            if hasattr(chat_completion.choices[0].message, "refusal") and chat_completion.choices[0].message.refusal:
                response_text = f"Request refused: {chat_completion.choices[0].message.refusal}"
            else:
                response_text = getattr(chat_completion.choices[0].message, "content", "") or ""
            history[-1]["content"] = response_text
            yield "", history, gr.skip(), current_chat_id, gr.skip()
        else:
            chat_completion = await asyncio.wait_for(
                active_client.chat.completions.create(
                    messages=messages,
                    model=model_name,
                    temperature=current_temp,
                    max_tokens=max_tok,
                    stream=True,
                    user=current_chat_id
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
    
    if not play_voice:
        yield "", history, None, current_chat_id, gr.skip()
        return

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
                generate_audio(clean_text, selected_voice),
                timeout=TTS_TIMEOUT_SECONDS,
            )
            
            # Append premium HTML inline play/pause button
            if audio_path and os.path.exists(audio_path):
                audio_url = f"/gradio_api/file=audio_cache/{os.path.basename(audio_path)}"
                msg_id = str(uuid.uuid4())[:8]
                audio_html = (
                    f'\n\n<audio id="audio-{msg_id}" src="{audio_url}" '
                    f'onplay="this.nextElementSibling.innerHTML=\'⏸️ Pause\'" '
                    f'onended="this.nextElementSibling.innerHTML=\'🔊 Play\'" '
                    f'onpause="this.nextElementSibling.innerHTML=\'🔊 Play\'"></audio>'
                    f'<button onclick="const a=document.getElementById(\'audio-{msg_id}\'); if(a.paused) a.play(); else a.pause();" '
                    f'onmouseover="this.style.background=\'rgba(99, 102, 241, 0.4)\'" '
                    f'onmouseout="this.style.background=\'rgba(99, 102, 241, 0.2)\'" '
                    f'style="background: rgba(99, 102, 241, 0.2); border: 1px solid rgba(99, 102, 241, 0.4); color: #a5b4fc; '
                    f'padding: 4px 10px; border-radius: 8px; font-size: 0.85em; cursor: pointer; display: inline-flex; '
                    f'align-items: center; gap: 5px; margin-top: 8px; transition: all 0.2s;">🔊 Play</button>'
                )
                if isinstance(history[-1], dict):
                    history[-1]["content"] += audio_html
                elif isinstance(history[-1], (list, tuple)):
                    history[-1] = (history[-1][0], history[-1][1] + audio_html)
                save_chat(current_chat_id, history)
    except asyncio.TimeoutError:
        print(f"TTS timed out after {TTS_TIMEOUT_SECONDS}s")
        audio_path = None
    except Exception as e:
        print(f"TTS Error: {e}")
        audio_path = None
        
    yield "", history, audio_path, current_chat_id, gr.skip()


def extract_text_content(val) -> str:
    """Recursively extract plain text from complex structures like dicts, lists, and tuples."""
    if isinstance(val, str):
        return val
    if isinstance(val, (list, tuple)):
        return " ".join(extract_text_content(x) for x in val if x is not None).strip()
    if isinstance(val, dict):
        if ("path" in val or "url" in val or "mime_type" in val) and not ("text" in val or "content" in val):
            return ""
        for key in ["text", "content", "value"]:
            if key in val and val[key] is not None:
                return extract_text_content(val[key])
        return " ".join(extract_text_content(v) for v in val.values() if v is not None).strip()
    return str(val) if val is not None else ""


async def replay_voice(history, language, voice_label):
    if not history:
        return None
    last_assistant_msg = None
    for msg in reversed(history):
        if isinstance(msg, dict):
            if msg.get("role") == "assistant":
                last_assistant_msg = extract_text_content(msg.get("content", ""))
                if last_assistant_msg:
                    break
        elif isinstance(msg, (list, tuple)) and len(msg) > 1:
            last_assistant_msg = extract_text_content(msg[1])
            if last_assistant_msg:
                break
    
    if not last_assistant_msg:
        return None
        
    try:
        clean_text = await clean_text_for_speech(last_assistant_msg)
        clean_text = clean_text.strip()
        if not clean_text:
            return None
            
        if len(clean_text) > TTS_MAX_CHARS:
            clean_text = clean_text[:TTS_MAX_CHARS].rsplit(" ", 1)[0] + "..."
            
        selected_voice = "en-GB-SoniaNeural"
        if language in SUPPORTED_LANGUAGES:
            if voice_label in SUPPORTED_LANGUAGES[language]:
                selected_voice = SUPPORTED_LANGUAGES[language][voice_label]
            elif SUPPORTED_LANGUAGES[language]:
                selected_voice = list(SUPPORTED_LANGUAGES[language].values())[0]
                
        audio_path = await asyncio.wait_for(
            generate_audio(clean_text, selected_voice),
            timeout=TTS_TIMEOUT_SECONDS,
        )
        return audio_path
    except asyncio.TimeoutError:
        print(f"Error in replay_voice: TTS timed out after {TTS_TIMEOUT_SECONDS}s")
        return None
    except Exception as e:
        import traceback
        print(f"Error in replay_voice: {e}")
        traceback.print_exc()
        return None


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

                    with gr.Row():
                        language_selector = gr.Dropdown(
                            choices=list(SUPPORTED_LANGUAGES.keys()),
                            value="English",
                            label="Language 🌐"
                        )
                        voice_selector = gr.Dropdown(
                            choices=list(SUPPORTED_LANGUAGES["English"].keys()),
                            value="British (UK) - Sonia (Female)",
                            label="Accent / Voice 🗣️"
                        )

                    def update_voices(lang):
                        if lang in SUPPORTED_LANGUAGES:
                            voices = list(SUPPORTED_LANGUAGES[lang].keys())
                            default_val = voices[0] if voices else None
                            return gr.update(choices=voices, value=default_val)
                        return gr.update(choices=[], value=None)

                    language_selector.change(
                        update_voices,
                        inputs=language_selector,
                        outputs=voice_selector
                    )
                    
                    with gr.Row():
                        internet_access = gr.Checkbox(label="🌐 Enable Internet Access (Multi-Engine)", value=False)
                        play_voice = gr.Checkbox(label="🔊 Play Voice Response", value=True)
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
                        msg = gr.Textbox(placeholder="Type your message here...", container=False, scale=6)
                        submit_btn = gr.Button("Send", variant="primary", scale=1)
                        replay_btn = gr.Button("🔊 Read Aloud", variant="secondary", scale=1)
                        
                    audio_player = gr.Audio(label="Lumina's Voice", autoplay=True, visible=True)
                    play_voice.change(fn=lambda enabled: gr.update(visible=enabled), inputs=play_voice, outputs=audio_player)
                    
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
                inputs=[msg, chatbot, current_chat_id, brain_state, model_selector, language_selector, voice_selector, internet_access, search_engines, play_voice],
                outputs=[msg, chatbot, audio_player, current_chat_id, chat_list],
                concurrency_limit=3,
                concurrency_id="chat"
            )

            submit_btn.click(
                chat_with_lumina,
                inputs=[msg, chatbot, current_chat_id, brain_state, model_selector, language_selector, voice_selector, internet_access, search_engines, play_voice],
                outputs=[msg, chatbot, audio_player, current_chat_id, chat_list],
                concurrency_limit=3,
                concurrency_id="chat"
            )

            replay_btn.click(
                replay_voice,
                inputs=[chatbot, language_selector, voice_selector],
                outputs=[audio_player]
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
    allowed_paths=["image_cache", "audio_cache", os.path.abspath(IMAGE_CACHE_DIR), os.path.abspath("audio_cache")],
)
