import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from lumina.routing.classifier import classify_search_need


class MockCompletion:
    def __init__(self, content: str):
        self.choices = [MagicMock()]
        self.choices[0].message.content = content


CONCURRENT_MESSAGES = [
    "What is the weather in London?",
    "Tell me a joke",
    "Explain quantum computing",
    "Write a poem",
    "How do I code in Python?",
    "What's the news today?",
    "Solve 2+2",
    "What is AI?",
    "Tell me about history",
    "Give me a recipe",
    "Explain gravity",
    "What is machine learning?",
    "Write a song",
    "How are you?",
    "What is the capital of France?",
    "Explain DNA",
    "Tell me a fun fact",
    "What is the meaning of life?",
    "How do rockets work?",
    "Define recursion",
]


@pytest.mark.asyncio
async def test_10_concurrent_classify_requests():
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = '{"needs_search": false}'

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    with patch("lumina.routing.classifier.groq_client", mock_client):
        with patch("lumina.routing.classifier.gemma_client", mock_client):
            tasks = [
                classify_search_need(msg, [], "Conscious")
                for msg in CONCURRENT_MESSAGES[:10]
            ]
            results = await asyncio.gather(*tasks)
            assert len(results) == 10
            assert all(r == {"needs_search": False} for r in results)


@pytest.mark.asyncio
async def test_20_concurrent_classify_mixed_states():
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = '{"needs_search": false}'

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    states = ["Conscious", "Fast", "Analysis", "Chill", "Subconscious"]

    with patch("lumina.routing.classifier.groq_client", mock_client):
        with patch("lumina.routing.classifier.gemma_client", mock_client):
            tasks = [
                classify_search_need(CONCURRENT_MESSAGES[i], [], states[i % len(states)])
                for i in range(20)
            ]
            results = await asyncio.gather(*tasks)
            assert len(results) == 20


@pytest.mark.asyncio
async def test_50_concurrent_requests_graceful_degradation():
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = '{"needs_search": true, "query": "test", "type": "text"}'

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    with patch("lumina.routing.classifier.groq_client", mock_client):
        with patch("lumina.routing.classifier.gemma_client", mock_client):
            tasks = [
                classify_search_need(f"query {i}", [], "Conscious")
                for i in range(50)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successes = [r for r in results if isinstance(r, dict)]
            assert len(successes) >= 45
