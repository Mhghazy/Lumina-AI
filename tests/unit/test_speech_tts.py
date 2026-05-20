import pytest
from lumina.speech.tts import clean_text_for_speech


class TestCleanTextForSpeech:
    @pytest.mark.asyncio
    async def test_removes_image_prompt_tags(self):
        result = await clean_text_for_speech("Here is your image: [IMAGE_PROMPT:a cat].")
        assert "[IMAGE_PROMPT:" not in result
        assert "image you requested" in result

    @pytest.mark.asyncio
    async def test_removes_markdown_images(self):
        result = await clean_text_for_speech("See ![alt](url.png) here")
        assert "![alt](url.png)" not in result

    @pytest.mark.asyncio
    async def test_removes_code_blocks(self):
        result = await clean_text_for_speech("Code: ```block``` done")
        assert "```" not in result

    @pytest.mark.asyncio
    async def test_removes_inline_code(self):
        result = await clean_text_for_speech("Use `var` here")
        assert "`var`" not in result

    @pytest.mark.asyncio
    async def test_removes_bold_italic(self):
        result = await clean_text_for_speech("**bold** and *italic*")
        assert "**" not in result
        assert "*" not in result or result == "bold and italic"

    @pytest.mark.asyncio
    async def test_removes_headers(self):
        result = await clean_text_for_speech("# Title\n## Sub\n### Deep")
        assert "#" not in result

    @pytest.mark.asyncio
    async def test_removes_supplementary_emoji(self):
        result = await clean_text_for_speech("Hello 😀🌍")
        assert "😀" not in result

    @pytest.mark.asyncio
    async def test_removes_bmp_symbols(self):
        result = await clean_text_for_speech("Symbols ★☎✓")
        assert "★" not in result

    @pytest.mark.asyncio
    async def test_empty_string(self):
        result = await clean_text_for_speech("")
        assert result == ""

    @pytest.mark.asyncio
    async def test_no_markdown(self):
        text = "Hello world, this is plain text."
        result = await clean_text_for_speech(text)
        assert result == text

    @pytest.mark.asyncio
    async def test_mixed_content(self):
        text = "**Hello** `world` ![img](u.png) 😀"
        result = await clean_text_for_speech(text)
        assert "**" not in result
        assert "`" not in result
        assert "![img](u.png)" not in result

    @pytest.mark.asyncio
    async def test_only_emoji(self):
        result = await clean_text_for_speech("😀🌍★☎")
        assert result.strip() == ""

    @pytest.mark.asyncio
    async def test_image_prompt_replaced_naturally(self):
        result = await clean_text_for_speech("[IMAGE_PROMPT:a beautiful sunset]")
        assert "Here is the image you requested" in result

    @pytest.mark.asyncio
    async def test_multi_line_code_block(self):
        text = "Here:\n```python\nprint(1)\n```\nDone"
        result = await clean_text_for_speech(text)
        assert "```" not in result
        assert "I have provided the code" in result
