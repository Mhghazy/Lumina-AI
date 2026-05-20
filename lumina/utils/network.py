import os
import re
import random
import time
import requests
import urllib3
from PIL import Image
from io import BytesIO

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

IMAGE_DOWNLOAD_TIMEOUT_SECONDS = 25

def safe_error(exc: Exception) -> str:
    """Mask key parameters in errors to avoid printing secrets in logs."""
    return re.sub(r"([?&](?:key|api_key)=)[^&\s]+", r"\1<redacted>", str(exc))

def get_headers():
    """Generate typical headers with a randomized user agent."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "DNT": "1",
    }

def make_session() -> requests.Session:
    """Create a persistent requests session with custom headers and disabled verification."""
    s = requests.Session()
    s.verify = False
    s.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
    })
    return s

def save_image_bytes(data: bytes, filepath: str) -> bool:
    """Verify and write raw image bytes to disk."""
    try:
        img = Image.open(BytesIO(data))
        img.verify()
        # Re-open after verification since verify() closes the stream
        img = Image.open(BytesIO(data))
        img.save(filepath)
        return True
    except Exception as e:
        print(f"[ImageGen] PIL validate error: {safe_error(e)}")
        return False

def download_url(url: str, filepath: str, retries: int = 2, wait: float = 3.0) -> bool:
    """Download an image from a URL and save it to disk with fallback retry logic."""
    session = make_session()
    for attempt in range(1, retries + 1):
        try:
            r = session.get(url, timeout=IMAGE_DOWNLOAD_TIMEOUT_SECONDS, allow_redirects=True)
            ct = r.headers.get("Content-Type", "").lower()
            print(f"[ImageGen]   attempt {attempt}: HTTP {r.status_code}, {ct}")
            if r.status_code == 200 and "image" in ct:
                return save_image_bytes(r.content, filepath)
            if attempt < retries:
                print(f"[ImageGen]   retrying in {wait}s...")
                time.sleep(wait)
        except Exception as e:
            print(f"[ImageGen]   attempt {attempt} error: {safe_error(e)}")
            if attempt < retries:
                time.sleep(3)
    return False
