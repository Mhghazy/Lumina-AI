import pytest
from lumina.models.brain import get_brain_state_params
from lumina.providers.llm import groq_client, gemma_client
from lumina.core.config import (
    SYSTEM_PROMPT,
    SUBCONSCIOUS_PROMPT,
    GEMMA_FAST_PROMPT,
    GEMMA_ANALYSIS_PROMPT,
    CHILL_PROMPT,
    GEMMA_MODEL,
)


@pytest.mark.smoke
def test_conscious_mode_defaults():
    client, model, temp, max_tok, prompt = get_brain_state_params(
        "🧠 Conscious Mode (Full Power)", "Groq Llama 3.3 70B Versatile"
    )
    assert client == groq_client
    assert model == "llama-3.3-70b-versatile"
    assert temp == 0.7
    assert max_tok == 2048
    assert prompt == SYSTEM_PROMPT


def test_fast_mode():
    client, model, temp, max_tok, prompt = get_brain_state_params(
        "⚡ Fast Mode (Quick & Snappy)", "Groq Llama 3.3 70B Versatile"
    )
    assert client == gemma_client
    assert model == GEMMA_MODEL
    assert temp == 0.7
    assert max_tok == 1024
    assert prompt == GEMMA_FAST_PROMPT


def test_analysis_mode():
    client, model, temp, max_tok, prompt = get_brain_state_params(
        "🔬 Deep Analysis Mode (Rigorous Thinking)", "Groq Llama 3.3 70B Versatile"
    )
    assert client == gemma_client
    assert model == GEMMA_MODEL
    assert temp == 0.5
    assert max_tok == 4096
    assert prompt == GEMMA_ANALYSIS_PROMPT


def test_chill_mode():
    client, model, temp, max_tok, prompt = get_brain_state_params(
        "🍸 Chill Mode (No Overthinking)", "Groq Llama 3.3 70B Versatile"
    )
    assert client == groq_client
    assert model == "llama-3.1-8b-instant"
    assert temp == 0.8
    assert max_tok == 1024
    assert prompt == CHILL_PROMPT


def test_subconscious_mode():
    client, model, temp, max_tok, prompt = get_brain_state_params(
        "💤 Subconscious Mode (Power Saving)", "Groq Llama 3.3 70B Versatile"
    )
    assert client == groq_client
    assert model == "llama-3.1-8b-instant"
    assert temp == 1.2
    assert max_tok == 2048
    assert prompt == SUBCONSCIOUS_PROMPT


def test_model_selector_conscious_default_stays():
    client, model, temp, max_tok, prompt = get_brain_state_params(
        "🧠 Conscious Mode (Full Power)", "Groq Llama 3.3 70B Versatile"
    )
    assert client == groq_client
    assert model == "llama-3.3-70b-versatile"


def test_model_selector_conscious_gemma_overridden():
    client, model, temp, max_tok, prompt = get_brain_state_params(
        "🧠 Conscious Mode (Full Power)", "Google Gemma 4 31B"
    )
    assert client == groq_client
    assert model == "llama-3.3-70b-versatile"


def test_model_selector_llama_31_overridden():
    client, model, temp, max_tok, prompt = get_brain_state_params(
        "🧠 Conscious Mode (Full Power)", "Groq Llama 3.1 8B Instant"
    )
    assert client == groq_client
    assert model == "llama-3.3-70b-versatile"


def test_model_selector_subconscious_forced():
    client, model, temp, max_tok, prompt = get_brain_state_params(
        "💤 Subconscious Mode (Power Saving)", "Google Gemma 4 31B"
    )
    assert model == "llama-3.1-8b-instant"


def test_brain_state_overrides_selector():
    client, model, temp, max_tok, prompt = get_brain_state_params(
        "⚡ Fast Mode (Quick & Snappy)", "Groq Llama 3.3 70B Versatile"
    )
    assert client == gemma_client
    assert model == GEMMA_MODEL


def test_unrecognized_brain_state_falls_to_default():
    client, model, temp, max_tok, prompt = get_brain_state_params(
        "Unknown State", "Groq Llama 3.3 70B Versatile"
    )
    assert client == groq_client
    assert model == "llama-3.3-70b-versatile"
    assert temp == 0.7
    assert max_tok == 2048
    assert prompt == SYSTEM_PROMPT


def test_subconscious_truncates_history():
    _, _, _, _, prompt = get_brain_state_params(
        "💤 Subconscious Mode (Power Saving)", "Groq Llama 3.3 70B Versatile"
    )
    assert prompt == SUBCONSCIOUS_PROMPT


def test_fast_mode_uses_gemma_model():
    _, model, _, _, _ = get_brain_state_params(
        "⚡ Fast Mode (Quick & Snappy)", "Groq Llama 3.1 8B Instant"
    )
    assert model == GEMMA_MODEL


def test_chill_mode_uses_llama_31():
    _, model, _, _, _ = get_brain_state_params(
        "🍸 Chill Mode (No Overthinking)", "Google Gemma 4 31B"
    )
    assert model == "llama-3.1-8b-instant"
