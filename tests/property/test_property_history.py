import json
import io
import pytest
from unittest.mock import patch, mock_open
from hypothesis import given, strategies as st, assume

from lumina.memory.history import save_chat, load_chat


@given(
    chat_id=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=["L", "N", "P"])),
    num_messages=st.integers(min_value=0, max_value=20),
)
@pytest.mark.property
def test_save_load_roundtrip_property(chat_id, num_messages):
    assume(chat_id.strip())
    history = []
    for i in range(num_messages):
        role = "user" if i % 2 == 0 else "assistant"
        history.append({"role": role, "content": f"message {i}"})

    buf = io.StringIO()

    def saving_open(*args, **kwargs):
        if len(args) > 1 and args[1] == "w":
            m = mock_open()
            m.return_value.write.side_effect = buf.write
            return m.return_value
        m = mock_open(read_data=buf.getvalue() or "{}")
        return m.return_value

    with patch("builtins.open", saving_open):
        with patch("os.path.exists", return_value=True):
            save_chat(chat_id, history)
            loaded = load_chat(chat_id)

    assert len(loaded) == num_messages
    for original, loaded_msg in zip(history, loaded):
        assert loaded_msg["role"] == original["role"]
        assert loaded_msg["content"] == original["content"]


@given(
    content=st.text(min_size=0, max_size=50),
)
@pytest.mark.property
def test_title_never_exceeds_30_chars(content):
    history = [{"role": "user", "content": content}]
    buf = io.StringIO()

    def saving_open(*args, **kwargs):
        if len(args) > 1 and args[1] == "w":
            m = mock_open()
            m.return_value.write.side_effect = buf.write
            return m.return_value
        m = mock_open(read_data=buf.getvalue() or "{}")
        return m.return_value

    with patch("builtins.open", saving_open):
        with patch("os.path.exists", return_value=True):
            save_chat("prop-test", history)

    written = buf.getvalue()
    if written:
        data = json.loads(written)
        title = data.get("title", "")
        assert len(title) <= 33
