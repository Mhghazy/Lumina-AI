import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, mock_open

from lumina.ui.interface import chat_with_lumina


class MockChunk:
    def __init__(self, content: str):
        self.choices = [MagicMock()]
        self.choices[0].delta.content = content


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


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_10_turn_conversation():
    mock_groq = MagicMock()
    mock_groq.chat = AsyncMock()
    mock_groq.chat.completions.create = AsyncMock()
    mock_groq.chat.completions.create.return_value = MockAsyncStream(["Hello!"])

    messages = [
        "Hi there",
        "What's the weather?",
        "Tell me a joke",
        "Explain Python",
        "What is AI?",
        "Write a poem",
        "How do rockets work?",
        "What is the capital of France?",
        "Tell me about history",
        "Goodbye",
    ]

    history = []
    chat_id = None

    with patch("lumina.ui.interface.groq_client", mock_groq):
        with patch("lumina.ui.interface.get_brain_state_params") as mock_brain:
            mock_brain.return_value = (mock_groq, "llama-3.3-70b-versatile", 0.7, 4096, "You are Lumina")
            with patch("lumina.ui.interface.save_chat"):
                with patch("lumina.ui.interface.generate_audio", AsyncMock(return_value=None)):
                    with patch("lumina.ui.interface.clean_text_for_speech", AsyncMock(return_value="Hello!")):
                        for msg in messages:
                            results = []
                            async for result in chat_with_lumina(
                                msg, history, chat_id,
                                "Conscious Mode (Full Power)",
                                "Groq Llama 3.3 70B Versatile",
                                False, []
                            ):
                                results.append(result)
                            assert len(results) > 0
                            history = results[-1][1]
                            chat_id = results[-1][3]
                            assert history is not None

    assert len(history) >= 2 * len(messages)


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_switch_brain_states_during_session():
    mock_groq = MagicMock()
    mock_groq.chat = AsyncMock()
    mock_groq.chat.completions.create = AsyncMock()
    mock_groq.chat.completions.create.return_value = MockAsyncStream(["OK"])

    states = [
        "Conscious Mode (Full Power)",
        "Fast Mode (Quick & Snappy)",
        "Chill Mode (No Overthinking)",
        "Analysis Mode (Rigorous Thinking)",
        "Subconscious Mode (Power Saving)",
    ]

    history = []

    with patch("lumina.ui.interface.groq_client", mock_groq):
        with patch("lumina.ui.interface.gemma_client", mock_groq):
            with patch("lumina.ui.interface.get_brain_state_params") as mock_brain:
                with patch("lumina.ui.interface.save_chat"):
                    with patch("lumina.ui.interface.generate_audio", AsyncMock(return_value=None)):
                        with patch("lumina.ui.interface.clean_text_for_speech", AsyncMock(return_value="OK")):
                            for i, state in enumerate(states):
                                model = "Groq Llama 3.3 70B Versatile" if i % 2 == 0 else "Google Gemma 4 31B"
                                if "Fast" in state or "Analysis" in state:
                                    mock_brain.return_value = (mock_groq, "gemma-4-31b-it", 0.1, 2048, f"You are Lumina in {state}")
                                else:
                                    mock_brain.return_value = (mock_groq, "llama-3.3-70b-versatile", 0.7, 4096, "You are Lumina")

                                results = []
                                async for result in chat_with_lumina(
                                    f"test message {i}", history, "session-1",
                                    state, model, False, []
                                ):
                                    results.append(result)
                                assert len(results) > 0
                                history = results[-1][1]

    assert len(history) >= 10
