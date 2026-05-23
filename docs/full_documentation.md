# 📖 Lumina AI — Full Single-Page Documentation

*This document contains all architectural, security, API, and ADR documentation combined onto a single page for easy searching and printing.*

---

# 🏛️ Architecture

## 🏛️ System Architecture & Data Flow

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

    subgraph CoreBackend [lumina/ Package Orchestration]
        Router[Brain State Router]
        Preflight[Pre-flight Search Classifier]
        History[Chat History Manager]
        TTS[Edge TTS Engine]
    end

    subgraph ExternalLLMs [LLM Clients]
        Groq[Groq API: Llama 3.3 70B / 3.1 8B]
        Gemma[Google API via OpenAI API: Gemma 4 31B]
    end

    subgraph ScraperSubsystem [lumina/search/scraper.py Multi-Engine Scraper]
        Google[Google Search API]
        Bing[Bing Web Scraper]
        DDG[DuckDuckGo DDGS]
        Wiki[Wikipedia API]
        Ahmia[Ahmia / Torch Dark Web]
    end

    subgraph ImageSubsystem [lumina/image/engine.py 6-Stage Image Pipeline]
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

## 💾 Memory Persistence Design

Chat history in Lumina is designed to be persistent, portable, and fault-tolerant.

### History Serialization (`history.py`)
All conversations are saved as JSON blobs in the `chats/` directory.

- **Data Structure**:
```json
{
  "id": "uuid4",
  "title": "Explain quantum physics...",
  "updated_at": "2026-05-22 14:30",
  "history": [
    {"role": "user", "content": "Explain quantum physics"},
    {"role": "assistant", "content": "Quantum physics is..."}
  ]
}
```

### Auto-Titling and Flattening
- **Title Generation**: `save_chat()` automatically extracts the very first user message, converts it to a string, and truncates it to 30 characters to dynamically name the chat session in the UI sidebar.
- **Robust Parsing**: Gradio 4+ occasionally returns history as tuples (`(user_msg, bot_msg)`) or nested `FileData` dictionaries (when users upload images). The `extract_text_content()` recursive helper flattens these complex structures into clean strings before they are serialized to JSON or sent to the TTS engine.

## 📊 Comprehensive Architectural Diagrams

The following diagrams illustrate the high-level interactions, the internal orchestration, the complete request lifecycle, and the production deployment architecture of Lumina AI.

### 1. System-Wide Use Case Diagram
This diagram illustrates the primary actions a human user can take and how those actions connect to the autonomous orchestration handled by the Lumina Backend Core.

```mermaid
flowchart LR
    subgraph Client [Web Browser / Local Machine]
        User([👤 User])
    end
    
    Lumina([🤖 Lumina Backend Core])
    Engine([🧠 LLM Inference Engine])
    
    User --> UC1(💬 Chat with AI Companion)
    User --> UC2(🧠 Select Brain State Persona)
    User --> UC3(🎨 Generate Images)
    User --> UC4(✏️ Edit Images via Multimodal)
    User --> UC5(📖 Review Conversation History)
    
    %% Connections between User intents and Backend Execution
    UC1 --> Lumina
    UC3 --> Lumina
    UC4 --> Lumina
    
    Lumina --> BUC1(🔍 Classify Search Intent)
    Lumina --> BUC2(🌐 Scrape Surface/Dark Web)
    Lumina --> BUC4(🖼️ Cascade Image Generation)
    Lumina --> BUC5(🗣️ Synthesize Speech)
    Lumina --> BUC6(💾 Cache Artifacts to Disk)
    
    %% Feedback loops returning the data
    BUC2 -.->|Return Context| Lumina
    BUC4 -.->|Return Image| User
    BUC5 -.->|Return Audio| User
    
    Lumina ==>|Compile Prompt & Context| Engine
    Engine ==>|Stream Response| User
```

## 🧠 Neural Network & Model Architecture

Lumina AI implements a hybrid, multi-modal neural network orchestration stack designed to optimize reasoning fidelity, response latency, operation cost, and high availability. Rather than executing a single local model with massive compute requirements, Lumina distributes inference workloads across specialized cloud-hosted LLM clusters, decentralized diffusion pipelines, and neural text-to-speech synthesis networks.

The system partitions workloads across three main neural layers:
1. **Cognitive Reasoning Layer** (Text-to-Text & Tool Routing)
2. **Visual Synthesis Layer** (Text-to-Image & Multimodal img2img)
3. **Acoustic Synthesis Layer** (Text-to-Speech)

### 📊 Model Orchestration & Modality Flow

The following diagram maps out how different inputs and modalities flow through Lumina's dynamic neural routing architecture:

```mermaid
flowchart TD
    subgraph Inputs [User Modalities]
        Prompt["Prompt (Text)"]
        InImage["Source Image (Multi-res RGB)"]
    end

    subgraph CognitiveLLM [Cognitive & Routing Layer]
        L33["Groq LLaMA 3.3 (70B-Versatile)"]
        L31["Groq LLaMA 3.1 (8B-Instant)"]
        G4["Google Gemma 4 (31B-IT)"]
    end

    subgraph DiffusionImage [Image Diffusion Layer]
        Flux["FLUX.1-schnell (12B Flow Transformer)"]
        Imagen["Google Imagen 4"]
        GeminiIm["Gemini 3.1 Flash Image Gen"]
        Horde["Stable Diffusion v1.5 Deliberate"]
        Craiyon["Craiyon v3 Photo Synthesis"]
        Pollinations["Pollinations AI Generator"]
    end

    subgraph AudioSynth [Speech Synthesis Layer]
        EdgeTTS["Microsoft Edge-TTS Neural Speech"]
    end

    Prompt --> L31
    L31 -- "Pre-flight Intent Classification" --> Router[Brain State Router]
    Router -- "Conscious (Default)" --> L33
    Router -- "Fast / Analysis" --> G4
    Router -- "Chill / Subconscious" --> L31

    L33 & G4 & L31 -- "Text Generation" --> EdgeTTS
    L33 & G4 & L31 -- "Generate '[IMAGE_PROMPT: ...]'" --> DiffusionImage
    InImage & Prompt -- "1. Vision-to-Image Edit" --> GeminiEdit["Gemini 2.0 Flash Vision Edit"]
    InImage & Prompt -- "2. Latent Diffusion Edit" --> SDimg2img["AI Horde img2img Deliberate"]
```

---

### 1. Cognitive Reasoning Layer (LLMs)

Lumina delegates text processing, intent classification, and character-driven response generation using a 5-tier dynamic routing configuration:

| Model Name | API Provider | Parameters | Attention / Architecture Features | Context Window | Operational Role |
|---|---|---|---|---|---|
| **LLaMA 3.3 70B** | Groq | 70 Billion | Grouped-Query Attention (GQA), Rotary Position Embeddings (RoPE) | 128,000 tokens | **Conscious (Default)** mode. Primary cognitive engine. Used for complex coding, logical reasoning, and creative writing. |
| **Gemma 4 31B** | Google (OpenAI-compatible) | 31 Billion | Multi-Query Attention, GeGLU activation, RoPE | 8,192 tokens | **Fast & Deep Analysis** modes. High-speed reasoning, deep reading, and document research. |
| **LLaMA 3.1 8B** | Groq | 8 Billion | Grouped-Query Attention (GQA), RoPE | 128,000 tokens | **Chill & Subconscious** modes. Lightweight conversational partner, pre-flight search intent classification. |

#### Pre-flight Intent Classification (`classifier.py`)
To prevent wasting high-tier tokens, Lumina routes incoming messages to a lightweight classifier model (`L31` or `G4` depending on the current mode). This model evaluates the prompt and the last two chat history turns using a few-shot JSON formatting schema to output:
```json
{
  "needs_search": true,
  "query": "search query text",
  "type": "text"
}
```
If `needs_search` is true, the system performs external scraping before sending the concatenated context to the primary generative model.

---

### 2. Visual Synthesis Layer (Text-to-Image & Edit)

When the cognitive layer emits an `[IMAGE_PROMPT: ...]` command, the image subsystem invokes a **6-stage cascade** to synthesize images, falling back sequentially if rate limits or outages are encountered.

```mermaid
flowchart LR
    Start([Trigger Engine]) --> P1[1. Pollinations AI]
    P1 -- Error --> P2[2. Together FLUX.1]
    P2 -- Error --> P3[3. Craiyon v3]
    P3 -- Error --> P4[4. Google Imagen 4]
    P4 -- Error --> P5[5. Gemini 3.1 Flash]
    P5 -- Error --> P6[6. AI Horde SD]
    P6 -- Error --> Fallback[PIL Error Card]
```

#### Text-to-Image Model Parameters:
- **FLUX.1-schnell**: A 12-billion parameter rectified flow transformer model developed by Black Forest Labs. It is optimized for high-fidelity prompt adherence, realistic text rendering, and rapid 4-step generation.
- **Google Imagen 4**: Google's text-to-image diffusion model, specializing in high-fidelity compositions, realistic lighting, and text generation.
- **Stable Diffusion v1.5 (Deliberate)**: Fine-tuned weight configuration run on crowdsourced GPU nodes, utilizing a traditional UNet latent diffusion architecture.

#### Vision-Conditioned Image Editing (img2img):
When editing an uploaded image, the system utilizes a **3-stage editing cascade**:
1. **Gemini Multimodal Vision (`gemini-2.0-flash-preview-image-generation`)**: Integrates visual features from the base64-encoded input image directly into the model's multimodal cross-attention layers alongside the textual instruction to synthesize a new edited image.
2. **AI Horde img2img (Stable Diffusion Deliberate)**: Runs standard image-to-image latent diffusion. The source image is encoded into latent space, noise is added based on a `denoising_strength=0.65` parameter, and the UNet is run to denoise the latents based on the edit prompt.
3. **PIL Native Overlay**: A non-neural fallback that draws a semi-transparent banner containing the edit description on top of the original image.

---

### 3. Acoustic Synthesis Layer (Neural TTS)

Lumina converts generated text into verbal responses using a deep learning text-to-speech network:

- **Microsoft Edge-TTS Engine**: Synthesizes natural-sounding speech from text strings. It leverages deep neural networks (DNN) trained on extensive voice datasets. By default, it employs `en-GB-SoniaNeural`, which models human prosody, inflection, and British regional pronunciation.
- **Preprocessing & Sanitization (`tts.py`)**: A custom regex pipeline cleans the LLM output before speech generation. It strips markdown blocks, system-only formatting, URLs, and code blocks, preventing the neural TTS engine from pronouncing raw markdown or HTML tags.

---



---

# 🚀 Deployment & Infrastructure


Lumina includes a fully containerized production infrastructure utilizing Docker, Gunicorn, and Nginx.

**Infrastructure Components:**
- **Dockerfile**: Builds a lightweight Python 3.11 image and installs all dependencies.
- **Production Server**: Uses **Gunicorn** with asynchronous **Uvicorn** workers to handle high-concurrency requests and robust application scaling.
- **Reverse Proxy (Nginx)**: The included `nginx/nginx.conf` securely routes traffic to the backend on port 80, explicitly handling WebSocket upgrades required by Gradio.
- **docker-compose.yml**: Orchestrates the Nginx reverse proxy and the Lumina Python backend, automatically mounting persistent volumes for image and audio caches.
- **Environment Separation**:
  - `.env.dev`: Local development environment variables template.
  - `.env.prod`: Production environment variables explicitly loaded by Docker Compose.

**Deployment Steps:**
1. Populate `.env.prod` with your real API keys.
2. Run the following command to build the image and spin up the backend and reverse proxy in the background:

```bash
docker-compose up -d --build
```
3. Access the application on `http://<your-server-ip>/`.

---
Illustrates the production-ready Docker infrastructure, showcasing how traffic hits the reverse proxy before being distributed to Uvicorn workers.

```mermaid
flowchart TD
    subgraph Host[Host OS / Server]
        subgraph Docker[Docker Network]
            Nginx["Nginx Reverse Proxy<br>(Port 80/443)"]
            App["Lumina FastAPI App<br>(Gunicorn / Uvicorn Workers)"]
            Nginx <-->|WebSockets & HTTP| App
        end
        Volumes[("Docker Volumes<br>Caches & History")]
        App <--> Volumes
    end
    
    Internet((🌍 Internet))
    Internet <--> Nginx
    
    subgraph CloudAPIs[External Cloud APIs]
        Groq(Groq Llama 3)
        Google(Google Gemma/Imagen)
        Together(Together FLUX)
        TTS(Microsoft Edge TTS)
    end
    
    App <--> CloudAPIs
```


---

# 🔒 Security


Lumina implements defense-in-depth to protect against adversarial prompts and cross-site scripting (XSS).

### Pre-flight Moderation Check
During the search classification phase (`classifier.py`), user input is routed through the OpenAI `moderations` API (if the active LLM client supports it). If flagged for self-harm, hate speech, or explicit content, the request can be intercepted before hitting the reasoning models.

### System Prompt Isolation
The system strictly enforces role boundaries in the API payload:
```python
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": user_input}
]
```
The dynamic system prompt (which assigns the 5-tier brain state rules) is always prepended with ultimate authority. Any user attempt to inject "Ignore previous instructions" is countered by the heavy weighting of the `system` role in models like Llama 3.3 and Gemma.

### Content Security Policy (CSP) & Markdown Sanitization
To prevent malicious code execution via UI injection:
1. **XSS Protection**: A custom Starlette `CSPMiddleware` is injected into the FastAPI app to restrict executable scripts while allowing necessary blobs for images and audio.
2. **TTS Sanitization**: The `clean_text_for_speech()` function strips HTML (`<audio>`, `<button>`) and Markdown fences from the LLM's output so that adversarial text cannot manipulate the underlying edge-tts engine.

---

### 🛡️ Threat Model Flowchart

The following diagram illustrates how Lumina mitigates various attack vectors at multiple layers of the application stack.

```mermaid
flowchart TD
    Adversary([🦹 Malicious User])
    
    subgraph Defenses [Lumina Security Boundary]
        CSP["CSP Middleware<br>(Blocks XSS/Eval)"]
        Preflight["Moderation API<br>(Checks for Harm)"]
        SysPrompt["Strict System Prompt<br>(Enforces Role Isolation)"]
        Sanitizer["TTS Text Sanitizer<br>(Strips HTML/Markdown)"]
    end
    
    Adversary -- "1. Submits XSS Script" --> CSP
    CSP -- "Blocked" --> Drop1((Drop))
    
    Adversary -- "2. Submits Explicit Prompt" --> Preflight
    Preflight -- "Flagged" --> Drop2((Drop))
    
    Adversary -- "3. 'Ignore previous instructions'" --> SysPrompt
    SysPrompt -- "Overridden by System Authority" --> LLM[LLM Engine]
    
    LLM -- "Hallucinates HTML/Audio tags" --> Sanitizer
    Sanitizer -- "Cleaned Text" --> TTS[Edge-TTS]
```


---

# 🧠 Routing


### 1. Introduction & Goals
Lumina AI employs a dynamic LLM routing architecture to manage user requests efficiently. Because Lumina orchestrates multiple capabilities (casual conversation, deep analysis, web searching, image generation), statically binding a single LLM to all tasks is inefficient both in terms of latency and API costs.

The goals of the LLM routing architecture are:
- **Latency Optimization**: Use lightning-fast, smaller models (e.g., Llama 3.1 8B) for simple background tasks like search intent classification.
- **Resource Allocation**: Reserve heavy-weight models (e.g., Llama 3.3 70B, Gemma 4 31B) strictly for the final conversational generation where reasoning and quality matter most.
- **Contextual Adaptation**: Dynamically switch the active model, system prompt, token limits, and temperature based on the user's selected "Brain State."

---

### 2. Pre-flight Intent Classification (`classifier.py`)

Before a user's message is ever sent to the main response LLM, it is intercepted by a pre-flight classifier.

#### Purpose
The classifier's sole responsibility is determining if the user's prompt requires external data retrieval (e.g., searching the surface web, dark web, or retrieving images/videos).

#### Implementation Details
- **Function**: `classify_search_need(message, past_history, brain_state)`
- **Model Selection**: 
  - If the user is in "Fast" or "Analysis" mode, it uses **Google Gemma 4 31B**.
  - Otherwise, it defaults to the ultra-fast **Groq Llama 3.1 8B Instant**.
- **Context Handling**: It injects the user's message alongside the last two turns of conversation history to maintain context (e.g., if the user says "what about in Paris?", the classifier knows what was previously being discussed).
- **Format Enforcement**: The output *must* be valid JSON to be parsed programmatically. 
  - Because Gemma models do not natively support strict JSON-mode (`response_format={"type": "json_object"}`), the system prompt dynamically appends a strict instruction: `"Output ONLY a raw JSON object with no markdown or extra text."`
  - A fallback regex/stripper logic automatically cleans any markdown code fences (` ```json `) the LLM might hallucinate.

---

### 3. Brain State Routing (`brain.py`)

Once pre-flight checks (and subsequent web searches) are complete, the `brain.py` router configures the primary generation LLM. 

#### Purpose
It acts as a switchboard that translates UI settings (Brain State and Model overrides) into specific API parameters (`client`, `model_name`, `temperature`, `max_tokens`, `system_prompt`).

#### The 5-Tier Persona Mapping
The system supports five distinct psychological "states", each tuning the LLM's behavior:

1. **Conscious (Default)**
   - **Model**: Groq Llama 3.3 70B
   - **Settings**: Temp `0.7`, Max Tokens `2048`
   - **Role**: Balanced, capable, highly intelligent assistant.
2. **Fast**
   - **Model**: Google Gemma 4 31B
   - **Settings**: Temp `0.7`, Max Tokens `1024`
   - **Role**: High-speed responses using the Gemma pipeline.
3. **Deep Analysis**
   - **Model**: Google Gemma 4 31B
   - **Settings**: Temp `0.5`, Max Tokens `4096`
   - **Role**: Low hallucination, deep reading, extensive token generation for coding and research.
4. **Chill**
   - **Model**: Groq Llama 3.1 8B
   - **Settings**: Temp `0.8`, Max Tokens `1024`
   - **Role**: Relaxed, conversational, casual. Uses a smaller, cheaper model for casual chatting.
5. **Subconscious**
   - **Model**: Groq Llama 3.1 8B
   - **Settings**: Temp `1.2`, Max Tokens `2048`
   - **Role**: High temperature, creative, loose "dream" mode.

#### Manual Overrides
Users can manually override the model using the UI Model Selector. The `get_brain_state_params()` function evaluates this override first, allowing a user to, for example, apply the "Subconscious" high-temperature prompt to the heavy Llama 3.3 70B model if they explicitly select it.

---

### 4. Data Flow Visualization

The following diagram illustrates the complete synchronous and asynchronous LLM routing lifecycle for a single user message.

```mermaid
sequenceDiagram
    participant User
    participant UI as Gradio Interface
    participant Classifier as Pre-flight Classifier (Llama 8B)
    participant Scraper as Search/Scraper Subsystem
    participant Brain as Brain Router
    participant LLM as Main LLM (Llama 70B / Gemma)

    User->>UI: Submit Message
    UI->>Classifier: classify_search_need(msg, history)
    
    rect rgb(240, 240, 240)
        Note over Classifier: Lightweight LLM predicts JSON
        Classifier-->>UI: {"needs_search": true, "query": "..."}
    end

    opt needs_search == true
        UI->>Scraper: perform_search(query)
        Scraper-->>UI: Retrieved Web Context
    end

    UI->>Brain: get_brain_state_params(state, model)
    Brain-->>UI: Returns (Client, Model, Temp, Tokens, Prompt)
    
    Note over UI: UI compiles system prompt + web context + history
    
    UI->>LLM: Stream Chat Completion
    LLM-->>UI: Yield Tokens
    UI-->>User: Render Real-time Response
```

---

### 5. The Chat Request Lifecycle (Sequence Diagram)
A highly detailed, end-to-end sequence illustrating how a single user prompt triggers a massive orchestration of search scraping, LLM streaming, image generation, audio synthesis, and memory persistence.

```mermaid
sequenceDiagram
    participant User
    participant UI as Gradio UI
    participant BrainRouter as Brain Router
    participant SearchClass as Search Classifier
    participant SearchEngines as Search Engines
    participant LLM as Main LLM
    participant ImageEngine as Image Engine
    participant TTS as Edge-TTS
    participant Persistence as Persistence Layer
    
    User->>UI: Submit prompt
    UI->>BrainRouter: Fetch active Brain State parameters
    BrainRouter-->>UI: Return System Prompt & Model
    
    UI->>SearchClass: Classify search intent (JSON)
    alt needs_search == true
        SearchClass->>SearchEngines: Query APIs / Scrape Web
        SearchEngines-->>SearchClass: Return Context
    end
    SearchClass-->>UI: Return final context string
    
    UI->>LLM: Stream chat completion
    LLM-->>UI: Stream text chunks
    
    opt Contains "/imagine" tag
        UI->>ImageEngine: Extract prompt & trigger generation
        ImageEngine-->>UI: Return generated image path
    end
    
    UI->>TTS: Asynchronous text synthesis
    TTS-->>UI: Return synthesized audio file path
    
    UI->>Persistence: Save conversation JSON to /chats
    Persistence-->>UI: Saved
    
    UI-->>User: Stream complete multimodal response (Text + Audio + Image)
```


---

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



---

# 🧪 Testing Architecture

Lumina AI employs a rigorous testing methodology to ensure stability across its complex multimodal pipelines. With **285 automated tests**, our suite guarantees high availability even when external providers fail.

## 1. Test Layers

### Unit Tests
The unit test layer focuses on pure Python logic that does not require network I/O:
- **Regex & Sanitizers**: Testing the `clean_text_for_speech()` function to ensure it aggressively strips all HTML, Unicode, and Markdown artifacts without mutating the spoken text.
- **Brain State Router**: Testing `get_brain_state_params()` to ensure the correct Model, Temperature, and System Prompt are emitted based on UI overrides.

### Integration Tests
Integration tests spin up the FastAPI environment to test subsystem coupling:
- **Middleware Safety**: Testing the `CSPMiddleware` to ensure Gradio WebSockets successfully upgrade, but malicious cross-site scripting (XSS) via injected `eval()` is blocked by the Content-Security-Policy headers.
- **Search Consolidation**: Mocking HTTP responses for `ddgs` and `googlesearch` to ensure the aggregator cleanly deduplicates URLs and formats the markdown context correctly.

## 2. External API Mocking Strategy
Because Lumina relies heavily on third-party cloud providers (Groq, Google, Together), we use `pytest-mock` and `responses` to intercept network calls.
- **LLM Streaming**: We mock the `AsyncGroq` and `AsyncOpenAI` clients to yield token chunks programmatically, testing how the Gradio UI renders real-time typewriter effects.

## 3. Failure & Cascade Simulation
This is the most critical testing layer for Lumina AI. We actively simulate catastrophic cloud outages to ensure our failovers trigger correctly.

### The 6-Stage Image Cascade Test
We inject a mock into `generate_image_async()` that forces:
1. `Pollinations AI` -> `HTTP 502 Bad Gateway`
2. `Together AI` -> `HTTP 401 Unauthorized`
3. `Craiyon` -> `HTTP 429 Too Many Requests` (Simulating Cloudflare blocks)
4. `Google Imagen` -> `HTTP 500 Internal Error`
5. `Gemini Flash` -> `HTTP 503 Service Unavailable`
**Assertion**: The test asserts that the function seamlessly catches all 5 exceptions in less than 2 seconds and successfully generates the local PIL Fallback Error Card, guaranteeing the UI never crashes.

### Edge-TTS Disconnects
We simulate a `ConnectionResetError` during the `edge-tts` WebSocket streaming phase. We assert that Lumina intercepts this specific Windows-based ProactorEventLoop crash, suppresses the traceback, and safely falls back to text-only mode without breaking the Gradio interface.


---

# 📜 API Contracts & Interfaces

To ensure Lumina AI remains highly modular, all internal subsystems communicate using strict JSON schemas and asynchronous Python contracts.

## 1. Search Classifier JSON Schema
When the lightweight LLM evaluates a user prompt in `classifier.py`, it must return a strictly formatted JSON object. 

**Expected Schema:**
```json
{
  "needs_search": "boolean",
  "query": "string (optional, required if needs_search is true)",
  "type": "enum ('text', 'images', 'news', 'darkweb')"
}
```
*Note: A custom regex sanitizer automatically cleans any markdown fences (` ```json `) emitted by Google Gemma before `json.loads()` is called.*

## 2. Chat Persistence Schema
The `history.py` module saves conversations to the `chats/` directory using the following JSON schema. This schema ensures portability and enables future Vector DB migration.

**Expected Schema (`chats/<uuid>.json`):**
```json
{
  "id": "string (uuid4)",
  "title": "string (max 30 chars)",
  "updated_at": "string (ISO 8601 timestamp)",
  "history": [
    {
      "role": "enum ('user', 'assistant', 'system')",
      "content": "string (markdown allowed)"
    }
  ]
}
```

## 3. Subsystem Async Contracts
All heavy I/O operations are wrapped in strict asynchronous interfaces to prevent blocking the Gradio UI event loop.

### Image Engine
```python
async def generate_image_async(prompt: str) -> str:
    """
    Executes the 6-stage image generation cascade.
    Returns: Absolute path to the generated .png in `image_cache/`.
    Guarantees: Never raises an exception; always returns a valid image path (even if it's the PIL error card).
    """
```

### Search Scraper
```python
async def perform_search(query: str, engines: list = None) -> tuple[str, list]:
    """
    Executes concurrent web scraping against requested engines.
    Returns: A tuple containing (1) The concatenated markdown text context, and (2) A list of raw media dictionaries (images/videos).
    """
```


---

# 🔌 API & Subsystems

## Project Structure

```
Lumina-AI/
├── main.py                          # Entry point — boots FastAPI + Gradio on :7861
├── requirements.txt                 # Python dependencies
├── .env                             # API keys (GROQ_API_KEY, GOOGLE_API_KEY, TOGETHER_API_KEY)
├── .gitignore                       # Excludes .env, __pycache__, chats/, audio_cache/
├── LICENSE                          # MIT License
├── README.md                        # User setup & usage guide
├── implementation_plan.md           # Original architectural blueprint
├── lumina_technical_documentation.md # This file
├── .github/workflows/ci.yml         # GitHub Actions: import validation
├── audio_cache/                     # Generated TTS .mp3 files (gitignored)
├── image_cache/                     # Generated image .png files
├── chats/                           # Chat history JSON files (gitignored)
└── lumina/                          # Core Python package
    ├── __init__.py                  # Loads .env via dotenv
    ├── core/
    │   ├── __init__.py
    │   └── config.py                # Constants: timeouts, prompts, model names, dirs
    ├── providers/
    │   ├── __init__.py
    │   └── llm.py                   # AsyncGroq + AsyncOpenAI (Gemma) client init
    ├── models/
    │   ├── __init__.py
    │   └── brain.py                 # 5-tier brain state router
    ├── routing/
    │   ├── __init__.py
    │   └── classifier.py            # Pre-flight search intent classifier
    ├── search/
    │   ├── __init__.py
    │   └── scraper.py               # Multi-engine search (Google, Bing, DDG, Wiki, Ahmia, Tor)
    ├── image/
    │   ├── __init__.py
    │   └── engine.py                # 6-stage image generation + 3-stage image editing
    ├── speech/
    │   ├── __init__.py
    │   └── tts.py                   # Edge TTS British voice synthesis
    ├── memory/
    │   ├── __init__.py
    │   └── history.py               # Chat persistence to JSON files
    ├── ui/
    │   ├── __init__.py
    │   └── interface.py             # Gradio UI + FastAPI server + CSP middleware
    └── utils/
        ├── __init__.py
        └── network.py               # HTTP utilities, PIL validation, user-agent rotation
```

---

## Files & Their Roles

### `main.py` — Application Entry Point

**Location:** `Lumina-AI/main.py`

Imports the `app` FastAPI instance from `lumina.ui` and runs Uvicorn on `127.0.0.1:7861`.

```python
import uvicorn
from lumina.ui import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=7861)
```

**Instructions:** Start the application with `python main.py`. No modification needed.

---

### `lumina/__init__.py` — Package Initializer

**Location:** `Lumina-AI/lumina/__init__.py`

Automatically calls `load_dotenv()` when the `lumina` package is imported, making `.env` variables available globally.

---

### `lumina/core/config.py` — Global Configuration

**Location:** `Lumina-AI/lumina/core/config.py`

Holds all shared constants. Imported by every other module.

**Exported constants:**

| Constant | Default | Purpose |
|---|---|---|
| `CHATS_DIR` | `"chats"` | Chat history storage directory |
| `IMAGE_CACHE_DIR` | `"image_cache"` | Generated image storage directory |
| `GOOGLE_API_KEY` | env var | Google API key for Gemma/Imagen/Gemini |
| `GOOGLE_IMAGEN_MODEL` | `imagen-4.0-generate-001` | Imagen model name |
| `GOOGLE_GEMINI_IMAGE_MODEL` | `gemini-3.1-flash-image-preview` | Gemini image generation model |
| `GOOGLE_GEMINI_EDIT_MODEL` | `gemini-2.0-flash-preview-image-generation` | Gemini image editing model |
| `GEMMA_MODEL` | `gemma-4-31b-it` | Gemma LLM model name |
| `SEARCH_TIMEOUT_SECONDS` | `25` | Max search duration |
| `CHAT_IMAGE_TIMEOUT_SECONDS` | `75` | Max chat image generation time |
| `STUDIO_IMAGE_TIMEOUT_SECONDS` | `120` | Max studio image generation time |
| `TTS_TIMEOUT_SECONDS` | `30` | Max TTS generation time |
| `TTS_MAX_CHARS` | `1200` | Character limit for TTS input |
| `PREFLIGHT_TIMEOUT_SECONDS` | `12` | Search classification timeout |
| `CHAT_REQUEST_TIMEOUT_SECONDS` | `60` | Max LLM response time |
| `STREAM_CHUNK_TIMEOUT_SECONDS` | `30` | Max time between stream chunks |
| `SYSTEM_PROMPT` | (see file) | Main Lumina persona prompt |
| `SUBCONSCIOUS_PROMPT` | (see file) | Power-saving dream mode prompt |
| `GEMMA_FAST_PROMPT` | (see file) | Fast response mode prompt |
| `GEMMA_ANALYSIS_PROMPT` | (see file) | Deep analysis mode prompt |
| `CHILL_PROMPT` | (see file) | Relaxed mode prompt |

**Instructions:** Edit model names, timeouts, or persona prompts here. API keys belong in `.env`, not this file.

---

### `lumina/providers/llm.py` — LLM Client Initialization

**Location:** `Lumina-AI/lumina/providers/llm.py`

Initializes two async LLM clients:

- **`groq_client`** — `AsyncGroq` with `GROQ_API_KEY` from environment. Used for Llama 3.3 70B and Llama 3.1 8B.
- **`gemma_client`** — `AsyncOpenAI` pointed at Google's OpenAI-compatibility endpoint (`https://generativelanguage.googleapis.com/v1beta/openai/`) with `GOOGLE_API_KEY`. Used for Gemma 4 31B.   

**Instructions:** Ensure `GROQ_API_KEY` and `GOOGLE_API_KEY` are set in `.env`.

---

### `lumina/models/brain.py` — Brain State Router

**Location:** `Lumina-AI/lumina/models/brain.py`

Exports `get_brain_state_params(brain_state, model_selector)` which returns a tuple: `(client, model_name, temperature, max_tokens, system_prompt)`.

**5 brain states:**

| State | Client | Model | Temp | Max Tokens |
|---|---|---|---|---|
| Conscious (default) | Groq | Llama 3.3 70B | 0.7 | 2048 |
| Fast | Gemma | Gemma 4 31B | 0.7 | 1024 |
| Deep Analysis | Gemma | Gemma 4 31B | 0.5 | 4096 |
| Chill | Groq | Llama 3.1 8B | 0.8 | 1024 |
| Subconscious | Groq | Llama 3.1 8B | 1.2 | 2048 |

The `model_selector` parameter allows manual override (e.g., forcing a specific model regardless of brain state).

**Instructions:** Add or modify brain states here. Each state defines which client, model, temperature, max tokens, and system prompt to use.

---

### `lumina/routing/classifier.py` — Search Intent Classifier

**Location:** `Lumina-AI/lumina/routing/classifier.py`

Exports `classify_search_need(message, past_history, brain_state)` — an async function that uses a lightweight LLM (Llama 3.1 8B or Gemma 4 31B) to determine if a user message requires a live internet search.

**Returns:** `dict` — e.g., `{"needs_search": true, "query": "best search query", "type": "text"}` or `{"needs_search": false}`.

**Logic:**
- Uses Gemma when brain state is Fast or Analysis, Groq Llama otherwise.
- Gemma does not support `response_format={"type": "json_object"}` — so the prompt explicitly instructs raw JSON output with no markdown.
- Strips markdown code fences from the response before JSON parsing.
- On any error, safely returns `{"needs_search": false}`.

**Instructions:** No configuration needed. The classifier is triggered automatically when internet access is enabled in the UI.

---

### `lumina/search/scraper.py` — Multi-Engine Search Aggregator

**Location:** `Lumina-AI/lumina/search/scraper.py` (554 lines)

The largest module in the project. Exports `perform_search()`, `format_images_for_chat()`, and `format_videos_for_chat()`.

**Supported search engines:**

| Engine | Function | Method | Type support |
|---|---|---|---|
| Google | `search_google()` | `googlesearch-python` | text |
| Bing | `search_bing()` | BeautifulSoup scrape on `bing.com/search` | text |
| DuckDuckGo | `search_duckduckgo()` | `ddgs` / `duckduckgo_search` | text, images, videos, news |
| Wikipedia | `search_wikipedia()` | `wikipedia` library | text |
| Ahmia (dark web) | `search_ahmia()` | BeautifulSoup scrape on `ahmia.fi` | text (onion URLs) |
| Torch (dark web fallback) | `_scrape_torch()` | BeautifulSoup scrape on `torchdarkweb.com` | text |
| Tor Direct | `search_onion_direct()` | SOCKS proxy through Tor | text (direct .onion fetch) |

**`perform_search(query, engines=None, search_type="text")`**
- Runs selected engines in sequence (not parallel).
- Deduplicates results by URL.
- Formats results into a structured text block for LLM context injection.
- Returns `(formatted_text, raw_media)` where `raw_media` contains image/video results for direct rendering.

**`format_images_for_chat(results)` / `format_videos_for_chat(results)`**
- Generate markdown strings for embedding images and videos directly in chat responses.

**Tor support:**
- Attempts SOCKS5 proxies on ports 9150 (Tor Browser) and 9050 (Tor daemon).
- Configurable via `TOR_SOCKS_PROXY` or `TOR_PROXY` environment variables.

**Instructions:** Requires `requests[socks]` (PySocks) for Tor features. Search engines are toggled from the UI.

---

### `lumina/image/engine.py` — Image Generation & Editing Engine

**Location:** `Lumina-AI/lumina/image/engine.py` (407 lines)

Exports `generate_image_async(prompt)` and `edit_image_async(prompt, input_image_path)`.

#### Image Generation Pipeline (6 stages, cascading failover):

| Stage | Provider | Key Required | Method |
|---|---|---|---|
| 1 | Pollinations AI | No | `GET image.pollinations.ai/prompt/{encoded}?nologo=true&seed={r}&width=1024&height=1024` |
| 2 | Together AI (FLUX.1-schnell-Free) | `TOGETHER_API_KEY` | `together.Images.generate()` |
| 3 | Craiyon v3 | No | POST `api.craiyon.com/v3` with model `photo` |
| 4 | Google Imagen 4 | `GOOGLE_API_KEY` | POST `generativelanguage.googleapis.com/v1beta/models/{imagen}:predict` |
| 5 | Gemini 3.1 Flash | `GOOGLE_API_KEY` | POST `generativelanguage.googleapis.com/v1beta/models/{gemini}:generateContent` with `responseModalities: ["Image"]` |
| 6 | AI Horde | Anonymous | POST `aihorde.net/api/v2/generate/async`, poll for completion |

**Fallback:** If all 6 stages fail, generates a dark-themed PIL error card with the prompt and error explanation, ensuring the UI never receives `None`.

#### Image Editing Pipeline (3 stages):

| Stage | Provider | Key Required | Method |
|---|---|---|---|
| 1 | Gemini multimodal | `GOOGLE_API_KEY` | POST with inline image data + edit instruction, tries multiple model variants |
| 2 | AI Horde img2img | Anonymous | POST source image as base64, `denoising_strength=0.65`, poll up to 12×5s |
| 3 | PIL overlay fallback | No | Draws semi-transparent banner with edit instruction on the original image |

**Instructions:** Images are cached in `image_cache/`. The pipeline auto-cascades on failure. At minimum, `GOOGLE_API_KEY` enables stages 4–5 (generation) and stage 1 (editing). `TOGETHER_API_KEY` enables stage 2.

---

### `lumina/speech/tts.py` — Text-to-Speech Engine

**Location:** `Lumina-AI/lumina/speech/tts.py` (32 lines)

Exports `clean_text_for_speech(text)` and `generate_audio(text)`.

**`clean_text_for_speech(text)`**
- Strips `[IMAGE_PROMPT:...]` tags, markdown images, code blocks, backticks, bold/italic markers, headers, and emojis (both BMP symbols and supplementary Unicode).
- Strips inline HTML tags (like `<audio>` and `<button>`) to prevent the TTS engine from reading UI markup.

**`generate_audio(text)`**
- Uses Edge TTS with dynamically selected voices (including 24 regional Arabic dialects).
- Saves output to `audio_cache/lumina_{uuid_hex[:8]}.mp3`.
- Directory is created automatically.

**Instructions:** Ensure `edge-tts` is installed. TTS triggers automatically after each chat response. Max 1200 characters (configurable via `TTS_MAX_CHARS` in config).

#### Supported Languages & Neural Voices
Lumina supports a vast array of high-fidelity neural voices. The LLM automatically detects the chosen language and accent, switching its persona, spelling, slang, and dialect dynamically.

**English Variations:**
- **British (UK):** Sonia (F), Libby (F), Maisie (F), Ryan (M), Thomas (M)
- **American (US):** Aria (F), Jenny (F), Emma (F), Guy (M), Andrew (M)
- **Australian (AU):** Natasha (F), William (M)
- **Canadian (CA):** Clara (F), Liam (M)
- **Indian (IN):** Neerja (F), Prabhat (M)
- **Irish (IE):** Emily (F), Connor (M)
- **New Zealander (NZ):** Molly (F), Mitchell (M)
- **South African (ZA):** Leah (F), Luke (M)
- **Singaporean (SG):** Luna (F), Wayne (M)
- **Philippine (PH):** Rosa (F), James (M)
- **Hong Kong (HK):** Yan (F), Sam (M)
- **Kenyan (KE):** Asilia (F), Chilemba (M)
- **Nigerian (NG):** Ezinne (F), Abeo (M)
- **Tanzanian (TZ):** Imani (F), Elimu (M)

**Arabic Dialects:**
- **Egypt (EG):** Salma (F), Shakir (M)
- **Saudi Arabia (SA):** Zariyah (F), Hamed (M)
- **UAE (AE):** Fatima (F), Hamdan (M)
- **Lebanon (LB):** Layla (F), Rami (M)
- **Jordan (JO):** Sana (F), Taim (M)
- **Syria (SY):** Amany (F), Laith (M)
- **Algeria (DZ):** Amina (F), Ismael (M)
- **Morocco (MA):** Mouna (F), Jamal (M)
- **Tunisia (TN):** Reem (F), Hedi (M)
- **Iraq (IQ):** Rana (F), Bassel (M)
- **Kuwait (KW):** Noura (F), Fahed (M)
- **Qatar (QA):** Amal (F), Moaz (M)

**European & Asian Languages:**
- **Spanish (Spain):** Elvira (F), Alvaro (M)
- **Spanish (Mexico):** Dalia (F), Jorge (M)
- **French (France):** Denise (F), Vivienne (F), Henri (M)
- **French (Canada):** Sylvie (F), Antoine (M)
- **German:** Amala (F), Seraphina (F), Killian (M)
- **Italian:** Elsa (F), Diego (M)
- **Portuguese (Brazil):** Francisca (F), Antonio (M)
- **Portuguese (Portugal):** Raquel (F), Duarte (M)
- **Russian:** Svetlana (F), Dmitry (M)
- **Japanese:** Nanami (F), Keita (M)
- **Chinese (Mandarin):** Xiaoxiao (F), Yunxi (M)
- **Hindi:** Swara (F), Madhur (M)

---

### `lumina/memory/history.py` — Chat Persistence

**Location:** `Lumina-AI/lumina/memory/history.py` (79 lines)

Exports `get_chat_list()`, `load_chat(chat_id)`, and `save_chat(chat_id, history)`.

**Storage format:** JSON files in `chats/` directory:

```json
{
  "id": "uuid",
  "title": "First 30 chars of first user message...",
  "updated_at": "2026-05-20 19:30",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

**Legacy support:** `load_chat()` handles old tuple-format history `["user_msg", "assistant_msg"]` in addition to dict format.

**`get_chat_list()`** Returns `[(display_name, chat_id), ...]` sorted by file modification time (newest first).

**Instructions:** History auto-saves after every message. Clear the `chats/` directory to reset.

---

### `lumina/ui/interface.py` — Web UI & Server

**Location:** `Lumina-AI/lumina/ui/interface.py` (487 lines)

The most complex module. Exports `app` (FastAPI instance) and `demo` (Gradio Blocks instance).

#### Windows Compatibility
- Sets `asyncio.WindowsSelectorEventLoopPolicy()` to avoid `ProactorEventLoop` crashes.
- Monkey-patches `_ProactorBasePipeTransport._call_connection_lost` to suppress benign `ConnectionResetError` tracebacks during TTS.

#### UI Tabs

**1. Chat Companion Tab (`chat_with_lumina` coroutine)**

Data flow:
1. Load brain state params via `get_brain_state_params()`
2. Build message history with system prompt (automatically applies regional dialects/slang based on the selected voice accent, e.g., Egyptian or Lebanese Arabic).
3. Optionally classify search need & run `perform_search()` in thread
4. Call LLM (streaming for Groq, non-streaming for Gemma — avoids Google API 500 errors)
5. Process `[IMAGE_PROMPT:...]` tags → `generate_image_async()` → replace with markdown
6. Clean text & generate audio via `generate_audio()`
7. Inject an inline HTML `<audio>` player with a custom styled "Play" button directly into the chat stream using relative paths to bypass strict Gradio `allowed_paths` checks.
8. Save chat history
9. Yield incremental UI updates (streaming response, audio player, chat list refresh)

**Robust Parsing Helper:** Uses a recursive `extract_text_content()` function to extract strings from nested Gradio message structures (lists, tuples, `FileData` dicts) to prevent type errors.

UI controls:
- Brain state radio (Conscious, Fast, Analysis, Chill, Subconscious)
- Model selector (Llama 3.3 70B, Llama 3.1 8B, Gemma 4 31B)
- Internet access toggle + search engine checkboxes
- Chat history dropdown + new chat button
- Audio player (autoplay)
- Example prompts

**2. AI Image Studio Tab**
- Style dropdown (Ultra Realistic, Cartoonish/Anime, CGI/3D Render, Default)
- Text prompt → `generate_image_async()` with style keyword appended
- Image upload + edit instruction → `edit_image_async()`

#### Server & Middleware

```python
class CSPMiddleware(BaseHTTPMiddleware):
    # Injects permissive Content-Security-Policy header
    # Allows all sources, inline scripts, blobs, data URIs

app = FastAPI()
app.add_middleware(CSPMiddleware)
app = gr.mount_gradio_app(app, demo, path="/", allowed_paths=[image_cache_abspath])
```

**Instructions:** Run via `main.py`. The CSP middleware is critical for allowing Gradio to load external media, blobs, and web workers without browser blocking.

---

### `lumina/utils/network.py` — HTTP & Image Utilities

**Location:** `Lumina-AI/lumina/utils/network.py` (77 lines)

Provides shared utilities used by the scraper and image engine:

| Function | Purpose |
|---|---|
| `safe_error(exc)` | Redacts API keys from error strings via regex `([?&](?:key|api_key)=)[^&\s]+` |
| `get_headers()` | Generates browser-like headers with random User-Agent |
| `make_session()` | Creates a `requests.Session` with disabled SSL verification |
| `save_image_bytes(data, filepath)` | Validates image with PIL `verify()` before writing to disk |
| `download_url(url, filepath, retries, wait)` | Downloads an image with retry logic, checks Content-Type for `image/*` |

---

### Prerequisites
- Python 3.11+
- Groq API key (required)
- Google API key (required for Gemma, Imagen, Gemini)
- Together AI API key (optional, improves image generation)

### Installation

```bash
git clone <repo-url>
cd Lumina-AI
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
pip install requests[socks]  # Optional: for Tor/.onion support
```

### Configuration

Create `.env` in the project root:

```env
GROQ_API_KEY=gsk_your_key_here
GOOGLE_API_KEY=AIza_your_key_here
TOGETHER_API_KEY=tgp_v1_your_key_here  # Optional
```

### Running (Local Development)

```bash
python main.py
```

Open `http://127.0.0.1:7861` in a browser.


```
groq==1.2.0              → AsyncGroq LLM client
gradio==6.14.0           → Web UI framework
python-dotenv==1.2.2     → .env loading
edge-tts==7.2.8          → British TTS
requests==2.34.2         → HTTP client
beautifulsoup4==4.14.3   → HTML scraping
duckduckgo-search==8.1.1 → DuckDuckGo search API
googlesearch-python==1.3.0 → Google search
wikipedia==1.4.0         → Wikipedia API
Pillow==10.4.0           → Image processing/validation
together==2.14.0         → Together AI FLUX image gen
openai==2.37.0           → OpenAI-compatible Gemma client
fastapi==0.136.1         → ASGI framework
uvicorn==0.46.0          → ASGI server
```

---

## ⚙️ Summary of Subsystem Capabilities

| Subsystem | Primary Technologies | Core Capabilities |
| :--- | :--- | :--- |
| **Conversational AI** | Groq Llama 3.3 / Google Gemma 4 | 5 distinct persona modes, emotional intelligence switching, autonomous prompt generation, and dynamic dialect switching based on TTS accent. |
| **Web Research** | BeautifulSoup, DDGS, Google/Wiki APIs | Surface web scraping, Tor dark web indexing (`ahmia.fi`), automatic deduplication, rich markdown media embedding. |
| **Image Generation** | Pollinations, Together FLUX, Craiyon v3, Google Imagen, Gemini Flash, AI Horde | 6-stage fault-tolerant failover, Cloudflare WAF evasion, lazy-generation retry loops, PIL integrity verification, fail-safe error cards. |
| **Speech Synthesis** | Edge TTS | 24+ regional accents, inline chat HTML play buttons, on-the-fly text/HTML sanitization, asynchronous caching, Windows socket error suppression. |
| **Security & Server** | FastAPI, Uvicorn, Starlette Middleware | Permissive Content-Security-Policy injection, robust relative path handling for static files, environment variable management, and comprehensive error handling. |



---

# 🔭 Observability Strategy

As Lumina AI orchestrates increasingly complex asynchronous tasks (LLM Routing, Web Scraping, 6-Stage Image Cascades), robust observability is critical for debugging and performance tuning.

## 1. Logging Strategy
We utilize Python's standard `logging` library, heavily augmented for async contexts.
- **Format**: All production logs are serialized to JSON. This allows logs to be easily ingested and queried by systems like ELK (Elasticsearch, Logstash, Kibana) or Grafana Loki.
- **Trace IDs**: Every incoming chat request is assigned a unique `UUID`. This Trace ID is passed down through the `BrainRouter`, `SearchClassifier`, and `ImageEngine` to easily track a single user journey across multiple async threads.

## 2. Distributed Tracing
Because Lumina relies heavily on external Cloud APIs, we implement basic span tracking:
- **LLM Latency**: Time to First Token (TTFT) and Total Generation Time are measured for both Groq and Google endpoints.
- **Failover Cascades**: When `generate_image_async` cascades from Provider 1 to Provider 2, an `WARN` level trace is emitted indicating *why* the failover occurred (e.g., HTTP 429 Rate Limit vs HTTP 500 Internal Error).

## 3. Core Metrics & Monitoring
The FastAPI middleware exposes a `/metrics` endpoint (Prometheus format) tracking:
- `lumina_search_timeouts_total`: Number of times the DDG/Google scraper timed out.
- `lumina_image_generation_duration_seconds`: Histogram of image pipeline latency.
- `lumina_tts_generation_errors`: Counter for Edge-TTS websocket disconnects.
- `lumina_active_websocket_connections`: Gauge tracking active Gradio users.

## 4. Alerting
Alerts should be configured if:
- The Pre-flight Search Classifier begins returning non-JSON formats repeatedly (indicating a prompt injection or LLM drift).
- Image Generation reaches Stage 6 (AI Horde) or the PIL Fallback more than 5 times in a 10-minute window (indicating upstream provider outages).


---

# ADR 0001: Multi-Tiered LLM Routing Architecture

## Status
**Accepted** (May 2026)

## Context
Lumina AI requires the ability to perform lightweight background tasks (like classifying whether a user's prompt needs a web search) alongside heavy reasoning tasks (like generating long-form coding answers). Sending every background classification to a massive 70B parameter model is too slow and costly, while sending complex reasoning tasks to an 8B model yields poor results.

## Decision
We implemented a **Multi-Tiered LLM Routing Architecture**:
1. **Pre-Flight Classification**: All messages are intercepted by a lightweight, high-speed model (Groq Llama 3.1 8B or Gemma 31B depending on the user's state) which strictly outputs JSON (`{"needs_search": true}`).
2. **5-Tier Brain State Persona**: We decouple the primary generation into 5 states (Conscious, Fast, Analysis, Chill, Subconscious) mapped dynamically to different combinations of API Providers (Groq/Google), Models (Llama 70B vs Gemma 31B), and temperatures (0.5 to 1.2).

## Consequences
- **Positive**: Massive reduction in latency. Pre-flight checks take <800ms. API costs are minimized because 70B models are strictly reserved for actual response generation.
- **Negative**: Adds architectural complexity. We must maintain separate client instances (`AsyncGroq`, `AsyncOpenAI`) and handle fallback logic if one provider goes down. The system prompts become highly dynamic and harder to test rigidly.


---

# ADR 0002: 6-Stage Multimodal Failover Strategy

## Status
**Accepted** (May 2026)

## Context
Generative AI APIs are notoriously unstable. Rate limits, cloud outages, or explicit content blockades frequently cause single-provider systems to crash or return empty responses. Since Lumina AI relies heavily on multimodal image generation within the Chat UI and the AI Studio, a single point of failure is unacceptable.

## Decision
We implemented a **6-Stage Cascading Failover Engine** using an asynchronous `try-except` pipeline:
1. **Pollinations AI** (No-auth, lightning fast)
2. **Together AI FLUX** (High-fidelity, authenticated)
3. **Craiyon v3** (Web-scraping fallback)
4. **Google Imagen 4** (Premium authenticated)
5. **Gemini 3.1 Flash** (Multimodal fallback)
6. **AI Horde** (Anonymous, crowdsourced, slow but highly resilient)

If all six cloud providers fail, the system falls back to generating a local PIL (Python Imaging Library) error card with the user's prompt drawn on it.

## Consequences
- **Positive**: Near 100% uptime for the image generation feature. Complete resilience against Cloudflare blocks (which frequently target Craiyon) or Google API rate limits.
- **Negative**: Requires maintaining API contracts for 6 entirely different services. The `ImageEngine` class is monolithic and relies heavily on complex `asyncio` blocking wrappers because some APIs require synchronous HTTP polling.


---

# ADR 0003: FastAPI & Gradio Hybrid Architecture

## Status
**Accepted** (May 2026)

## Context
Lumina AI requires a real-time web interface for chat, image generation, and audio playback. Standard full-stack frameworks (like Next.js + Node) would require a massive duplication of logic, since the core machine learning inference, TTS, and web scraping ecosystems are natively Python-based.

## Decision
We chose to build the UI entirely in **Gradio** and mount it directly onto a **FastAPI** ASGI application.
- **FastAPI**: Acts as the robust middleware layer, handling Uvicorn worker scaling, Content-Security-Policy (CSP) header injection, and potential REST API expansions.
- **Gradio**: Handles the WebSocket connections, real-time UI streaming, and state management natively in Python.

## Consequences
- **Positive**: Extreme development velocity. We can build complex multimodal UI components (like injecting inline HTML audio players) using pure Python without writing React components. The entire app ships in a single Docker container.
- **Negative**: UI customization is heavily restricted by Gradio's component limitations. We have to employ hacks (like the `extract_text_content` recursive flattener) to parse Gradio's complex `FileData` tuples when users upload images. Mounting Gradio inside FastAPI also requires careful Nginx proxying for WebSocket upgrades.


---

