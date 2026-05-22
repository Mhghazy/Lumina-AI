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
