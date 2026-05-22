import json
import asyncio
from lumina.core.config import PREFLIGHT_TIMEOUT_SECONDS, GEMMA_MODEL
from lumina.providers.llm import groq_client, gemma_client

async def classify_search_need(message: str, past_history: list, brain_state: str):
    """
    Decides if the current message requires an internet search.
    Returns:
        dict: The parsed JSON response, e.g. {"needs_search": True, "query": "...", "type": "..."}
    """
    preflight_messages = [{
        "role": "system", 
        "content": (
            "You are a search query generator. If the user's message requires looking up "
            "current events, facts, images, videos, or dark web links, output a JSON object: "
            "{\"needs_search\": true, \"query\": \"best search query\", \"type\": \"text\"} "
            "(type can be text, images, videos, news). If no search is needed, output "
            "{\"needs_search\": false}. ONLY output valid JSON."
        )
    }]
    
    # Append the last two history exchanges to give context to search classification
    for val in past_history[-2:]:
        if isinstance(val, dict):
            preflight_messages.append({"role": val.get("role", "user"), "content": val.get("content", "")})
            
    preflight_messages.append({"role": "user", "content": message})
    
    try:
        is_gemma_mode = "Fast" in brain_state or "Analysis" in brain_state
        preflight_client = gemma_client if is_gemma_mode else groq_client
        preflight_model = GEMMA_MODEL if is_gemma_mode else "llama-3.1-8b-instant"
        
        # Check content moderation using OpenAI Moderations API if supported by the client
        if hasattr(preflight_client, "moderations"):
            try:
                await preflight_client.moderations.create(input=message)
            except Exception:
                pass

        # Gemma compatibility note: Gemma doesn't support response_format={"type":"json_object"}
        if is_gemma_mode:
            preflight_messages[0]["content"] += " Output ONLY a raw JSON object with no markdown or extra text."
            preflight_response = await asyncio.wait_for(
                preflight_client.chat.completions.create(
                    messages=preflight_messages,
                    model=preflight_model,
                    temperature=0.1,
                    max_tokens=200,
                    user="lumina-preflight"
                ),
                timeout=PREFLIGHT_TIMEOUT_SECONDS,
            )
        else:
            preflight_response = await asyncio.wait_for(
                preflight_client.chat.completions.create(
                    messages=preflight_messages,
                    model=preflight_model,
                    temperature=0.1,
                    max_tokens=200,
                    response_format={"type": "json_object"},
                    user="lumina-preflight"
                ),
                timeout=PREFLIGHT_TIMEOUT_SECONDS,
            )
            
        if hasattr(preflight_response.choices[0].message, "refusal") and preflight_response.choices[0].message.refusal:
            print(f"[Routing] Request refused: {preflight_response.choices[0].message.refusal}")
            return {"needs_search": False}
            
        content = getattr(preflight_response.choices[0].message, "content", "").strip()
        # strip markdown code blocks if the LLM output it wrapped in ```json ... ```
        if content.startswith("```"):
            content = content.strip("`").replace("json", "", 1).strip()
            
        return json.loads(content)
    except Exception as e:
        print(f"[Routing] Search pre-flight classification error: {e}")
        return {"needs_search": False}
