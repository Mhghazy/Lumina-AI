import asyncio
import pytest
from unittest.mock import patch, MagicMock

from lumina.routing.classifier import classify_search_need


@pytest.mark.asyncio
async def test_concurrent_5_classify_requests():
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = '{"needs_search": false}'

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    with patch("lumina.routing.classifier.groq_client", mock_client):
        with patch("lumina.routing.classifier.gemma_client", mock_client):
            tasks = [
                classify_search_need(f"message {i}", [], "Conscious")
                for i in range(5)
            ]
            results = await asyncio.gather(*tasks)
            assert len(results) == 5
            for r in results:
                assert r == {"needs_search": False}


@pytest.mark.asyncio
async def test_concurrent_20_classify_no_cascade_timeout():
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = '{"needs_search": true, "query": "test", "type": "text"}'

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    with patch("lumina.routing.classifier.groq_client", mock_client):
        with patch("lumina.routing.classifier.gemma_client", mock_client):
            tasks = [
                classify_search_need(f"query {i}", [], "Conscious")
                for i in range(20)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successes = [r for r in results if isinstance(r, dict)]
            assert len(successes) >= 18


@pytest.mark.asyncio
async def test_concurrent_mixed_brain_states():
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = '{"needs_search": false}'

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    states = ["Conscious", "Fast", "Analysis", "Chill", "Subconscious"]
    with patch("lumina.routing.classifier.groq_client", mock_client):
        with patch("lumina.routing.classifier.gemma_client", mock_client):
            tasks = [
                classify_search_need(f"msg {i}", [], states[i % len(states)])
                for i in range(10)
            ]
            results = await asyncio.gather(*tasks)
            assert len(results) == 10
