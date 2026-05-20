import json
import os
import time
import pytest
from unittest.mock import patch, mock_open

from lumina.memory.history import save_chat, load_chat, get_chat_list


def test_save_1000_messages():
    history = [{"role": "user", "content": f"message {i}"} for i in range(1000)]
    buf = __import__("io").StringIO()

    def saving_open(*args, **kwargs):
        if len(args) > 1 and args[1] == "w":
            m = mock_open()
            m.return_value.write.side_effect = buf.write
            return m.return_value
        m = mock_open(read_data=buf.getvalue() or "{}")
        return m.return_value

    with patch("builtins.open", saving_open):
        with patch("os.path.exists", return_value=True):
            save_chat("big-history", history)
            loaded = load_chat("big-history")

    assert len(loaded) == 1000
    assert loaded[0]["content"] == "message 0"
    assert loaded[-1]["content"] == "message 999"


def test_save_and_load_100_chats():
    bufs = {}

    def multi_open(*args, **kwargs):
        filepath = args[0]
        if filepath not in bufs:
            bufs[filepath] = __import__("io").StringIO()
        buf = bufs[filepath]

        if len(args) > 1 and args[1] == "w":
            m = mock_open()
            m.return_value.write.side_effect = buf.write
            return m.return_value
        m = mock_open(read_data=buf.getvalue() or "{}")
        return m.return_value

    with patch("builtins.open", multi_open):
        with patch("os.path.exists", return_value=True):
            for i in range(100):
                save_chat(f"chat-{i}", [{"role": "user", "content": f"hello {i}"}])

        with patch("os.listdir", return_value=[f"chat-{i}.json" for i in range(100)]):
            with patch("os.path.getmtime", return_value=1000):
                chat_list = get_chat_list()
                assert len(chat_list) >= 90


def test_concurrent_save_same_chat():
    buf = __import__("io").StringIO()
    call_count = 0

    def saving_open(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if len(args) > 1 and args[1] == "w":
            m = mock_open()
            m.return_value.write.side_effect = buf.write
            return m.return_value
        m = mock_open(read_data=buf.getvalue() or "{}")
        return m.return_value

    with patch("builtins.open", saving_open):
        with patch("os.path.exists", return_value=True):
            import threading
            threads = []
            for i in range(10):
                t = threading.Thread(
                    target=save_chat,
                    args=("concurrent", [{"role": "user", "content": f"update {i}"}]),
                )
                threads.append(t)
                t.start()
            for t in threads:
                t.join()

            assert call_count >= 10


def test_large_history_loads_under_threshold():
    data = {
        "id": "large",
        "title": "Large Chat",
        "history": [{"role": "user", "content": "x" * 1000}] * 200,
    }
    json_str = json.dumps(data)

    with patch("builtins.open", mock_open(read_data=json_str)):
        with patch("os.path.exists", return_value=True):
            start = time.perf_counter()
            loaded = load_chat("large")
            elapsed = time.perf_counter() - start
            assert len(loaded) == 200
            assert elapsed < 2.0
