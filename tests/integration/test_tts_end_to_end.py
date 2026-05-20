import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from lumina.speech.tts import clean_text_for_speech, generate_audio


@pytest.mark.asyncio
async def test_generate_audio_returns_path():
    mock_comms = AsyncMock()
    mock_comms.save = AsyncMock(return_value=None)

    with patch("lumina.speech.tts.edge_tts.Communicate", return_value=mock_comms):
        with patch("lumina.speech.tts.os.makedirs"):
            with patch("lumina.speech.tts.os.path.join", return_value="/tmp/audio_cache/test.mp3"):
                result = await generate_audio("Hello world")
                assert result is not None
                assert isinstance(result, str)


@pytest.mark.asyncio
async def test_generate_audio_empty_text():
    mock_comms = AsyncMock()
    mock_comms.save = AsyncMock(return_value=None)

    with patch("lumina.speech.tts.edge_tts.Communicate", return_value=mock_comms):
        with patch("lumina.speech.tts.os.makedirs"):
            with patch("lumina.speech.tts.os.path.join", return_value="/tmp/audio_cache/test.mp3"):
                result = await generate_audio("")
                assert result is not None
                assert isinstance(result, str)


@pytest.mark.asyncio
async def test_generate_audio_timeout():
    mock_comms = AsyncMock()
    mock_comms.save = AsyncMock(side_effect=Exception("TTS timeout"))

    with patch("lumina.speech.tts.edge_tts.Communicate", return_value=mock_comms):
        with patch("lumina.speech.tts.os.makedirs"):
            with patch("lumina.speech.tts.os.path.join", return_value="/tmp/audio_cache/test.mp3"):
                try:
                    result = await generate_audio("This will time out")
                    assert result is None
                except Exception as e:
                    assert "TTS timeout" in str(e)


@pytest.mark.asyncio
async def test_clean_text_for_speech_long_input():
    long_text = "Hello world! " * 200
    result = await clean_text_for_speech(long_text)
    assert result is not None
    assert len(result) > 0
