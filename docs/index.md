# Lumina AI Developer Portal

Welcome to the internal engineering documentation for Lumina AI. This portal contains all architecture decisions, API contracts, deployment schemas, and subsystem overviews required to maintain and scale the repository.

---

## 🗺️ Core Architecture

| Document | Description |
|---|---|
| **[Architecture Overview](architecture.md)** | High-level data flows, Memory persistence logic, and System-wide Use Cases. |
| **[Deployment Infrastructure](deployment.md)** | Dockerization, Nginx Reverse Proxy, and Uvicorn/Gunicorn worker scaling. |
| **[LLM Routing Engine](routing.md)** | Pre-flight search intent classification and the 5-Tier Brain State persona mapping. |
| **[Failover Strategies](failover.md)** | The 6-stage resilient image generation cascade and TTS fallback mechanics. |

## 🛡️ Security & Reliability

| Document | Description |
|---|---|
| **[Security & Threat Model](security.md)** | Prompt Injection defense, XSS mitigation, and Content-Security-Policy rules. |
| **[Testing Architecture](testing.md)** | Unit/Integration testing strategies, mock injection, and failover simulation. |
| **[Observability](observability.md)** | **[NEW]** Telemetry, logging formats, metrics tracing, and system monitoring. |

## 🔌 APIs & Decisions

| Document | Description |
|---|---|
| **[API Contracts](api_contracts.md)** | **[NEW]** JSON schemas for Chat History, UI WebSockets, and Async LLM requests. |
| **[Subsystem Reference](api.md)** | Deep dive into every core Python module (`lumina/`), setup instructions, and dependency map. |
| **[Architecture Decision Records](adr/)** | **[NEW]** Historical log of major architectural choices (e.g., Gradio vs React, Routing). |
