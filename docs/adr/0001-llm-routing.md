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
