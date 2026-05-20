from lumina.providers.llm import groq_client, gemma_client
from lumina.core.config import (
    GEMMA_MODEL,
    SYSTEM_PROMPT,
    SUBCONSCIOUS_PROMPT,
    GEMMA_FAST_PROMPT,
    GEMMA_ANALYSIS_PROMPT,
    CHILL_PROMPT
)

def get_brain_state_params(brain_state: str, model_selector: str):
    """
    Selects model, client, temperature, max tokens, and system prompt 
    according to brain state settings and model overrides.
    """
    # Defaults
    active_client = groq_client
    model_name = "llama-3.3-70b-versatile"
    current_temp = 0.7
    max_tok = 2048
    system_prompt = SYSTEM_PROMPT

    # Handle model selector override
    if model_selector == "Groq Llama 3.1 8B Instant":
        model_name = "llama-3.1-8b-instant"
        active_client = groq_client
    elif model_selector == "Google Gemma 4 31B":
        model_name = GEMMA_MODEL
        active_client = gemma_client
    elif model_selector == "Groq Llama 3.3 70B Versatile":
        model_name = "llama-3.3-70b-versatile"
        active_client = groq_client

    # Adjust based on brain state
    if "Subconscious" in brain_state:
        system_prompt = SUBCONSCIOUS_PROMPT
        if model_name != "llama-3.1-8b-instant":
            model_name = "llama-3.1-8b-instant"
            active_client = groq_client
        current_temp = 1.2
        max_tok = 2048
    elif "Fast" in brain_state:
        system_prompt = GEMMA_FAST_PROMPT
        if model_name != GEMMA_MODEL:
            model_name = GEMMA_MODEL
            active_client = gemma_client
        current_temp = 0.7
        max_tok = 1024
    elif "Analysis" in brain_state:
        system_prompt = GEMMA_ANALYSIS_PROMPT
        if model_name != GEMMA_MODEL:
            model_name = GEMMA_MODEL
            active_client = gemma_client
        current_temp = 0.5
        max_tok = 4096
    elif "Chill" in brain_state:
        system_prompt = CHILL_PROMPT
        if model_name != "llama-3.1-8b-instant":
            model_name = "llama-3.1-8b-instant"
            active_client = groq_client
        current_temp = 0.8
        max_tok = 1024
    else:
        system_prompt = SYSTEM_PROMPT
        if model_name != "llama-3.3-70b-versatile":
            model_name = "llama-3.3-70b-versatile"
            active_client = groq_client
        current_temp = 0.7
        max_tok = 2048

    return active_client, model_name, current_temp, max_tok, system_prompt
