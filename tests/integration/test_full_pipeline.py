import io
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, mock_open


class MockCompletion:
    def __init__(self, content: str):
        message_mock = MagicMock(content=content, refusal=None)
        delta_mock = MagicMock(content=content)
        self.choices = [MagicMock(message=message_mock, delta=delta_mock)]


class MockAsyncStream:
    def __init__(self, chunks: list):
        self._chunks = chunks
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._index >= len(self._chunks):
            raise StopAsyncIteration
        chunk = MagicMock()
        chunk.choices[0].delta.content = self._chunks[self._index]
        self._index += 1
        return chunk


@pytest.mark.asyncio
async def test_full_pipeline_no_internet():
    buf = io.StringIO()

    def saving_open(*args, **kwargs):
        if len(args) > 1 and args[1] == "w":
            m = mock_open()
            m.return_value.write.side_effect = buf.write
            return m.return_value
        m = mock_open(read_data=buf.getvalue() or json.dumps({"history": []}))
        return m.return_value

    mock_groq = MagicMock()
    mock_groq.chat = AsyncMock()
    mock_groq.chat.completions.create = AsyncMock()
    mock_groq.chat.completions.create.return_value = MockAsyncStream(["Hello! I'm Lumina, lovely to meet you! 😊"])

    mock_tts = AsyncMock()
    mock_tts.return_value = "/audio/test.wav"

    with patch("lumina.ui.interface.groq_client", mock_groq):
        with patch("lumina.ui.interface.get_brain_state_params") as mock_brain:
            mock_brain.return_value = (mock_groq, "llama-3.3-70b-versatile", 0.7, 4096, "You are Lumina")
            with patch("lumina.ui.interface.save_chat") as mock_save:
                with patch("lumina.ui.interface.generate_audio", mock_tts):
                    with patch("lumina.ui.interface.clean_text_for_speech") as mock_clean:
                        mock_clean.return_value = "Hello! I'm Lumina, lovely to meet you!"

                        from lumina.ui.interface import chat_with_lumina

                        results = []
                        async for result in chat_with_lumina(
                            "Hello!", [], None, "Conscious Mode (Full Power)",
                            "Groq Llama 3.3 70B Versatile", "English", "British (UK) - Sonia (Female)",
                            internet_access=False, search_engines=[]
                        ):
                            results.append(result)

                        assert len(results) > 0
                        final = results[-1]
                        assert final[1] is not None
                        last_history = final[1]
                        assert len(last_history) >= 2
                        assert last_history[-1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_full_pipeline_with_search():
    buf = io.StringIO()

    def saving_open(*args, **kwargs):
        if len(args) > 1 and args[1] == "w":
            m = mock_open()
            m.return_value.write.side_effect = buf.write
            return m.return_value
        m = mock_open(read_data=buf.getvalue() or json.dumps({"history": []}))
        return m.return_value

    mock_groq = MagicMock()
    mock_groq.chat = AsyncMock()
    mock_groq.chat.completions.create = AsyncMock()
    mock_groq.chat.completions.create.return_value = MockAsyncStream(
        ["According to search results, **Paris** is the capital of France! 🇫🇷\n\n[Source](http://example.com)"]
    )

    mock_classifier = AsyncMock()
    mock_classifier.return_value = {"needs_search": True, "query": "capital of France", "type": "text"}

    mock_tts = AsyncMock()
    mock_tts.return_value = "/audio/test.wav"

    with patch("lumina.ui.interface.groq_client", mock_groq):
        with patch("lumina.ui.interface.classify_search_need", mock_classifier):
            with patch("lumina.ui.interface.perform_search") as mock_search:
                mock_search.return_value = ("### Web Results\n- [France](http://france.fr)", [])
                with patch("lumina.ui.interface.get_brain_state_params") as mock_brain:
                    mock_brain.return_value = (mock_groq, "llama-3.3-70b-versatile", 0.7, 4096, "You are Lumina")
                    with patch("lumina.ui.interface.save_chat") as mock_save:
                        with patch("lumina.ui.interface.generate_audio", mock_tts):
                            with patch("lumina.ui.interface.clean_text_for_speech") as mock_clean:
                                mock_clean.return_value = "Paris is the capital of France"

                                from lumina.ui.interface import chat_with_lumina

                                results = []
                                async for result in chat_with_lumina(
                                    "What is the capital of France?", [], None,
                                    "Conscious Mode (Full Power)", "Groq Llama 3.3 70B Versatile",
                                    "English", "British (UK) - Sonia (Female)",
                                    internet_access=True, search_engines=["Google", "Wikipedia"]
                                ):
                                    results.append(result)

                                assert len(results) > 0
                                final = results[-1]
                                assert final[1] is not None
                                mock_classifier.assert_called_once()
                                mock_search.assert_called_once()


@pytest.mark.asyncio
async def test_full_pipeline_gemma_non_streaming():
    mock_gemma = MagicMock()
    mock_gemma.chat = AsyncMock()
    mock_gemma.chat.completions.create = AsyncMock()
    mock_gemma.chat.completions.create.return_value = MockCompletion("Fast response! ⚡")

    mock_tts = AsyncMock()
    mock_tts.return_value = "/audio/test.wav"

    with patch("lumina.ui.interface.gemma_client", mock_gemma):
        with patch("lumina.ui.interface.get_brain_state_params") as mock_brain:
            mock_brain.return_value = (mock_gemma, "gemma-4-31b-it", 0.7, 2048, "You are Lumina in Fast Mode")
            with patch("lumina.ui.interface.save_chat"):
                with patch("lumina.ui.interface.generate_audio", mock_tts):
                    with patch("lumina.ui.interface.clean_text_for_speech") as mock_clean:
                        mock_clean.return_value = "Fast response!"

                        from lumina.ui.interface import chat_with_lumina

                        results = []
                        async for result in chat_with_lumina(
                                "Quick question", [], None, "Fast Mode",
                                "Google Gemma 4 31B", "English", "British (UK) - Sonia (Female)",
                                internet_access=False, search_engines=[]
                        ):
                            results.append(result)

                        assert len(results) > 0
                        final = results[-1]
                        assert "Fast response" in str(final[1])


@pytest.mark.asyncio
async def test_pipeline_search_classifier_fallback_on_error():
    mock_groq = MagicMock()
    mock_groq.chat = AsyncMock()
    mock_groq.chat.completions.create = AsyncMock()
    mock_groq.chat.completions.create.return_value = MockAsyncStream(["No search needed."])

    with patch("lumina.ui.interface.groq_client", mock_groq):
        with patch("lumina.ui.interface.classify_search_need") as mock_classify:
            mock_classify.side_effect = Exception("Classifier crashed")
            with patch("lumina.ui.interface.get_brain_state_params") as mock_brain:
                mock_brain.return_value = (mock_groq, "llama-3.3-70b-versatile", 0.7, 4096, "You are Lumina")
                with patch("lumina.ui.interface.save_chat"):
                    with patch("lumina.ui.interface.generate_audio") as mock_tts:
                        mock_tts.return_value = None

                        from lumina.ui.interface import chat_with_lumina

                        results = []
                        async for result in chat_with_lumina(
                            "test", [], None, "Conscious Mode (Full Power)",
                            "Groq Llama 3.3 70B Versatile", "English", "British (UK) - Sonia (Female)",
                            internet_access=True, search_engines=["Google"]
                        ):
                            results.append(result)

                        assert len(results) > 0


@pytest.mark.asyncio
async def test_chat_with_lumina_play_voice_disabled():
    mock_groq = MagicMock()
    mock_groq.chat = AsyncMock()
    mock_groq.chat.completions.create = AsyncMock()
    mock_groq.chat.completions.create.return_value = MockAsyncStream(["I am speaking!"])

    mock_tts = AsyncMock()

    with patch("lumina.ui.interface.groq_client", mock_groq):
        with patch("lumina.ui.interface.get_brain_state_params") as mock_brain:
            mock_brain.return_value = (mock_groq, "llama-3.3-70b-versatile", 0.7, 4096, "You are Lumina")
            with patch("lumina.ui.interface.save_chat"):
                with patch("lumina.ui.interface.generate_audio", mock_tts):
                    with patch("lumina.ui.interface.clean_text_for_speech") as mock_clean:
                        mock_clean.return_value = "I am speaking!"

                        from lumina.ui.interface import chat_with_lumina

                        results = []
                        async for result in chat_with_lumina(
                            "hello", [], None, "Conscious Mode (Full Power)",
                            "Groq Llama 3.3 70B Versatile", "English", "British (UK) - Sonia (Female)",
                            internet_access=False, search_engines=[], play_voice=False
                        ):
                            results.append(result)

                        assert len(results) > 0
                        final = results[-1]
                        assert final[2] is None
                        mock_tts.assert_not_called()


@pytest.mark.asyncio
async def test_replay_voice_function():
    from lumina.ui.interface import replay_voice

    mock_tts = AsyncMock(return_value="/audio/test.wav")
    mock_clean = AsyncMock(return_value="I am here")

    with patch("lumina.ui.interface.generate_audio", mock_tts):
        with patch("lumina.ui.interface.clean_text_for_speech", mock_clean):
            # Test empty history
            res = await replay_voice([], "English", "British (UK) - Sonia (Female)")
            assert res is None

            # Test dictionary history format
            dict_history = [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "I am here"}
            ]
            res = await replay_voice(dict_history, "English", "British (UK) - Sonia (Female)")
            assert res == "/audio/test.wav"
            mock_tts.assert_called_with("I am here", "en-GB-SoniaNeural")

            mock_tts.reset_mock()

            # Test list-of-lists history format
            list_history = [
                ["hello", "I am here"]
            ]
            res = await replay_voice(list_history, "English", "British (UK) - Sonia (Female)")
            assert res == "/audio/test.wav"
            mock_tts.assert_called_with("I am here", "en-GB-SoniaNeural")


def test_extract_text_content():
    from lumina.ui.interface import extract_text_content

    # Test basic string
    assert extract_text_content("hello") == "hello"

    # Test list of strings
    assert extract_text_content(["hello", "world"]) == "hello world"

    # Test dictionary with content/text keys
    assert extract_text_content({"content": "hello content"}) == "hello content"
    assert extract_text_content({"text": "hello text"}) == "hello text"

    # Test nested lists/dicts
    assert extract_text_content([{"content": "hello"}, "world"]) == "hello world"

    # Test file/media dictionary exclusion (path/url keys with no text keys should return empty)
    media_dict = {"path": "/cache/image.png", "mime_type": "image/png"}
    assert extract_text_content(media_dict) == ""

    # Test dictionary fallback
    assert extract_text_content({"custom_key": "some random text"}) == "some random text"


@pytest.mark.asyncio
async def test_clean_text_for_speech_strips_html():
    from lumina.speech.tts import clean_text_for_speech

    input_text = "Here is the response. <audio id='aud'></audio><button onclick='play()'>🔊 Play</button>"
    cleaned = await clean_text_for_speech(input_text)
    # The clean_text_for_speech removes HTML tags and emojis, so the button emoji "🔊" is removed too
    # Let's verify that HTML tags like <audio> and <button> are gone
    assert "<audio" not in cleaned
    assert "button" not in cleaned
    assert "Play" in cleaned
    assert "Here is the response" in cleaned


@pytest.mark.asyncio
async def test_replay_voice_with_list_structure():
    from lumina.ui.interface import replay_voice

    mock_tts = AsyncMock(return_value="/audio/test.wav")
    mock_clean = AsyncMock(return_value="I am here")

    with patch("lumina.ui.interface.generate_audio", mock_tts):
        with patch("lumina.ui.interface.clean_text_for_speech", mock_clean):
            # Test a list as content in dictionary
            dict_history = [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": ["I am", "here"]}
            ]
            res = await replay_voice(dict_history, "English", "British (UK) - Sonia (Female)")
            assert res == "/audio/test.wav"
            # It should extract and join the list: "I am here"
            mock_clean.assert_called_with("I am here")

