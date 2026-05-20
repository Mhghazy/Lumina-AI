import os
import pytest
from unittest.mock import patch, MagicMock

from lumina.image.engine import generate_image_async, edit_image_async


@pytest.mark.asyncio
async def test_generate_image_async_filepath_in_cache_dir():
    mock_providers = [MagicMock(return_value=True)]

    with patch("lumina.image.engine.PROVIDERS", mock_providers):
        with patch("lumina.image.engine.IMAGE_CACHE_DIR", "/tmp/lumina_cache"):
            with patch("os.makedirs"):
                with patch("os.path.join", return_value="/tmp/lumina_cache/img_test.png"):
                    with patch("os.path.abspath", return_value="/tmp/lumina_cache/img_test.png"):
                        with patch("asyncio.to_thread") as mock_thread:
                            mock_thread.side_effect = lambda f, *a, **kw: f()
                            result = await generate_image_async("test")
                            assert result is not None
                            assert "lumina_cache" in result


@pytest.mark.asyncio
async def test_edit_image_async_creates_file_in_cache():
    with patch("os.path.exists", return_value=True):
        mock_providers = [MagicMock(return_value=True)]

        with patch("lumina.image.engine.EDIT_PROVIDERS", mock_providers):
            with patch("lumina.image.engine.IMAGE_CACHE_DIR", "/tmp/lumina_edit"):
                with patch("os.path.join", return_value="/tmp/lumina_edit/edit_test.png"):
                    with patch("os.path.abspath", return_value="/tmp/lumina_edit/edit_test.png"):
                        with patch("asyncio.to_thread") as mock_thread:
                            mock_thread.side_effect = lambda f, *a, **kw: f()
                            result = await edit_image_async("edit", "/tmp/src.png")
                            assert result is not None


@pytest.mark.asyncio
async def test_generate_image_async_provider_exception_continues():
    results = [False, True]
    idx = [0]

    def provider_fn(*a, **kw):
        i = idx[0]
        idx[0] += 1
        if i == 0:
            raise Exception("Provider crashed")
        return results[i]

    mock_providers = [
        lambda *a, **kw: (_ for _ in ()).throw(Exception("crash")),
        MagicMock(return_value=True),
    ]

    with patch("lumina.image.engine.PROVIDERS", mock_providers):
        with patch("lumina.image.engine.IMAGE_CACHE_DIR", "/tmp/cache"):
            with patch("os.makedirs"):
                with patch("asyncio.to_thread") as mock_thread:
                    mock_thread.side_effect = lambda f, *a, **kw: f()
                    result = await generate_image_async("test")
                    assert result is not None
