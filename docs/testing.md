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
