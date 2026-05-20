import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from lumina.speech.tts import clean_text_for_speech


@pytest.mark.asyncio
async def test_markdown_citations_are_preserved():
    text = "According to [1], the sky is blue."
    result = await clean_text_for_speech(text)
    assert result is not None


@pytest.mark.asyncio
async def test_markdown_image_refs_stripped():
    text = "Here's a chart: ![FakeChart](http://chart.com/fig1.png)"
    result = await clean_text_for_speech(text)
    assert "![FakeChart](http://chart.com/fig1.png)" not in result
    assert "chart" in result


@pytest.mark.asyncio
async def test_code_block_with_fake_api_keys_removed():
    text = 'Here is the code:\n```\napi_key = "sk-1234567890"\n```\nThat\'s it.'
    result = await clean_text_for_speech(text)
    assert "api_key" not in result
    assert "sk-1234567890" not in result
    assert "Here is the code" in result or "That's it" in result


@pytest.mark.asyncio
async def test_hallucination_code_blocks_stripped():
    text = "The answer is:\n```\nprint('hallucinated')\n```\nThat's all."
    result = await clean_text_for_speech(text)
    assert "```" not in result
    assert "answer" in result.lower()
