from unittest.mock import patch, MagicMock
from lumina.utils.network import safe_error


def test_error_log_contains_no_api_keys():
    err = safe_error(Exception("https://api.example.com?key=sk-1234567890abcdef"))
    assert "sk-1234567890abcdef" not in err
    assert "key=<redacted>" in err


def test_provider_name_in_error():
    err = safe_error(Exception("Pollinations: Connection refused"))
    assert "Pollinations" in err
    assert "Connection refused" in err


def test_structured_error_contains_subsystem():
    err = safe_error(Exception("[ImageGen] Imagen 3 failed: timeout"))
    assert "timeout" in err


def test_multiple_secrets_all_redacted():
    err = safe_error(
        Exception("?key=foo&api_key=bar&token=baz&secret=qux")
    )
    assert "key=<redacted>" in err
    assert "api_key=<redacted>" in err
    assert "foo" not in err
    assert "bar" not in err


def test_empty_error_does_not_crash():
    err = safe_error(Exception(""))
    assert isinstance(err, str)


def test_non_string_error():
    err = safe_error(Exception(42))
    assert "42" in err or isinstance(err, str)
