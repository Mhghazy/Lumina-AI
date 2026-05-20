import random
import string
import pytest

from lumina.search.scraper import _make_soup


@pytest.mark.fuzz
class TestFuzzHtml:
    def test_random_giant_html(self):
        for _ in range(10):
            size = random.randint(10_000, 200_000)
            html = "<html><body>" + "".join(random.choices(string.ascii_letters, k=size)) + "</body></html>"
            soup = _make_soup(html)
            assert soup is not None

    def test_random_tag_nesting(self):
        tags = ["div", "span", "a", "p", "b", "i", "ul", "li", "table", "tr", "td"]
        for _ in range(30):
            depth = random.randint(1, 20)
            html = "<html><body>"
            for _ in range(depth):
                tag = random.choice(tags)
                attr = f' class="{" ".join(random.choices(["a","b","c","x","y"], k=random.randint(0,3)))}"'
                html += f"<{tag}{attr}>"
            html += "test"
            html += "</" + "></".join(reversed([random.choice(tags) for _ in range(depth)])) + ">"
            html += "</body></html>"
            soup = _make_soup(html)
            assert soup is not None

    def test_random_malformed_tags(self):
        for _ in range(50):
            html = "<html><body>"
            for _ in range(random.randint(1, 10)):
                tag = random.choice(["div", "script", "style", "a", "img"])
                variant = random.choice([
                    f"<{tag}>text</{tag}>",
                    f"<{tag}",
                    f"</{tag}>",
                    f"<{tag} attr='>'>text",
                    f"<{tag}><!-- comment --></{tag}>",
                    f"<{tag} attr=value>",
                ])
                html += variant
            html += "</body></html>"
            soup = _make_soup(html)
            assert soup is not None

    def test_random_script_content(self):
        for _ in range(30):
            js = "".join(random.choices(string.printable, k=random.randint(1, 200)))
            html = f"<html><body><script>{js}</script></body></html>"
            soup = _make_soup(html)
            assert soup is not None

    def test_zero_width_chars_in_html(self):
        zw_chars = "\u200B\u200C\u200D\uFEFF\u200E\u200F\u202A\u202B\u202C\u202D\u202E"
        for _ in range(20):
            prefix = random.choice(zw_chars) * random.randint(1, 10)
            html = f"<html><body><div>{prefix}Hello{prefix}</div></body></html>"
            soup = _make_soup(html)
            assert soup is not None
