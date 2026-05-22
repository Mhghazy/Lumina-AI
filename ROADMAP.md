# Lumina AI Roadmap

This document outlines the short-term and long-term goals for the Lumina AI virtual companion ecosystem.

## 🚀 Near Term (v2.1 - v2.3)
- **Vector Database Integration**: Replace the simple JSON-based memory system with a robust vector database (like ChromaDB or Qdrant) to grant Lumina true long-term episodic memory.
- **Enhanced Image Pipelines**: Add ComfyUI API integration as an additional failover stage for local hardware acceleration.
- **Live Voice Mode**: Implement WebRTC for continuous two-way audio conversations with Lumina, moving beyond the current asynchronous TTS rendering.

## 🌟 Medium Term (v2.4 - v2.9)
- **Agentic Actions**: Grant Lumina the ability to natively execute code (via a sandboxed container) to solve complex user requests.
- **Multi-modal Input**: Allow users to upload images for Lumina to analyze contextually during casual chat (currently limited to the Image Studio).
- **Expanded Local LLM Support**: Deepen integration with Ollama and vLLM to allow users to host the Brain states entirely offline without Groq or Gemini API keys.

## 🔭 Long Term (v3.0+)
- **Fully Autonomous Companion**: Shift from a purely reactive chat UI to a proactive AI that can reach out to the user, schedule tasks, and run persistent background processes.
