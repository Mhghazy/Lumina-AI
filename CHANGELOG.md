# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-05-22

### Added
- **Production Infrastructure**: Fully containerized the application using Docker, `docker-compose`, and a reverse-proxy Nginx server.
- **Multi-Modal Image Pipeline**: Introduced a highly resilient 6-stage fallback cascade for image generation (Pollinations, Together FLUX, Craiyon, Google Imagen, Gemini Flash, AI Horde).
- **Dynamic Brain States**: Implemented 5 psychological personas (Conscious, Fast, Analysis, Chill, Subconscious) mapped dynamically to Groq Llama 3.3, Llama 3.1, and Google Gemma models.
- **Architectural Documentation**: Added comprehensive `llm_routing_architecture.md` detailing the LLM flow and failover capabilities.
- **Collaborative Scaffolding**: Added GitHub issue/PR templates, a roadmap, and a contributing guide for open-source collaboration.

### Changed
- Refactored `history.py` to robustly parse complex Gradio nested tuples and cleanly serialize chat history to JSON.
- Upgraded the text-to-speech engine to support 24+ regional accents via `edge-tts` with silent timeout recovery.

### Fixed
- Fixed CSP (Content-Security-Policy) errors in the FastAPI middleware that were blocking inline CSS/JS execution in the Gradio UI.
- Fixed 429 Rate Limit crashes in `googlesearch-python` by falling back to DuckDuckGo search automatically.
