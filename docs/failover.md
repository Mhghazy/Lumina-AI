# 🛡️ Failover Design

## 🛡️ Multimodal Failover Design

Lumina achieves high availability through deep fallback cascades. By utilizing a "try-except chain", the system guarantees a response even when third-party APIs experience downtime or rate-limit blocks.

### Image Generation Failover (6-Stage)
If the primary image generator fails, the `generate_image_async()` function automatically cascades down to the next provider:
1. **Pollinations AI**: Extremely fast, no authentication required.
2. **Together AI (FLUX)**: High-quality models using `TOGETHER_API_KEY`.
3. **Craiyon v3**: Web scraping-based fallback using custom headers.
4. **Google Imagen 4**: High-fidelity authenticated generation.
5. **Gemini 3.1 Flash**: Multimodal content generation fallback.
6. **AI Horde**: A crowdsourced, anonymous GPU cluster (polls for completion).

If all 6 providers fail, the system **never crashes**. Instead, it generates a fallback PIL (Python Imaging Library) error card locally, rendering the prompt and a generic "API Unavailable" message so the user interface remains stable.

### Audio and Search Failovers
- **TTS**: Handled via `edge-tts`. If the websocket connection to Microsoft drops, the `TTS_TIMEOUT_SECONDS` config catches the timeout, safely suppressing the error so the text response still renders for the user.
- **Search Engine Scrapers**: If `googlesearch-python` triggers a 429 Rate Limit, Lumina automatically falls back to DuckDuckGo (`ddgs`), and subsequently Wikipedia. For Dark Web searches, it attempts Ahmia first, and falls back to Torch if `.onion` indexing is blocked.

---
## 🌌 Distributed Image Pipeline

The `lumina/image/engine.py` orchestrates a decentralized approach to image synthesis.

### Pipeline Architecture
- **Asynchronous Execution**: Because image generation can take anywhere from 3 seconds (Pollinations) to 2 minutes (AI Horde queue), the entire failover chain is wrapped in `asyncio.to_thread()`. This prevents the slow synchronous HTTP requests (`requests.Session().post`) from blocking Gradio's main asynchronous event loop.
- **Image Editing (img2img)**: For the "AI Image Studio" tab, Lumina performs a 3-stage edit fallback:
  1. **Gemini Multimodal**: Passes the base64-encoded image and text instruction directly to the `gemini-2.0-flash` vision model.
  2. **AI Horde (img2img)**: Resizes the source image, applies `denoising_strength=0.65`, and polls the distributed GPU workers.
  3. **PIL Overlay**: If both fail, Lumina draws a semi-transparent banner natively over the original image detailing the prompt, ensuring the user gets *some* visual feedback.

