import json
import pytest
from unittest.mock import patch, MagicMock, mock_open

from lumina.memory.history import save_chat, load_chat, get_chat_list


class TestSaveChat:
    def test_title_from_first_user_message(self):
        history = [{"role": "user", "content": "Hello world, this is a long message"}]
        with patch("builtins.open", mock_open()) as m:
            save_chat("test-id", history)
            handle = m()
            written = "".join(call[0][0] for call in handle.write.call_args_list)
            data = json.loads(written)
            assert "Hello world, this is a long" in data["title"]
            assert len(data["title"]) <= 33

    def test_title_from_tuple_format(self):
        history = [("hello there", "hi back")]
        with patch("builtins.open", mock_open()) as m:
            save_chat("test-id", history)
            handle = m()
            written = "".join(call[0][0] for call in handle.write.call_args_list)
            data = json.loads(written)
            assert "hello there" in data["title"]

    def test_title_empty_history(self):
        with patch("builtins.open", mock_open()) as m:
            save_chat("test-id", [])
            handle = m()
            written = "".join(call[0][0] for call in handle.write.call_args_list)
            data = json.loads(written)
            assert data["title"] == "New Chat"

    def test_title_non_string_content(self):
        history = [{"role": "user", "content": 12345}]
        with patch("builtins.open", mock_open()) as m:
            save_chat("test-id", history)
            handle = m()
            written = "".join(call[0][0] for call in handle.write.call_args_list)
            data = json.loads(written)
            assert "12345" in data["title"]

    def test_saves_correct_structure(self):
        history = [{"role": "user", "content": "hi"}]
        with patch("builtins.open", mock_open()) as m:
            save_chat("test-id", history)
            handle = m()
            written = "".join(call[0][0] for call in handle.write.call_args_list)
            data = json.loads(written)
            assert data["id"] == "test-id"
            assert "history" in data
            assert "updated_at" in data
            assert "title" in data


class TestLoadChat:
    def test_normalizes_dict_format(self):
        chat_data = json.dumps({
            "id": "test",
            "history": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "world"}
            ]
        })
        with patch("builtins.open", mock_open(read_data=chat_data)):
            with patch("os.path.exists", return_value=True):
                result = load_chat("test-id")
                assert len(result) == 2
                assert result[0]["role"] == "user"
                assert result[0]["content"] == "hello"

    def test_normalizes_tuple_format(self):
        chat_data = json.dumps({
            "id": "test",
            "history": [["hello", "world"]]
        })
        with patch("builtins.open", mock_open(read_data=chat_data)):
            with patch("os.path.exists", return_value=True):
                result = load_chat("test-id")
                assert len(result) == 2
                assert result[0]["role"] == "user"
                assert result[0]["content"] == "hello"
                assert result[1]["role"] == "assistant"
                assert result[1]["content"] == "world"

    def test_empty_tuple_entries_skipped(self):
        chat_data = json.dumps({
            "id": "test",
            "history": [["", ""]]
        })
        with patch("builtins.open", mock_open(read_data=chat_data)):
            with patch("os.path.exists", return_value=True):
                result = load_chat("test-id")
                assert len(result) == 0

    def test_file_not_found(self):
        with patch("os.path.exists", return_value=False):
            result = load_chat("nonexistent")
            assert result == []

    def test_corrupt_json(self):
        with patch("builtins.open", mock_open(read_data="not json")):
            with patch("os.path.exists", return_value=True):
                result = load_chat("test-id")
                assert result == []

    def test_empty_chat_id(self):
        assert load_chat(None) == []
        assert load_chat("") == []

    def test_partial_tuple(self):
        chat_data = json.dumps({
            "id": "test",
            "history": [["hello", None]]
        })
        with patch("builtins.open", mock_open(read_data=chat_data)):
            with patch("os.path.exists", return_value=True):
                result = load_chat("test-id")
                assert len(result) == 1
                assert result[0]["content"] == "hello"


class TestGetChatList:
    def test_skips_non_json_files(self):
        with patch("os.listdir", return_value=["file.txt", "data.csv"]):
            with patch("os.path.getmtime", return_value=0):
                result = get_chat_list()
                assert result == []

    def test_sorts_by_mtime(self):
        with patch("os.listdir", return_value=["a.json", "b.json"]):
            with patch("builtins.open") as m_open:
                m_open.return_value.__enter__.return_value.read.side_effect = [
                    json.dumps({"id": "a", "title": "Chat A", "updated_at": "2024-01-01"}),
                    json.dumps({"id": "b", "title": "Chat B", "updated_at": "2024-01-02"}),
                ]
                with patch("os.path.getmtime", side_effect=[100, 200]):
                    result = get_chat_list()
                    assert len(result) == 2

    def test_skips_corrupt_json(self):
        with patch("os.listdir", return_value=["a.json", "b.json"]):
            with patch("builtins.open") as m_open:
                m_open.return_value.__enter__.return_value.read.side_effect = [
                    "not json",
                    json.dumps({"id": "b", "title": "Chat B"}),
                ]
                with patch("os.path.getmtime", return_value=100):
                    result = get_chat_list()
                    assert len(result) == 1
