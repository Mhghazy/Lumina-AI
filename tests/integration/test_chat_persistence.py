import io
import json
import pytest
from unittest.mock import patch, mock_open

from lumina.memory.history import save_chat, load_chat


@pytest.mark.smoke
def test_save_then_load_roundtrip():
    history = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "world"},
    ]

    buf = io.StringIO()

    def saving_open(*args, **kwargs):
        if "w" in str(args) or kwargs.get("mode") == "w":
            m = mock_open()
            m.return_value.write.side_effect = buf.write
            return m.return_value
        m = mock_open(read_data=buf.getvalue() or "{}")
        return m.return_value

    with patch("builtins.open", saving_open):
        with patch("os.path.exists", return_value=True):
            save_chat("roundtrip-id", history)
            loaded = load_chat("roundtrip-id")

    assert len(loaded) == 2
    assert loaded[0]["role"] == "user"
    assert loaded[0]["content"] == "hello"
    assert loaded[1]["role"] == "assistant"
    assert loaded[1]["content"] == "world"


def test_save_then_load_tuple_history():
    tuple_history = [("hello", "world")]
    buf = io.StringIO()

    def saving_open(*args, **kwargs):
        if "w" in str(args) or kwargs.get("mode") == "w":
            m = mock_open()
            m.return_value.write.side_effect = buf.write
            return m.return_value
        m = mock_open(read_data=buf.getvalue() or "{}")
        return m.return_value

    with patch("builtins.open", saving_open):
        with patch("os.path.exists", return_value=True):
            save_chat("tuple-id", tuple_history)
            loaded = load_chat("tuple-id")

    assert len(loaded) == 2
    assert loaded[0]["content"] == "hello"
    assert loaded[1]["content"] == "world"
