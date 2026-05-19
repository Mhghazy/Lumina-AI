# 🌟 Lumina AI — Comprehensive Technical Documentation

This document provides an in-depth technical breakdown of **Lumina AI**, a sovereign, multi-modal AI virtual character and assistant. Lumina AI combines state-of-the-art Large Language Models, real-time British text-to-speech synthesis, multi-engine surface and dark web research aggregation, and a highly resilient 6-stage image generation pipeline within a modern Gradio web interface.

---

## 🏛️ 1. System Architecture & Data Flow

Lumina AI is structured as a modular, asynchronous web application built on top of **FastAPI**, **Uvicorn**, and **Gradio**. It orchestrates multiple external APIs and local scraping subsystems to deliver seamless conversational and generative experiences.

```mermaid
flowchart TD
    subgraph Frontend [Gradio Web UI / Uvicorn Server]
        UI[Gradio Interface]
        ChatTab[💬 Chat Companion Tab]
        StudioTab[🎨 AI Image Studio Tab]
        UI --> ChatTab
        UI --> StudioTab
    end

    subgraph Middleware [FastAPI Application]
        CSP[CSPMiddleware]
        FastAPI[FastAPI Mount]
        CSP --> FastAPI
    end

    subgraph CoreBackend [main.py Orchestration]
        Router[Brain State Router]
        Preflight[Pre-flight Search Classifier]
        History[Chat History Manager]
        TTS[Edge TTS Engine]
    end

    subgraph ExternalLLMs [LLM Clients]
        Groq[Groq API: Llama 3.3 70B / 3.1 8B]
        Gemma[Google API via OpenAI API: Gemma 4 31B]
    end

    subgraph ScraperSubsystem [scraper.py Multi-Engine Scraper]
        Google[Google Search API]
        Bing[Bing Web Scraper]
        DDG[DuckDuckGo DDGS]
        Wiki[Wikipedia API]
        Ahmia[Ahmia / Torch Dark Web]
    end

    subgraph ImageSubsystem [image_gen.py 6-Stage Image Pipeline]
        Img1[1. Pollinations AI]
        Img2[2. Together AI FLUX]
        Img3[3. Craiyon v3]
        Img4[4. Google Imagen 4]
        Img5[5. Gemini 3.1 Flash]
        Img6[6. AI Horde GPU Cluster]
        PIL[PIL Fallback Error Card]
    end

    subgraph Storage [Local Filesystem Caches]
        ChatStore[chats/*.json]
        AudioStore[audio_cache/*.mp3]
        ImageStore[image_cache/*.png]
    end

    Frontend --> Middleware
    Middleware --> CoreBackend
    ChatTab --> Router
    StudioTab --> ImageSubsystem
    Router --> Preflight
    Preflight -- Needs Search --> ScraperSubsystem
    Router --> ExternalLLMs
    ExternalLLMs -- [IMAGE_PROMPT: ...] --> ImageSubsystem
    ExternalLLMs -- Text Output --> TTS
    History <--> ChatStore
    TTS --> AudioStore
    ImageSubsystem --> ImageStore
```

---

## 📁 2. File-by-File Technical Deep Dive & Capabilities

### `main.py`
**Purpose:** The central entry point and orchestration engine of the application. It establishes the FastAPI server, defines the Gradio frontend layout, manages chat persistence, routes LLM requests based on persona brain states, classifies search intent, and synthesizes speech.

#### Key Capabilities & Implementation Details:
- **Asynchronous Server & Middleware Setup:** Mounts the Gradio app onto a FastAPI instance running via Uvicorn (`127.0.0.1:7861`). Implements `CSPMiddleware` to inject a highly permissive `Content-Security-Policy` header, ensuring external media, BLOBs, and Web Workers load without browser CORS or CSP blocks.
- **Windows Event Loop Patching:** Explicitly sets `asyncio.WindowsSelectorEventLoopPolicy()` to prevent `ProactorEventLoop` instability on Windows. Monkey-patches `_ProactorBasePipeTransport._call_connection_lost` to cleanly silence benign `WinError 10054` connection reset tracebacks during Edge TTS streaming.
- **Multi-Client LLM Routing:** Initializes both `AsyncGroq` (for Llama 3.3 70B / Llama 3.1 8B) and `AsyncOpenAI` (configured for Google's Gemini/Gemma API base URL `https://generativelanguage.googleapis.com/v1beta/openai/` using model `gemma-4-31b-it`).
- **5-Tier Brain State Router:** Dynamically configures system prompts, active LLM clients, temperature, and context length based on user selection:
  1. `🧠 Conscious Mode`: Uses Groq Llama 3.3 70B (`temp=0.7`, `max_tokens=2048`). Witty, British, genius polymath.
  2. `⚡ Fast Mode`: Uses Google Gemma 4 31B (`temp=0.7`, `max_tokens=1024`). Snappy, ultra-concise, engaging.
  3. `🔬 Deep Analysis Mode`: Uses Google Gemma 4 31B (`temp=0.5`, `max_tokens=4096`). Rigorous, highly structured, analytical markdown formatting.
  4. `🍸 Chill Mode`: Uses Groq Llama 3.1 8B (`temp=0.8`, `max_tokens=1024`). Breezy, conversational, relaxed gut-instinct answers.
  5. `💤 Subconscious Mode`: Uses Groq Llama 3.1 8B (`temp=1.2`, `max_tokens=2048`). Abstract, surreal digital dreaming / sleep-talking.
- **Pre-flight Search Intent Classification:** Before generating a response, if internet access is enabled, it executes a lightweight LLM pre-flight check (`json_object` format on Llama, strict prompt on Gemma) to determine if the query requires live web/dark web data. If true, it invokes `scraper.py` inside `asyncio.to_thread` to prevent event loop blocking.
- **Dynamic Image Prompt Injection:** Scans LLM output streams for `[IMAGE_PROMPT: <prompt>]` regex tags. Upon detection, it triggers `generate_image_async`, verifies the local file, and replaces the tag with Gradio-compatible markdown (`![Generated Image](/gradio_api/file=...)`).
- **Real-Time British TTS:** Sanitizes text output (stripping markdown, code blocks, and emojis) and streams it to `edge-tts` using the British female voice `en-GB-SoniaNeural`, saving artifacts to `audio_cache/`.
- **Chat History Persistence:** Automatically serializes chat sessions into JSON files within the `chats/` directory, generating dynamic titles from initial user prompts and maintaining updated timestamps.

---

### `scraper.py`
**Purpose:** A robust, multi-threaded search aggregator and scraper designed to fetch, parse, deduplicate, and format live results from surface web engines and Tor dark web gateways.

#### Key Capabilities & Implementation Details:
- **Anti-Bot Evasion & Headers:** Implements a rotating pool of modern browser `User-Agent` strings alongside realistic `Accept`, `Accept-Encoding`, and `Accept-Language` headers to bypass basic bot detection and WAFs.
- **Multi-Engine Surface Web Scraping:**
  - `Google`: Uses `googlesearch-python` for advanced programmatic scraping.
  - `Bing`: Directly fetches Bing search result pages (`https://www.bing.com/search`) and parses DOM nodes (`li.b_algo`, `h2 a`, `div.b_caption`) via Beautiful Soup 4 and Python's built-in `html.parser`.
  - `DuckDuckGo`: Integrates `ddgs` (`DDGS`), with a fallback to `duckduckgo_search`, to support specialized search modalities including `text`, `images`, `videos`, and `news`.
  - `Wikipedia`: Queries the official Wikipedia API, handling disambiguation exceptions gracefully to return verified page summaries.
- **Dark Web / Tor Index Scraping:**
  - `Ahmia`: Scrapes `ahmia.fi` (the primary clearweb gateway to Tor hidden services). Parses `ol.searchResults li.result`, extracts onion redirect URLs (`redirect_url=`), onion hosts (`cite`), descriptions, and indexing age.
  - `Torch`: Implements a fallback clearweb scraper targeting `torchdarkweb.com` if Ahmia is unreachable.
- **Deduplication & Sanitization:** Filters aggregated results to remove redundant URLs across different search engines, ensuring clean context injection for the LLM.
- **Rich Media Markdown Formatting:** 
  - `format_images_for_chat`: Parses image search results into Gradio markdown grids, prioritizing highly reliable CDN-cached thumbnails over fragile third-party direct image links.
  - `format_videos_for_chat`: Constructs clickable markdown video cards complete with publisher metadata, duration tags, and descriptions.

---

### `image_gen.py`
**Purpose:** A bulletproof, asynchronous 6-stage image generation engine that guarantees visual output by cascading through premium, experimental, free, and distributed AI image providers, ending with a local PIL fallback.

#### Key Capabilities & Implementation Details:
- **Cloudflare & SSL Evasion:** Configures custom `requests.Session` objects with `verify=False` (suppressing `urllib3` insecure request warnings) and injects rigorous browser headers (`Origin`, `Referer`, `Sec-Fetch-Mode`) to bypass Cloudflare WAFs.
- **PIL Image Verification:** Protects the frontend from corrupt data or lazy-loading HTML queue pages masquerading as images. Every downloaded payload is loaded into `PIL.Image`, verified via `img.verify()`, and re-opened before saving to `image_cache/`.
- **6-Stage Cascading Failover Hierarchy:**
  1. `Stage 1: Pollinations AI (Default)`: Hits the direct URL generation endpoint `image.pollinations.ai`. Implements a 2-attempt retry loop with 3-second delays.
  2. `Stage 2: Together AI`: Initializes the `Together` SDK to invoke `FLUX.1-schnell-Free` when `TOGETHER_API_KEY` is provided. Handles both `b64_json` and direct URL response formats.
  3. `Stage 3: Craiyon v3`: Executes a POST request to `api.craiyon.com/v3` with strict CORS/Sec-Fetch headers and version token `35s5hfwn9n78gb06`, decoding the resulting base64 JPEG array.
  4. `Stage 4: Google Imagen`: Calls `generativelanguage.googleapis.com` using the `GOOGLE_IMAGEN_MODEL` (defaults to `imagen-4.0-generate-001`) with the user's dedicated Google API key. Parses the `bytesBase64Encoded` base64 payload.
  5. `Stage 5: Gemini 3.1 Flash Image`: Queries `generativelanguage.googleapis.com` using the `GOOGLE_GEMINI_IMAGE_MODEL` (defaults to `gemini-3.1-flash-image-preview`) with image response modality enabled, extracting `inlineData` base64 payloads.
  6. `Stage 6: AI Horde`: Connects to `aihorde.net/api/v2` using the anonymous key `0000000000`. Submits an asynchronous generation job (`k_euler_a`, `Deliberate` model) and polls the status endpoint every 4 seconds for up to 4 attempts.
- **Local PIL Error Card Fallback:** If all 6 cloud stages experience catastrophic simultaneous outages, it dynamically draws a beautiful dark-themed (`#12141A`) error card using `PIL.ImageDraw` containing the truncated prompt and status warnings. This ensures Gradio never receives a `None` object and prevents frontend UI crashes.

---

### `requirements.txt`
**Purpose:** Defines the core third-party Python package dependencies required to execute the Lumina AI environment.

#### Contents & Dependency Mapping:
```text
groq
gradio
python-dotenv
edge-tts
requests
beautifulsoup4
ddgs
duckduckgo-search
googlesearch-python
wikipedia
```
*Note: Additional libraries utilized across the codebase (e.g., `fastapi`, `uvicorn`, `starlette`, `openai`, `urllib3`, `pillow`, `together`) are either installed alongside Gradio/FastAPI or managed within the user's local Python 3.11 environment.*

---

### `README.md`
**Purpose:** The primary user-facing documentation providing an overview of Lumina's persona, prerequisite requirements, installation steps, and launch instructions.

#### Key Sections:
- **Persona Description:** Details Lumina's character traits — British wit, humor, polymath expertise (CS, physics, biology, medicine), and artistic creativity.
- **Prerequisites & Setup:** Guides users on cloning the repository, installing `requirements.txt`, and configuring the `GROQ_API_KEY` inside a `.env` file.
- **Execution & Features:** Explains how to launch the app via `python main.py` and highlights core features like high-speed streaming, British Edge TTS, and the Gradio UI.

---

### `implementation_plan.md`
**Purpose:** An architectural blueprint and historical tracking document establishing the foundational decisions made during the initial inception of Lumina AI.

#### Key Sections:
- **Tech Stack & Model Selection:** Documents the deliberate choice of Gradio for rapid UI development and Groq Llama 3 70B for lightning-fast reasoning.
- **Open Questions & Verification:** Outlines initial design considerations regarding UI theming and defines the manual verification checklist used to validate Lumina's persona behavior.

---

### `.gitignore`
**Purpose:** Specifies untracked files and directories to prevent sensitive credentials, virtual environments, and local cache bloat from entering Git version control.

#### Exclusions:
- **Environments:** `.env`, `.venv`, `env/`, `venv/`
- **Compiled Artifacts:** `__pycache__/`, `*.pyc`, `*.pyo`, `*.pyd`
- **Local Data Caches:** `audio_cache/`, `chats/`

---

## ⚙️ 3. Summary of Subsystem Capabilities

| Subsystem | Primary Technologies | Core Capabilities |
| :--- | :--- | :--- |
| **Frontend UI** | Gradio Blocks & Tabs | Multi-tab interface (Chat + AI Studio), chat history sidebar, brain state selectors, search engine toggles, real-time audio autoplay, multi-style dropdowns. |
| **Conversational AI** | Groq Llama 3.3 / Google Gemma 4 | 5 distinct persona modes, emotional intelligence switching (humor to empathy), autonomous prompt generation for images and search. |
| **Web Research** | BeautifulSoup, DDGS, Google/Wiki APIs | Surface web scraping, Tor dark web indexing (`ahmia.fi`), automatic deduplication, rich markdown media embedding. |
| **Image Generation** | Pollinations, Together FLUX, Craiyon v3, Google Imagen, Gemini Flash, AI Horde | 6-stage fault-tolerant failover, Cloudflare WAF evasion, lazy-generation retry loops, PIL integrity verification, fail-safe error cards. |
| **Speech Synthesis** | Edge TTS (`en-GB-SoniaNeural`) | On-the-fly text sanitization (removing markdown/emojis), asynchronous audio file caching, Windows socket error suppression. |
| **Security & Server** | FastAPI, Uvicorn, Starlette Middleware | Permissive Content-Security-Policy injection, environment variable management, robust exception handling across all endpoints. |
