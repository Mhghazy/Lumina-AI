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
