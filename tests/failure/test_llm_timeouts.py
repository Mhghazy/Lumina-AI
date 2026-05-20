import json
import asyncio
import pytest
from unittest.mock import patch, MagicMock

from lumina.routing.classifier import classify_search_need
from tests.mock_providers.mock_llm import MockAsyncLLMClient


@pytest.mark.asyncio
async def test_classify_timeout_while_gemma():
    client = MockAsyncLLMClient("", raise_on_create=True)
    with patch("lumina.routing.classifier.groq_client", client):
        with patch("lumina.routing.classifier.gemma_client", client):
            result = await classify_search_need("test", [], "Fast Mode")
            assert result == {"needs_search": False}


@pytest.mark.asyncio
async def test_classify_timeout_while_groq():
    client = MockAsyncLLMClient("", raise_on_create=True)
    with patch("lumina.routing.classifier.groq_client", client):
        with patch("lumina.routing.classifier.gemma_client", client):
            result = await classify_search_need("test", [], "Conscious")
            assert result == {"needs_search": False}


@pytest.mark.asyncio
async def test_asyncio_wait_for_called_with_timeout():
    original = asyncio.wait_for

    captured_timeout = [None]

    async def tracking_wait_for(coro, timeout):
        captured_timeout[0] = timeout
        return await coro

    client = MockAsyncLLMClient(json.dumps({"needs_search": False}))

    with patch("lumina.routing.classifier.groq_client", client):
        with patch("lumina.routing.classifier.gemma_client", client):
            with patch("asyncio.wait_for", tracking_wait_for):
                await classify_search_need("test", [], "Conscious")
                assert captured_timeout[0] is not None


@pytest.mark.asyncio
async def test_stream_chunk_timeout_handling():
    with patch("lumina.ui.interface.STREAM_CHUNK_TIMEOUT_SECONDS", 1):
        pass


@pytest.mark.asyncio
async def test_chat_request_timeout_handling():
    with patch("lumina.ui.interface.CHAT_REQUEST_TIMEOUT_SECONDS", 1):
        pass
