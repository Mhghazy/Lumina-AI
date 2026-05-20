import os
import time
import base64
import random
import asyncio
import urllib.parse
from PIL import Image
from io import BytesIO

from lumina.core.config import (
    GOOGLE_API_KEY,
    GOOGLE_IMAGEN_MODEL,
    GOOGLE_GEMINI_IMAGE_MODEL,
    GOOGLE_GEMINI_EDIT_MODEL,
    IMAGE_CACHE_DIR
)
from lumina.utils.network import (
    safe_error,
    make_session,
    download_url,
    save_image_bytes
)

def _has_google_key() -> bool:
    if GOOGLE_API_KEY:
        return True
    print("[ImageGen] Google provider skipped: GOOGLE_API_KEY is not set")
    return False

# ---------------------------------------------------------------------------
# Google Imagen provider
# ---------------------------------------------------------------------------
def _try_imagen(prompt: str, filepath: str) -> bool:
    print(f"[ImageGen] Provider: Google Imagen ({GOOGLE_IMAGEN_MODEL})")
    if not _has_google_key():
        return False
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GOOGLE_IMAGEN_MODEL}:predict?key={GOOGLE_API_KEY}"
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {"sampleCount": 1, "aspectRatio": "1:1"}
        }
        r = make_session().post(url, json=payload, timeout=8)
        r.raise_for_status()
        preds = r.json().get("predictions", [])
        if preds:
            img_b64 = preds[0].get("bytesBase64Encoded", "")
            if img_b64:
                return save_image_bytes(base64.b64decode(img_b64), filepath)
        print(f"[ImageGen] Imagen 3 response: {r.text[:200]}")
    except Exception as e:
        print(f"[ImageGen] Imagen 3 failed: {safe_error(e)}")
    return False

# ---------------------------------------------------------------------------
# Stage 2: Gemini 2.0 Flash image generation
# ---------------------------------------------------------------------------
def _try_gemini_flash_image(prompt: str, filepath: str) -> bool:
    print(f"[ImageGen] Provider: Gemini image generation ({GOOGLE_GEMINI_IMAGE_MODEL})")
    if not _has_google_key():
        return False
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GOOGLE_GEMINI_IMAGE_MODEL}:generateContent?key={GOOGLE_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": f"Generate a photorealistic image of: {prompt}"}]}],
            "generationConfig": {"responseModalities": ["Image"]}
        }
        r = make_session().post(url, json=payload, timeout=8)
        r.raise_for_status()
        for candidate in r.json().get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                if "inlineData" in part:
                    img_bytes = base64.b64decode(part["inlineData"]["data"])
                    return save_image_bytes(img_bytes, filepath)
        print(f"[ImageGen] Gemini Flash image: no inlineData in response")
    except Exception as e:
        print(f"[ImageGen] Gemini Flash image failed: {safe_error(e)}")
    return False

# ---------------------------------------------------------------------------
# Stage 3: Pollinations
# ---------------------------------------------------------------------------
def _try_pollinations(prompt: str, filepath: str) -> bool:
    encoded = urllib.parse.quote(prompt)
    seed = random.randint(1, 999_999)
    url = f"https://image.pollinations.ai/prompt/{encoded}?nologo=true&seed={seed}&width=1024&height=1024"
    print("[ImageGen] Provider: Pollinations")
    return download_url(url, filepath, retries=2, wait=3)

# ---------------------------------------------------------------------------
# Stage 4: Craiyon
# ---------------------------------------------------------------------------
def _try_craiyon(prompt: str, filepath: str) -> bool:
    print("[ImageGen] Provider: Craiyon")
    try:
        session = make_session()
        session.headers.update({
            "Content-Type": "application/json",
            "Origin": "https://www.craiyon.com",
            "Referer": "https://www.craiyon.com/",
        })
        payload = {
            "prompt": prompt,
            "model": "photo",
            "token": None,
            "negative_prompt": "low quality, blurry, distorted",
            "version": "35s5hfwn9n78gb06",
        }
        r = session.post("https://api.craiyon.com/v3", json=payload, timeout=25)
        r.raise_for_status()
        images = r.json().get("images", [])
        if images:
            return save_image_bytes(base64.b64decode(images[0]), filepath)
        print("[ImageGen] Craiyon: no images in response")
    except Exception as e:
        print(f"[ImageGen] Craiyon failed: {safe_error(e)}")
    return False

# ---------------------------------------------------------------------------
# Stage 5: AI Horde
# ---------------------------------------------------------------------------
def _try_aihorde(prompt: str, filepath: str) -> bool:
    print("[ImageGen] Provider: AI Horde")
    try:
        BASE = "https://aihorde.net/api/v2"
        session = make_session()
        session.headers.update({
            "apikey": "0000000000",
            "Content-Type": "application/json",
            "Client-Agent": "LuminaAI:1.0:local",
        })
        payload = {
            "prompt": prompt,
            "params": {"sampler_name": "k_euler_a", "cfg_scale": 7, "steps": 20, "width": 512, "height": 512, "n": 1},
            "models": ["Deliberate"],
            "r2": False,
        }
        r_sub = session.post(f"{BASE}/generate/async", json=payload, timeout=15)
        r_sub.raise_for_status()
        job_id = r_sub.json().get("id")
        if not job_id:
            print("[ImageGen] AI Horde: no job ID")
            return False
        print(f"[ImageGen]   AI Horde job: {job_id} — polling...")
        for _ in range(4):
            time.sleep(4)
            rs = session.get(f"{BASE}/generate/status/{job_id}", timeout=10)
            rs.raise_for_status()
            sd = rs.json()
            if sd.get("done"):
                gens = sd.get("generations", [])
                if gens:
                    return save_image_bytes(base64.b64decode(gens[0]["img"]), filepath)
                return False
            print(f"[ImageGen]   AI Horde: queue {sd.get('queue_position','?')}, ETA {sd.get('wait_time','?')}s")
        print("[ImageGen] AI Horde: timed out")
    except Exception as e:
        print(f"[ImageGen] AI Horde failed: {safe_error(e)}")
    return False

# ---------------------------------------------------------------------------
# Stage 6: Together AI
# ---------------------------------------------------------------------------
def _try_together(prompt: str, filepath: str) -> bool:
    print("[ImageGen] Provider: Together AI")
    try:
        from together import Together
        api_key = os.getenv("TOGETHER_API_KEY")
        if not api_key:
            print("[ImageGen] Together AI skipped: TOGETHER_API_KEY is not set")
            return False
        client = Together(api_key=api_key)
        resp = client.images.generate(prompt=prompt, model="black-forest-labs/FLUX.1-schnell-Free", width=1024, height=1024, steps=4, n=1)
        item = resp.data[0]
        if hasattr(item, "b64_json") and item.b64_json:
            return save_image_bytes(base64.b64decode(item.b64_json), filepath)
        url = getattr(item, "url", None) or item["url"]
        return download_url(url, filepath, retries=2, wait=3)
    except Exception as e:
        print(f"[ImageGen] Together AI failed: {safe_error(e)}")
    return False

PROVIDERS = [
    _try_pollinations,
    _try_together,
    _try_craiyon,
    _try_imagen,
    _try_gemini_flash_image,
    _try_aihorde,
]

async def generate_image_async(prompt: str) -> str | None:
    filepath = os.path.join(IMAGE_CACHE_DIR, f"img_{random.randint(1, 999_999)}.png")

    def _run():
        for fn in PROVIDERS:
            try:
                if fn(prompt, filepath):
                    return True
            except Exception as e:
                print(f"[ImageGen] {fn.__name__} raised: {safe_error(e)}")
        return False

    try:
        if await asyncio.to_thread(_run):
            return os.path.abspath(filepath)
    except Exception as e:
        print(f"[ImageGen] Chain error: {safe_error(e)}")

    # PIL error card fallback
    print("[ImageGen] ⚠ All providers failed — generating error card.")
    try:
        from PIL import ImageDraw
        img = Image.new("RGB", (1024, 1024), color=(18, 20, 26))
        draw = ImageDraw.Draw(img)
        for i, line in enumerate([
            "⚠  Image generation unavailable",
            "",
            f"Prompt: {prompt[:70]}{'...' if len(prompt) > 70 else ''}",
            "",
            "All providers are temporarily down.",
            "Please try again in a moment.",
        ]):
            draw.text((60, 410 + i * 38), line, fill=(190, 190, 200))
        img.save(filepath)
        return os.path.abspath(filepath)
    except Exception as pil_e:
        print(f"[ImageGen] PIL fallback failed: {pil_e}")
        return None

# ---------------------------------------------------------------------------
# Image Editing — Stage 1: Gemini multimodal img2img
# ---------------------------------------------------------------------------
def _try_edit_gemini(prompt: str, input_path: str, filepath: str) -> bool:
    print(f"[ImageEdit] Provider: Gemini multimodal edit ({GOOGLE_GEMINI_EDIT_MODEL})")
    if not _has_google_key():
        return False
    try:
        with open(input_path, "rb") as f:
            raw = f.read()
        img_obj = Image.open(BytesIO(raw)).convert("RGB")
        img_obj.thumbnail((1024, 1024), Image.LANCZOS)
        buf = BytesIO()
        img_obj.save(buf, format="JPEG", quality=85)
        img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        models_to_try = list(dict.fromkeys([
            GOOGLE_GEMINI_EDIT_MODEL,
            "gemini-2.0-flash-preview-image-generation",
            GOOGLE_GEMINI_IMAGE_MODEL,
        ]))
        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GOOGLE_API_KEY}"
            payload = {
                "contents": [{
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": img_b64,
                            }
                        },
                        {
                            "text": (
                                "Edit this image following the instruction below. "
                                "Return only the modified image, no text.\n\n"
                                f"Instruction: {prompt}"
                            )
                        },
                    ]
                }],
                "generationConfig": {"responseModalities": ["Image", "Text"]},
            }
            try:
                r = make_session().post(url, json=payload, timeout=45)
                r.raise_for_status()
                data = r.json()
                for candidate in data.get("candidates", []):
                    for part in candidate.get("content", {}).get("parts", []):
                        if "inlineData" in part:
                            img_bytes = base64.b64decode(part["inlineData"]["data"])
                            if save_image_bytes(img_bytes, filepath):
                                print(f"[ImageEdit] Gemini edit success with model: {model}")
                                return True
                print(f"[ImageEdit] Gemini edit ({model}): no inlineData in response — {r.text[:200]}")
            except Exception as model_e:
                print(f"[ImageEdit] Gemini edit ({model}) failed: {safe_error(model_e)}")
    except Exception as e:
        print(f"[ImageEdit] Gemini edit setup failed: {safe_error(e)}")
    return False

# ---------------------------------------------------------------------------
# Image Editing — Stage 2: AI Horde img2img
# ---------------------------------------------------------------------------
def _try_edit_aihorde(prompt: str, input_path: str, filepath: str) -> bool:
    print("[ImageEdit] Provider: AI Horde img2img")
    try:
        with open(input_path, "rb") as f:
            raw = f.read()
        img_obj = Image.open(BytesIO(raw)).convert("RGB")
        img_obj.thumbnail((512, 512), Image.LANCZOS)
        buf = BytesIO()
        img_obj.save(buf, format="PNG")
        source_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        BASE = "https://aihorde.net/api/v2"
        session = make_session()
        session.headers.update({
            "apikey": "0000000000",
            "Content-Type": "application/json",
            "Client-Agent": "LuminaAI:1.0:local",
        })
        payload = {
            "prompt": f"{prompt} ### low quality, blurry",
            "params": {
                "sampler_name": "k_euler_a",
                "cfg_scale": 7,
                "denoising_strength": 0.65,
                "steps": 25,
                "width": 512,
                "height": 512,
                "n": 1,
            },
            "source_image": source_b64,
            "source_processing": "img2img",
            "models": ["Deliberate"],
            "r2": False,
        }
        r_sub = session.post(f"{BASE}/generate/async", json=payload, timeout=20)
        r_sub.raise_for_status()
        job_id = r_sub.json().get("id")
        if not job_id:
            print("[ImageEdit] AI Horde img2img: no job ID")
            return False
        print(f"[ImageEdit]   AI Horde img2img job: {job_id} — polling...")
        for attempt in range(12):
            time.sleep(5)
            rs = session.get(f"{BASE}/generate/status/{job_id}", timeout=10)
            rs.raise_for_status()
            sd = rs.json()
            if sd.get("done"):
                gens = sd.get("generations", [])
                if gens:
                    return save_image_bytes(base64.b64decode(gens[0]["img"]), filepath)
                return False
            print(f"[ImageEdit]   AI Horde img2img: queue {sd.get('queue_position','?')}, ETA {sd.get('wait_time','?')}s")
        print("[ImageEdit] AI Horde img2img: timed out")
    except Exception as e:
        print(f"[ImageEdit] AI Horde img2img failed: {safe_error(e)}")
    return False

# ---------------------------------------------------------------------------
# Image Editing — Stage 3: PIL overlay fallback
# ---------------------------------------------------------------------------
def _try_edit_pil_overlay(prompt: str, input_path: str, filepath: str) -> bool:
    print("[ImageEdit] Provider: PIL overlay fallback")
    try:
        from PIL import ImageDraw
        src = Image.open(input_path).convert("RGB")
        src = src.resize((1024, 1024), Image.LANCZOS)
        overlay = Image.new("RGBA", src.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        # Semi-transparent dark banner at the bottom
        draw.rectangle([(0, 880), (1024, 1024)], fill=(18, 20, 26, 200))
        banner_text = f"✏️ Edit requested: {prompt[:80]}{'...' if len(prompt) > 80 else ''}"
        draw.text((24, 900), banner_text, fill=(220, 220, 240))
        sub_text = "⚠ AI edit providers unavailable — original image shown with prompt overlay."
        draw.text((24, 950), sub_text, fill=(160, 160, 180))
        result = Image.alpha_composite(src.convert("RGBA"), overlay).convert("RGB")
        result.save(filepath)
        return True
    except Exception as e:
        print(f"[ImageEdit] PIL overlay failed: {e}")
    return False

EDIT_PROVIDERS = [
    _try_edit_gemini,
    _try_edit_aihorde,
]

async def edit_image_async(prompt: str, input_image_path: str) -> str | None:
    if not input_image_path or not os.path.exists(input_image_path):
        print(f"[ImageEdit] Source image not found: {input_image_path}")
        return None

    filepath = os.path.join(IMAGE_CACHE_DIR, f"edit_{random.randint(1, 999_999)}.png")

    def _run():
        for fn in EDIT_PROVIDERS:
            try:
                if fn(prompt, input_image_path, filepath):
                    return True
            except Exception as e:
                print(f"[ImageEdit] {fn.__name__} raised: {safe_error(e)}")
        return False

    try:
        if await asyncio.to_thread(_run):
            return os.path.abspath(filepath)
    except Exception as e:
        print(f"[ImageEdit] Chain error: {safe_error(e)}")

    if _try_edit_pil_overlay(prompt, input_image_path, filepath):
        return os.path.abspath(filepath)

    print("[ImageEdit] ⚠ All edit providers failed.")
    return None
