import os
import time
import base64
import random
import asyncio
import re
import requests
import urllib.parse
import urllib3

from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

IMAGE_CACHE_DIR = "image_cache"
os.makedirs(IMAGE_CACHE_DIR, exist_ok=True)

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GOOGLE_IMAGEN_MODEL = os.environ.get("GOOGLE_IMAGEN_MODEL", "imagen-4.0-generate-001")
GOOGLE_GEMINI_IMAGE_MODEL = os.environ.get("GOOGLE_GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image-preview")
IMAGE_DOWNLOAD_TIMEOUT_SECONDS = 25

def _safe_error(exc: Exception) -> str:
    return re.sub(r"([?&](?:key|api_key)=)[^&\s]+", r"\1<redacted>", str(exc))

def _has_google_key() -> bool:
    if GOOGLE_API_KEY:
        return True
    print("[ImageGen] Google provider skipped: GOOGLE_API_KEY is not set")
    return False

def _make_session() -> requests.Session:
    s = requests.Session()
    s.verify = False
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
    })
    return s

def _save_image_bytes(data: bytes, filepath: str) -> bool:
    try:
        img = Image.open(BytesIO(data))
        img.verify()
        img = Image.open(BytesIO(data))
        img.save(filepath)
        return True
    except Exception as e:
        print(f"[ImageGen] PIL validate error: {_safe_error(e)}")
        return False

def _download_url(url: str, filepath: str, retries: int = 2, wait: float = 3.0) -> bool:
    session = _make_session()
    for attempt in range(1, retries + 1):
        try:
            r = session.get(url, timeout=IMAGE_DOWNLOAD_TIMEOUT_SECONDS, allow_redirects=True)
            ct = r.headers.get("Content-Type", "").lower()
            print(f"[ImageGen]   attempt {attempt}: HTTP {r.status_code}, {ct}")
            if r.status_code == 200 and "image" in ct:
                return _save_image_bytes(r.content, filepath)
            if attempt < retries:
                print(f"[ImageGen]   retrying in {wait}s...")
                time.sleep(wait)
        except Exception as e:
            print(f"[ImageGen]   attempt {attempt} error: {_safe_error(e)}")
            if attempt < retries:
                time.sleep(3)
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
        r = _make_session().post(url, json=payload, timeout=8)
        r.raise_for_status()
        preds = r.json().get("predictions", [])
        if preds:
            img_b64 = preds[0].get("bytesBase64Encoded", "")
            if img_b64:
                return _save_image_bytes(base64.b64decode(img_b64), filepath)
        print(f"[ImageGen] Imagen 3 response: {r.text[:200]}")
    except Exception as e:
        print(f"[ImageGen] Imagen 3 failed: {_safe_error(e)}")
    return False

# ---------------------------------------------------------------------------
# Stage 2: Gemini 2.0 Flash image generation (user's existing API key)
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
        r = _make_session().post(url, json=payload, timeout=8)
        r.raise_for_status()
        for candidate in r.json().get("candidates", []):
            for part in candidate.get("content", {}).get("parts", []):
                if "inlineData" in part:
                    img_bytes = base64.b64decode(part["inlineData"]["data"])
                    return _save_image_bytes(img_bytes, filepath)
        print(f"[ImageGen] Gemini Flash image: no inlineData in response")
    except Exception as e:
        print(f"[ImageGen] Gemini Flash image failed: {_safe_error(e)}")
    return False

# ---------------------------------------------------------------------------
# Stage 3: Pollinations (no model param — uses their default)
# ---------------------------------------------------------------------------
def _try_pollinations(prompt: str, filepath: str) -> bool:
    encoded = urllib.parse.quote(prompt)
    seed = random.randint(1, 999_999)
    url = f"https://image.pollinations.ai/prompt/{encoded}?nologo=true&seed={seed}&width=1024&height=1024"
    print("[ImageGen] Provider: Pollinations")
    return _download_url(url, filepath, retries=2, wait=3)

# ---------------------------------------------------------------------------
# Stage 4: Craiyon (free, no auth, returns base64)
# ---------------------------------------------------------------------------
def _try_craiyon(prompt: str, filepath: str) -> bool:
    print("[ImageGen] Provider: Craiyon")
    try:
        session = _make_session()
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
            return _save_image_bytes(base64.b64decode(images[0]), filepath)
        print("[ImageGen] Craiyon: no images in response")
    except Exception as e:
        print(f"[ImageGen] Craiyon failed: {_safe_error(e)}")
    return False

# ---------------------------------------------------------------------------
# Stage 5: AI Horde (free distributed GPU, anonymous key)
# ---------------------------------------------------------------------------
def _try_aihorde(prompt: str, filepath: str) -> bool:
    print("[ImageGen] Provider: AI Horde")
    try:
        BASE = "https://aihorde.net/api/v2"
        session = _make_session()
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
                    return _save_image_bytes(base64.b64decode(gens[0]["img"]), filepath)
                return False
            print(f"[ImageGen]   AI Horde: queue {sd.get('queue_position','?')}, ETA {sd.get('wait_time','?')}s")
        print("[ImageGen] AI Horde: timed out")
    except Exception as e:
        print(f"[ImageGen] AI Horde failed: {_safe_error(e)}")
    return False

# ---------------------------------------------------------------------------
# Stage 6: Together AI (when credits are available)
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
            return _save_image_bytes(base64.b64decode(item.b64_json), filepath)
        url = getattr(item, "url", None) or item["url"]
        return _download_url(url, filepath, retries=2, wait=3)
    except Exception as e:
        print(f"[ImageGen] Together AI failed: {_safe_error(e)}")
    return False

# ---------------------------------------------------------------------------
# Provider chain
# ---------------------------------------------------------------------------
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
                print(f"[ImageGen] {fn.__name__} raised: {_safe_error(e)}")
        return False

    try:
        if await asyncio.to_thread(_run):
            return os.path.abspath(filepath)
    except Exception as e:
        print(f"[ImageGen] Chain error: {_safe_error(e)}")

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
