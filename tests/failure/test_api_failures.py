import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from lumina.routing.classifier import classify_search_need
from lumina.image.engine import generate_image_async, PROVIDERS


@pytest.mark.asyncio
async def test_classify_groq_429_rate_limit():
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("429 Too Many Requests")

    with patch("lumina.routing.classifier.groq_client", mock_client):
        with patch("lumina.routing.classifier.gemma_client") as gemma_mock:
            result = await classify_search_need("hello", [], "Conscious")
            assert result == {"needs_search": False}


@pytest.mark.asyncio
async def test_classify_gemma_500_error():
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("500 Internal Server Error")

    with patch("lumina.routing.classifier.gemma_client", mock_client):
        result = await classify_search_need("hello", [], "Fast Mode")
        assert result == {"needs_search": False}


@pytest.mark.asyncio
async def test_classify_empty_response():
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = ""

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    with patch("lumina.routing.classifier.groq_client", mock_client):
        with patch("lumina.routing.classifier.gemma_client") as gemma_mock:
            result = await classify_search_need("hello", [], "Conscious")
            assert result == {"needs_search": False}


@pytest.mark.asyncio
async def test_classify_partial_response():
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = '{"needs_search":'

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    with patch("lumina.routing.classifier.groq_client", mock_client):
        with patch("lumina.routing.classifier.gemma_client") as gemma_mock:
            result = await classify_search_need("hello", [], "Conscious")
            assert result == {"needs_search": False}


@pytest.mark.asyncio
async def test_classify_all_providers_503_simultaneously():
    groq_mock = MagicMock()
    groq_mock.chat.completions.create.side_effect = Exception("503 Service Unavailable")

    gemma_mock = MagicMock()
    gemma_mock.chat.completions.create.side_effect = Exception("503 Service Unavailable")

    with patch("lumina.routing.classifier.groq_client", groq_mock):
        with patch("lumina.routing.classifier.gemma_client", gemma_mock):
            result = await classify_search_need("hello", [], "Conscious")
            assert result == {"needs_search": False}


@pytest.mark.asyncio
async def test_image_all_providers_http_error():
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("HTTP 503")
    mock_session.post.return_value = mock_response
    mock_session.get.return_value = mock_response

    with patch("lumina.image.engine.make_session", return_value=mock_session):
        with patch("lumina.image.engine.download_url", return_value=False):
            with patch("lumina.image.engine.GOOGLE_API_KEY", "fake_key"):
                with patch("lumina.image.engine.os.getenv", return_value="fake_key"):
                    result = await generate_image_async("test prompt")
                    assert result is not None
                    assert "error card" not in str(result).lower()


@pytest.mark.asyncio
async def test_image_provider_429_retry():
    call_count = 0

    def flaky_download(url, filepath, retries=2, wait=3):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            return False
        return True

    with patch("lumina.image.engine.download_url", side_effect=flaky_download):
        with patch("lumina.image.engine.GOOGLE_API_KEY", None):
            with patch("lumina.image.engine.os.getenv", return_value=None):
                result = await generate_image_async("test prompt")
                assert result is not None
