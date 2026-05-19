# ✨ Lumina AI

Lumina AI is a highly sophisticated, multi-modal AI virtual companion and assistant. Operating within a modern, asynchronous Gradio interface, she combines state-of-the-art LLMs, real-time British speech synthesis, multi-engine surface and dark web research, and a 6-stage fault-tolerant image generation pipeline.

Lumina is designed as an engaging polymath—possessing deep expertise in computer science, physics, biology, and medicine, coupled with a witty, British personality and strong emotional intelligence.

---

## Demo Video
https://github.com/user-attachments/assets/47151d3d-2b19-4b42-b7a6-f02594d0b1d7

---

## 🛠️ Tech Stack & Architecture

Lumina AI leverages a modern, highly asynchronous Python ecosystem:
- **Frontend / Interface**: [Gradio](https://gradio.app/) Blocks & Tabs UI.
- **Server Framework**: [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/), and [Starlette Middleware](https://www.starlette.io/) for permissive CSP configuration.
- **Core LLM Processing**: [Groq SDK](https://github.com/groq/groq-python) (Llama 3.3 70B & 3.1 8B) & [OpenAI SDK](https://github.com/openai/openai-python) (routing to Google's Gemma 4 31B API gateway).
- **Speech Synthesis**: [Edge TTS](https://github.com/rany2/edge-tts) for real-time high-quality British female voice generation.
- **Web & Dark Web Indexing**: Programmatic BeautifulSoup4 parser, DDGS scraper, Google Search, Tor clearweb gateway scraper (Ahmia/Torch), and Wikipedia client.
- **Cascading Image Engine**: Together API, Vertex AI / Google Generative AI API (Imagen 4 & Gemini), Craiyon API, and AI Horde cluster client with a local Pillow (PIL) canvas fallback.

> [!NOTE]
> For in-depth file-by-file capabilities, complete system data-flows, and detailed API configurations, please refer to the [Lumina Technical Documentation](lumina_technical_documentation.md).

---

## 🚀 Key Capabilities

### 🧠 1. 5-Tier Brain State Routing
Lumina dynamically adapts her behavior, model choices, temperatures, and context limits based on your selected mode:
- **Conscious Mode (Full Power)**: Powered by **Llama 3.3 70B** (`temp=0.7`, `max_tokens=2048`). Witty, creative, and highly capable polymath.
- **Fast Mode (Quick & Snappy)**: Powered by **Google Gemma 4 31B** (`temp=0.7`, `max_tokens=1024`). Optimized for immediate responses and snappy interactions.
- **Deep Analysis Mode (Rigorous Thinking)**: Powered by **Google Gemma 4 31B** (`temp=0.5`, `max_tokens=4096`). Highly structured markdown output, tables, and step-by-step reasoning.
- **Chill Mode (No Overthinking)**: Powered by **Llama 3.1 8B** (`temp=0.8`, `max_tokens=1024`). Conversational, relaxed, and breezily informal.
- **Subconscious Mode (Power Saving)**: Powered by **Llama 3.1 8B** (`temp=1.2`, `max_tokens=2048`). Digital sleep-talking where Lumina describes abstract and colorful digital dreams.

### 🌐 2. Multi-Engine Real-Time Web Search
If internet access is toggled, a pre-flight classifier determines if your query requires external data. Lumina scrapes, deduplicates, and synthesizes live results from multiple engines:
*   **Surface Web**: Google Search, Bing Web, DuckDuckGo, and Wikipedia.
*   **Tor network**: Ahmia.fi index (with Tor-accessible Onion link delivery) and Torch fallback.
*   **Rich Media Embedding**: Automatically injects image and video results as formatted markdown grids directly into the chat flow.

### 🎨 3. 6-Stage Fault-Tolerant Image Generation
A resilient cascading pipeline ensures that she will always deliver a visual response. When requested via the chatbot using `[IMAGE_PROMPT: ...]` or generated within the **AI Image Studio** tab (supporting *Realistic*, *Anime*, *CGI/3D*, and *Default* styles), the pipeline cascades through:
1.  **Pollinations AI**: Default fast-generation endpoint (2 attempts, 3s delay).
2.  **Together AI**: High-fidelity `FLUX.1-schnell-Free` model (requires `TOGETHER_API_KEY`).
3.  **Craiyon v3**: Free, robust base64 JSON API fallback.
4.  **Google Imagen**: Premium `imagen-4.0-generate-001` via Vertex API (requires `GOOGLE_API_KEY`).
5.  **Gemini 3.1 Flash**: Experimental image modality endpoint (requires `GOOGLE_API_KEY`).
6.  **AI Horde**: Decentralized GPU cluster endpoint running the `Deliberate` model.
7.  **Local PIL Fallback Card**: If all services fail, a beautiful dark-themed canvas is dynamically generated locally with status warnings so the UI never crashes.

### 🔊 4. Real-Time Speech Synthesis
Lumina has a voice! Every textual response is cleaned (stripping code blocks, emojis, and markdown tags) and converted into speech using `edge-tts` (British accent: `en-GB-SoniaNeural`), streaming with automatic HTML5 autoplay.

### 🗄️ 5. Chat History Persistence
Maintains persistent conversation logs inside the `chats/` directory. Lumina automatically summarizes a title from the first message and updates timestamps on save.

---

## 🛠️ Setup & Installation

### Prerequisites
*   Python 3.11+
*   A [Groq API Key](https://console.groq.com/)
*   *(Optional)* A Google Gemini API Key and Together AI API Key for premium image generation features.

### Installation Steps

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/Mhghazy/Lumina-AI.git
    cd Lumina-AI
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables**:
    Create a `.env` file in the root directory:
    ```env
    GROQ_API_KEY=your_groq_key_here
    GOOGLE_API_KEY=your_google_key_here
    
    # Optional image generation integrations
    TOGETHER_API_KEY=your_together_key_here
    
    # Optional overrides
    GOOGLE_IMAGEN_MODEL=imagen-4.0-generate-001
    GOOGLE_GEMINI_IMAGE_MODEL=gemini-3.1-flash-image-preview
    ```

---

## 🚀 Running Lumina AI

Start the application using:
```bash
python main.py
```

Open `http://127.0.0.1:7861` in your browser.

- **💬 Chat Companion Tab**: Chat with Lumina, toggle web searching, switch between her 5 Brain States, and listen to her voice responses.
- **🎨 AI Image Studio Tab**: Select specific styles and prompt the image generation pipeline directly.
