import asyncio
import pytest
from unittest.mock import patch, MagicMock, mock_open

from lumina.routing.classifier import classify_search_need
from lumina.memory.history import save_chat, load_chat


@pytest.mark.asyncio
async def test_long_10k_history_classification():
    history = [{"role": "user", "content": "x" * 1000} for _ in range(10)]

    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = '{"needs_search": false}'

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    with patch("lumina.routing.classifier.groq_client", mock_client):
        with patch("lumina.routing.classifier.gemma_client", mock_client):
            result = await classify_search_need("hello", history, "Conscious")
            assert result == {"needs_search": False}


@pytest.mark.asyncio
async def test_long_100k_history_no_memory_error():
    history = [{"role": "user", "content": "x" * 5000} for _ in range(20)]

    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = '{"needs_search": false}'

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    with patch("lumina.routing.classifier.groq_client", mock_client):
        with patch("lumina.routing.classifier.gemma_client", mock_client):
            result = await classify_search_need("hello", history, "Conscious")
            assert result == {"needs_search": False}


def test_long_history_save_load_roundtrip():
    long_history = [{"role": "user", "content": f"message {i}"} for i in range(500)]
    buf = __import__("io").StringIO()

    def saving_open(*args, **kwargs):
        if len(args) > 1 and args[1] == "w":
            m = mock_open()
            m.return_value.write.side_effect = buf.write
            return m.return_value
        m = mock_open(read_data=buf.getvalue() or '{"history": []}')
        return m.return_value

    with patch("builtins.open", saving_open):
        with patch("os.path.exists", return_value=True):
            save_chat("long-test", long_history)
            loaded = load_chat("long-test")

    assert len(loaded) == 500


def test_mixed_media_history():
    mixed = [
        {"role": "user", "content": "text message"},
        {"role": "user", "content": "[IMAGE_PROMPT: a cat]"},
        {"role": "user", "content": "another text"},
    ]
    buf = __import__("io").StringIO()

    def saving_open(*args, **kwargs):
        if len(args) > 1 and args[1] == "w":
            m = mock_open()
            m.return_value.write.side_effect = buf.write
            return m.return_value
        m = mock_open(read_data=buf.getvalue() or '{"history": []}')
        return m.return_value

    with patch("builtins.open", saving_open):
        with patch("os.path.exists", return_value=True):
            save_chat("mixed-test", mixed)
            loaded = load_chat("mixed-test")

    assert len(loaded) == 3
    assert "[IMAGE_PROMPT:" in loaded[1]["content"]
