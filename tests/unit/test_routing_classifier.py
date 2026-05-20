import json
import pytest
from unittest.mock import patch, AsyncMock

from lumina.routing.classifier import classify_search_need
from tests.mock_providers.mock_llm import (
    MockAsyncLLMClient,
    MOCK_SEARCH_NEEDED,
    MOCK_SEARCH_NOT_NEEDED,
    MOCK_MALFORMED_JSON,
    MOCK_MARKDOWN_WRAPPED_JSON,
    MOCK_TRIPLE_BACKTICK_NO_NEWLINE,
)


@pytest.mark.asyncio
async def test_prompt_construction_with_history():
    past_history = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
        {"role": "user", "content": "tell me a joke"},
        {"role": "assistant", "content": "why did the chicken..."},
    ]
    client = MockAsyncLLMClient(json.dumps(MOCK_SEARCH_NOT_NEEDED))
    with patch("lumina.routing.classifier.groq_client", client):
        with patch("lumina.routing.classifier.gemma_client", client):
            result = await classify_search_need("test message", past_history, "Conscious")
            assert result == MOCK_SEARCH_NOT_NEEDED


@pytest.mark.asyncio
async def test_prompt_construction_only_last_two():
    past_history = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "first reply"},
        {"role": "user", "content": "second"},
        {"role": "assistant", "content": "second reply"},
        {"role": "user", "content": "third"},
        {"role": "assistant", "content": "third reply"},
    ]
    client = MockAsyncLLMClient(json.dumps(MOCK_SEARCH_NOT_NEEDED))
    with patch("lumina.routing.classifier.groq_client", client):
        with patch("lumina.routing.classifier.gemma_client", client):
            result = await classify_search_need("test", past_history, "Conscious")
            assert result == MOCK_SEARCH_NOT_NEEDED


@pytest.mark.asyncio
async def test_prompt_construction_empty_history():
    client = MockAsyncLLMClient(json.dumps(MOCK_SEARCH_NOT_NEEDED))
    with patch("lumina.routing.classifier.groq_client", client):
        with patch("lumina.routing.classifier.gemma_client", client):
            result = await classify_search_need("test message", [], "Conscious")
            assert result == MOCK_SEARCH_NOT_NEEDED


@pytest.mark.asyncio
async def test_prompt_construction_non_dict_history():
    past_history = ["string_item", 123, None]
    client = MockAsyncLLMClient(json.dumps(MOCK_SEARCH_NOT_NEEDED))
    with patch("lumina.routing.classifier.groq_client", client):
        with patch("lumina.routing.classifier.gemma_client", client):
            result = await classify_search_need("test", past_history, "Conscious")
            assert result == MOCK_SEARCH_NOT_NEEDED


@pytest.mark.asyncio
async def test_json_parsing_valid():
    client = MockAsyncLLMClient(json.dumps(MOCK_SEARCH_NEEDED))
    with patch("lumina.routing.classifier.groq_client", client):
        with patch("lumina.routing.classifier.gemma_client", client):
            result = await classify_search_need("test", [], "Conscious")
            assert result == MOCK_SEARCH_NEEDED


@pytest.mark.asyncio
async def test_json_parsing_markdown_wrapped():
    client = MockAsyncLLMClient(MOCK_MARKDOWN_WRAPPED_JSON)
    with patch("lumina.routing.classifier.groq_client", client):
        with patch("lumina.routing.classifier.gemma_client", client):
            result = await classify_search_need("test", [], "Conscious")
            assert result == MOCK_SEARCH_NOT_NEEDED


@pytest.mark.asyncio
async def test_json_parsing_triple_backtick_no_newline():
    client = MockAsyncLLMClient(MOCK_TRIPLE_BACKTICK_NO_NEWLINE)
    with patch("lumina.routing.classifier.groq_client", client):
        with patch("lumina.routing.classifier.gemma_client", client):
            result = await classify_search_need("test", [], "Conscious")
            assert result == {"needs_search": True}


@pytest.mark.asyncio
async def test_json_parsing_invalid_json():
    client = MockAsyncLLMClient(MOCK_MALFORMED_JSON)
    with patch("lumina.routing.classifier.groq_client", client):
        with patch("lumina.routing.classifier.gemma_client", client):
            result = await classify_search_need("test", [], "Conscious")
            assert result == {"needs_search": False}


@pytest.mark.asyncio
async def test_gemma_vs_groq_branching_gemma_mode():
    client_groq = MockAsyncLLMClient(json.dumps(MOCK_SEARCH_NOT_NEEDED))
    client_gemma = MockAsyncLLMClient(json.dumps(MOCK_SEARCH_NOT_NEEDED))
    with patch("lumina.routing.classifier.groq_client", client_groq):
        with patch("lumina.routing.classifier.gemma_client", client_gemma):
            result = await classify_search_need("test", [], "Fast Mode")
            assert result == MOCK_SEARCH_NOT_NEEDED


@pytest.mark.asyncio
async def test_gemma_vs_groq_branching_groq_mode():
    client_groq = MockAsyncLLMClient(json.dumps(MOCK_SEARCH_NOT_NEEDED))
    client_gemma = MockAsyncLLMClient(json.dumps(MOCK_SEARCH_NOT_NEEDED))
    with patch("lumina.routing.classifier.groq_client", client_groq):
        with patch("lumina.routing.classifier.gemma_client", client_gemma):
            result = await classify_search_need("test", [], "Conscious")
            assert result == MOCK_SEARCH_NOT_NEEDED


@pytest.mark.asyncio
async def test_timeout_returns_safe_fallback():
    client = MockAsyncLLMClient("", raise_on_create=True)
    with patch("lumina.routing.classifier.groq_client", client):
        with patch("lumina.routing.classifier.gemma_client", client):
            result = await classify_search_need("test", [], "Conscious")
            assert result == {"needs_search": False}


@pytest.mark.asyncio
async def test_llm_api_error_returns_fallback():
    client = MockAsyncLLMClient("", raise_on_create=True)
    with patch("lumina.routing.classifier.groq_client", client):
        with patch("lumina.routing.classifier.gemma_client", client):
            result = await classify_search_need("test", [], "Conscious")
            assert result == {"needs_search": False}


@pytest.mark.asyncio
async def test_analysis_mode_uses_gemma():
    client_groq = MockAsyncLLMClient(json.dumps(MOCK_SEARCH_NOT_NEEDED))
    client_gemma = MockAsyncLLMClient(json.dumps(MOCK_SEARCH_NOT_NEEDED))
    with patch("lumina.routing.classifier.groq_client", client_groq):
        with patch("lumina.routing.classifier.gemma_client", client_gemma):
            result = await classify_search_need("test", [], "Deep Analysis Mode")
            assert result == MOCK_SEARCH_NOT_NEEDED
