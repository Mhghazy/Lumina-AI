# Lumina AI v2 — Technical Documentation


Please navigate to the main index to begin exploring the architecture, APIs, ADRs, and security models:

👉 **[Enter the Lumina Developer Portal](docs/index.md)** 👈

---

### 📚 Full Documentation (Arranged in Order)

If you prefer to read, search, or print the entire documentation as a single document:
👉 **[View Full Single-Page Documentation](docs/full_documentation.md)**

If you prefer to read through the documentation sequentially by topic, please follow this path:

1. **[System Architecture](docs/architecture.md)** — High-level data flows, memory persistence, and system-wide use case diagrams.
2. **[Deployment Infrastructure](docs/deployment.md)** — Docker setup, Nginx configuration, and Uvicorn scaling.
3. **[Security & Threat Models](docs/security.md)** — Prompt Injection defense, XSS mitigation, and the Threat Model Flowchart.
4. **[LLM Routing Engine](docs/routing.md)** — Pre-flight search intent classification and the 5-Tier Brain State persona mapping.
5. **[Failover Strategies](docs/failover.md)** — The 6-stage resilient image generation cascade and TTS fallback mechanics.
6. **[Testing Architecture](docs/testing.md)** — Unit/Integration testing strategies and external API failure simulation.
7. **[API Contracts](docs/api_contracts.md)** — Strict JSON schemas for Chat History and Async LLM requests.
8. **[Subsystem Reference](docs/api.md)** — Deep dive into every core Python module (`lumina/`), setup instructions, and the dependency map.
9. **[Observability](docs/observability.md)** — Telemetry, logging formats, metrics tracing, and system monitoring.
10. **[Architecture Decision Records (ADRs)](docs/adr/)** — Historical log of major architectural choices (e.g., LLM routing, Gradio framework).

---

*Note: If you are looking for contribution guidelines or version history, please see [CONTRIBUTING.md](CONTRIBUTING.md) and [CHANGELOG.md](CHANGELOG.md).*
