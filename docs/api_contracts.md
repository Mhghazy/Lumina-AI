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
