import random
import string
import pytest

from lumina.utils.network import safe_error


@pytest.mark.fuzz
class TestFuzzSafeError:
    def test_random_strings_in_errors(self):
        for _ in range(100):
            length = random.randint(0, 200)
            text = "".join(random.choices(string.printable, k=length))
            result = safe_error(Exception(text))
            assert isinstance(result, str)
            assert len(result) > 0 or text == ""

    def test_random_unicode_in_errors(self):
        for _ in range(50):
            chars = []
            for _ in range(random.randint(1, 50)):
                cp = random.randint(0x20, 0x1_0000)
                chars.append(chr(cp))
            text = "".join(chars)
            try:
                result = safe_error(Exception(text))
                assert isinstance(result, str)
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass

    def test_random_secret_patterns(self):
        patterns = [
            f"?key={''.join(random.choices(string.ascii_letters, k=10))}",
            f"&api_key={''.join(random.choices(string.hexdigits, k=20))}",
            f"?token={''.join(random.choices(string.ascii_letters + string.digits, k=16))}",
        ]
        for pattern in patterns:
            result = safe_error(Exception(pattern))
            assert isinstance(result, str)

    def test_nested_exceptions(self):
        for _ in range(20):
            inner = Exception("".join(random.choices(string.printable, k=20)))
            outer = Exception("wrapper", inner)
            result = safe_error(outer)
            assert isinstance(result, str)

    def test_exception_with_different_args(self):
        for _ in range(30):
            args = tuple(random.choices(string.printable, k=random.randint(0, 5)))
            exc = Exception(*args)
            result = safe_error(exc)
            assert isinstance(result, str)
