import pytest
from unittest.mock import patch, MagicMock

from lumina.utils.network import safe_error, get_headers, make_session, save_image_bytes, download_url


class TestSafeError:
    def test_redacts_key_param(self):
        result = safe_error(Exception("error at ?key=secret123"))
        assert "<redacted>" in result
        assert "secret123" not in result

    def test_redacts_api_key_param(self):
        result = safe_error(Exception("error at &api_key=abc123"))
        assert "<redacted>" in result
        assert "abc123" not in result

    def test_no_secrets_unchanged(self):
        msg = "connection refused"
        result = safe_error(Exception(msg))
        assert msg in result

    def test_partial_redact(self):
        result = safe_error(Exception("?key=foo&value=bar"))
        assert "key=<redacted>" in result
        assert "value=bar" in result

    def test_redacts_multiple_keys(self):
        result = safe_error(Exception("?key=a&key=b&key=c"))
        assert result.count("<redacted>") == 3

    def test_empty_exception(self):
        result = safe_error(Exception(""))
        assert result is not None


class TestGetHeaders:
    def test_returns_dict_with_expected_keys(self):
        headers = get_headers()
        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Accept-Language" in headers

    def test_random_ua(self):
        with patch("random.choice", return_value="test-ua"):
            headers = get_headers()
            assert headers["User-Agent"] == "test-ua"


class TestMakeSession:
    def test_returns_session_with_verify_false(self):
        session = make_session()
        assert session.verify is False

    def test_has_user_agent_header(self):
        with patch("random.choice", return_value="test-ua"):
            session = make_session()
            assert "User-Agent" in session.headers
            assert session.headers["User-Agent"] == "test-ua"


class TestSaveImageBytes:
    def test_valid_image_bytes(self):
        from PIL import Image
        from io import BytesIO

        img = Image.new("RGB", (10, 10))
        buf = BytesIO()
        img.save(buf, format="PNG")
        data = buf.getvalue()

        with patch("builtins.open", MagicMock()):
            result = save_image_bytes(data, "/tmp/test.png")
            assert result is True

    def test_invalid_image_bytes(self):
        result = save_image_bytes(b"not an image", "/tmp/test.png")
        assert result is False


class TestDownloadUrl:
    def test_retries_on_failure(self):
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "image/png"}

        class FailingThenPassing:
            def __init__(self):
                self.attempts = 0

            def get(self, *args, **kwargs):
                self.attempts += 1
                if self.attempts < 2:
                    raise Exception("Timeout")
                return mock_response

        mock_session_instance = FailingThenPassing()
        mock_session.get.side_effect = mock_session_instance.get

        with patch("lumina.utils.network.make_session", return_value=mock_session_instance):
            with patch("time.sleep"):
                with patch("lumina.utils.network.save_image_bytes", return_value=True):
                    result = download_url("http://example.com/img.png", "/tmp/test.png")
                    assert result is True

    def test_all_retries_fail(self):
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Always fails")

        with patch("lumina.utils.network.make_session", return_value=mock_session):
            with patch("time.sleep"):
                result = download_url("http://example.com/img.png", "/tmp/test.png")
                assert result is False

    def test_non_image_content_type(self):
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_session.get.return_value = mock_response

        with patch("lumina.utils.network.make_session", return_value=mock_session):
            result = download_url("http://example.com/page", "/tmp/test.png")
            assert result is False
