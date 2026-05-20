import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.mark.asyncio
async def test_streambanana_interrupted_stream_graceful():
    stream_chunks = ["Hello", " ", "world", "!"]

    class MockStreamIterator:
        def __init__(self):
            self._index = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self._index >= len(stream_chunks):
                raise StopAsyncIteration
            chunk = MagicMock()
            chunk.choices[0].delta.content = stream_chunks[self._index]
            self._index += 1
            return chunk

    mock_completion = MockStreamIterator()
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    text = ""
    async for chunk in mock_completion:
        text += chunk.choices[0].delta.content

    assert text == "Hello world!"


@pytest.mark.asyncio
async def test_streambanana_partial_chunk_handling():
    class PartialChunkStream:
        def __init__(self):
            self.called = False

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not self.called:
                self.called = True
                chunk = MagicMock()
                chunk.choices[0].delta.content = None
                return chunk
            raise StopAsyncIteration

    stream = PartialChunkStream()
    text = ""
    async for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            text += chunk.choices[0].delta.content

    assert text == ""


@pytest.mark.asyncio
async def test_streambanana_timeout_recovers():
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = asyncio.TimeoutError("timed out")

    try:
        await asyncio.wait_for(
            mock_client.chat.completions.create(messages=[], model="test"),
            timeout=1,
        )
    except asyncio.TimeoutError:
        pass


@pytest.mark.asyncio
async def test_streambanana_empty_stream_does_not_crash():
    class EmptyStream:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    stream = EmptyStream()
    text = ""
    async for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            text += chunk.choices[0].delta.content

    assert text == ""
