import requests
import urllib.parse
import random
import base64
import os
import re
from bs4 import BeautifulSoup
import wikipedia
from googlesearch import search as google_search_api

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

# Rotating user agents to reduce bot detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

ONION_URL_RE = re.compile(
    r"(?:(?:https?://)?(?:[a-z2-7]{16}|[a-z2-7]{56})\.onion(?:/[^\s<>'\")\]]*)?)",
    re.IGNORECASE,
)
DEFAULT_TOR_PROXIES = (
    "socks5h://127.0.0.1:9150",
    "socks5h://127.0.0.1:9050",
)

def _get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "DNT": "1",
    }


def _make_soup(html):
    """Parse HTML with Beautiful Soup 4 using Python's bundled parser."""
    return BeautifulSoup(html or "", "html.parser")


def _fetch_soup(url, timeout=12, session=None):
    requester = session or requests
    response = requester.get(url, headers=_get_headers(), timeout=timeout)
    response.raise_for_status()
    if response.apparent_encoding:
        response.encoding = response.apparent_encoding
    return _make_soup(response.text), response


def _normalize_onion_url(raw_url):
    if not raw_url:
        return ""

    url = raw_url.strip().strip("<>()[]{}'\".,")
    if not url.lower().startswith(("http://", "https://")):
        url = f"http://{url}"

    parsed = urllib.parse.urlparse(url)
    if not parsed.hostname or not parsed.hostname.lower().endswith(".onion"):
        return ""
    return urllib.parse.urlunparse(parsed)


def _extract_onion_urls(text):
    urls = []
    seen = set()
    for match in ONION_URL_RE.finditer(text or ""):
        url = _normalize_onion_url(match.group(0))
        key = url.rstrip("/").lower()
        if url and key not in seen:
            seen.add(key)
            urls.append(url)
    return urls


def _is_onion_url(url):
    return bool(_normalize_onion_url(url))


def _tor_proxy_candidates():
    configured = os.getenv("TOR_SOCKS_PROXY") or os.getenv("TOR_PROXY")
    if configured:
        return [p.strip() for p in re.split(r"[,;]", configured) if p.strip()]
    return list(DEFAULT_TOR_PROXIES)


def _fetch_onion_soup(url, timeout=25):
    last_error = None
    for proxy in _tor_proxy_candidates():
        session = requests.Session()
        session.trust_env = False
        session.proxies = {"http": proxy, "https": proxy}
        try:
            soup, response = _fetch_soup(url, timeout=timeout, session=session)
            return soup, response, proxy
        except Exception as e:
            last_error = e

    raise last_error or RuntimeError("No Tor SOCKS proxies are configured.")


def _decode_bing_url(href):
    """Return the destination URL when Bing wraps a result in a redirect."""
    if not href:
        return ""

    parsed = urllib.parse.urlparse(href)
    query = urllib.parse.parse_qs(parsed.query)
    encoded_target = query.get("u", [""])[0]
    if encoded_target:
        # Bing commonly stores the real URL as URL-safe base64 with an "a1" prefix.
        encoded_target = encoded_target[2:] if encoded_target.startswith("a1") else encoded_target
        try:
            padded = encoded_target + ("=" * (-len(encoded_target) % 4))
            decoded = base64.urlsafe_b64decode(padded).decode("utf-8", errors="ignore")
            if decoded.startswith(("http://", "https://")):
                return decoded
        except Exception:
            pass
        if encoded_target.startswith(("http://", "https://")):
            return encoded_target

    if href.startswith("/"):
        return urllib.parse.urljoin("https://www.bing.com", href)
    return href


# ─────────────────────────────────────────────
#  SURFACE WEB ENGINES
# ─────────────────────────────────────────────

def search_google(query, num_results=6):
    try:
        results = []
        for j in google_search_api(query, num_results=num_results, advanced=True, sleep_interval=1):
            results.append({
                "title": j.title or "",
                "url": j.url or "",
                "description": j.description or "",
                "source": "Google"
            })
        return results
    except Exception as e:
        print(f"[Scraper] Google Error: {e}")
        return []


def search_bing(query, num_results=6):
    """Scrapes Bing search results using BeautifulSoup."""
    try:
        url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}&count={num_results}"
        soup, _ = _fetch_soup(url, timeout=12)

        results = []
        result_items = soup.select("li.b_algo")
        if not result_items:
            result_items = [item for item in soup.select("li") if item.select_one("h2 a")]

        for item in result_items[:num_results]:
            title_elem = item.select_one("h2 a")
            desc_elem = (
                item.select_one("div.b_caption p")
                or item.select_one(".b_algoSlug")
                or item.select_one(".b_snippet")
                or item.find("p")
            )

            title = title_elem.get_text(strip=True) if title_elem else ""
            url_raw = _decode_bing_url(title_elem.get("href", "")) if title_elem else ""
            description = desc_elem.get_text(strip=True) if desc_elem else ""

            if title and url_raw:
                results.append({
                    "title": title,
                    "url": url_raw,
                    "description": description,
                    "source": "Bing"
                })
        return results
    except Exception as e:
        print(f"[Scraper] Bing Error: {e}")
        return []


def search_duckduckgo(query, search_type="text", max_results=6):
    try:
        with DDGS() as ddgs:
            raw = []
            if search_type == "text":
                raw = list(ddgs.text(query, max_results=max_results))
            elif search_type == "images":
                raw = list(ddgs.images(query, max_results=max_results))
            elif search_type == "videos":
                raw = list(ddgs.videos(query, max_results=max_results))
            elif search_type == "news":
                raw = list(ddgs.news(query, max_results=max_results))
            for r in raw:
                r["source"] = "DuckDuckGo"
            return raw
    except Exception as e:
        print(f"[Scraper] DuckDuckGo Error: {e}")
        return []


def search_wikipedia(query):
    try:
        search_results = wikipedia.search(query, results=3)
        if not search_results:
            return []
        best_title = search_results[0]
        page = wikipedia.page(best_title, auto_suggest=False)
        summary = wikipedia.summary(best_title, sentences=5, auto_suggest=False)
        return [{
            "title": page.title,
            "url": page.url,
            "summary": summary,
            "source": "Wikipedia"
        }]
    except wikipedia.exceptions.DisambiguationError as e:
        try:
            page = wikipedia.page(e.options[0], auto_suggest=False)
            summary = wikipedia.summary(e.options[0], sentences=5, auto_suggest=False)
            return [{"title": page.title, "url": page.url, "summary": summary, "source": "Wikipedia"}]
        except Exception:
            return []
    except Exception as e:
        print(f"[Scraper] Wikipedia Error: {e}")
        return []


# ─────────────────────────────────────────────
#  DARK WEB ENGINE (via Ahmia clearweb gateway)
# ─────────────────────────────────────────────

def search_ahmia(query, max_results=10):
    """
    Scrapes Ahmia.fi — the largest clearweb gateway to Tor dark web search.
    HTML structure (verified 2025):
      Results:  ol.searchResults > li.result
      Title:    h4 a  (text)
      Link:     h4 a [href] = '/search/redirect?...&redirect_url=<onion_url>'
      Host:     cite tag
      Desc:     p tag
      Age:      span tag
    Falls back to Torch (another dark web search engine) if Ahmia fails.
    """
    results = _scrape_ahmia(query, max_results)
    if not results:
        print("[Scraper] Ahmia returned 0 results, trying Torch fallback...")
        results = _scrape_torch(query, max_results)
    return results


def _scrape_ahmia(query, max_results=10):
    try:
        url = f"https://ahmia.fi/search/?q={urllib.parse.quote(query)}"
        soup, response = _fetch_soup(url, timeout=20)

        results = []
        # Primary selector
        result_list = soup.select("ol.searchResults li.result")
        # Fallback to any li.result
        if not result_list:
            result_list = soup.find_all("li", class_="result")
        # Fallback: any article or div that looks like a search result
        if not result_list:
            result_list = soup.select("div.result, article.result")

        for item in result_list[:max_results]:
            title_anchor = item.select_one("h4 a") or item.select_one("h3 a") or item.find("a")
            title = title_anchor.get_text(strip=True) if title_anchor else "Unknown"

            raw_href = title_anchor.get("href", "") if title_anchor else ""
            if "redirect_url=" in raw_href:
                parsed_qs = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
                onion_url = parsed_qs.get("redirect_url", [raw_href])[0]
            elif raw_href.startswith("http"):
                onion_url = raw_href
            else:
                onion_url = f"https://ahmia.fi{raw_href}"

            cite_elem = item.find("cite")
            onion_host = cite_elem.get_text(strip=True) if cite_elem else ""

            # If we have an onion_host (a .onion address) prefer it over the derived URL
            if onion_host and onion_host.lower().endswith(".onion") and not onion_url.lower().endswith(".onion"):
                onion_url = f"http://{onion_host}"

            # Description — skip the age/host spans
            desc_text = ""
            for p in item.find_all("p"):
                candidate = p.get_text(strip=True)
                if candidate and candidate.lower() != "no description provided":
                    desc_text = candidate
                    break

            age_elem = item.find("span", class_=lambda c: c and "age" in c.lower()) or item.find("span")
            age = age_elem.get_text(strip=True) if age_elem else ""

            if title and title != "Unknown":
                results.append({
                    "title": title,
                    "url": onion_url,
                    "onion_host": onion_host,
                    "description": desc_text,
                    "age": age,
                    "source": "Ahmia (Dark Web)"
                })

        if not results:
            print(f"[Scraper] Ahmia: 0 parsed results (HTTP {response.status_code})")
        return results

    except requests.exceptions.Timeout:
        print("[Scraper] Ahmia timed out.")
        return []
    except Exception as e:
        print(f"[Scraper] Ahmia Error: {e}")
        return []


def _scrape_torch(query, max_results=5):
    """
    Fallback dark web search via Torch clearweb mirror at torchdarkweb.com
    (publicly accessible clearweb aggregator of Tor results).
    """
    try:
        url = f"https://www.torchdarkweb.com/search?q={urllib.parse.quote(query)}"
        soup, _ = _fetch_soup(url, timeout=15)

        results = []
        for item in soup.select("div.result, li.result, div.search-result")[:max_results]:
            title_elem = item.find(["h2", "h3", "h4", "a"])
            title = title_elem.get_text(strip=True) if title_elem else "Unknown"
            link = title_elem.get("href", "") if title_elem and title_elem.name == "a" else ""
            if not link:
                a_tag = item.find("a")
                link = a_tag.get("href", "") if a_tag else ""

            desc_elem = item.find("p")
            description = desc_elem.get_text(strip=True) if desc_elem else ""

            if title and link:
                results.append({
                    "title": title,
                    "url": link,
                    "description": description,
                    "source": "Torch (Dark Web)"
                })
        return results
    except Exception as e:
        print(f"[Scraper] Torch fallback Error: {e}")
        return []


# ─────────────────────────────────────────────
#  UTILITIES
# ─────────────────────────────────────────────

def search_onion_direct(query, max_results=5):
    """Fetch explicitly supplied .onion URLs through a local Tor SOCKS proxy."""
    onion_urls = _extract_onion_urls(query)
    if not onion_urls:
        return []

    results = []
    for onion_url in onion_urls[:max_results]:
        try:
            soup, response, proxy = _fetch_onion_soup(onion_url)
            title_elem = soup.find("title")
            title = title_elem.get_text(" ", strip=True) if title_elem else onion_url

            desc_elem = soup.find("meta", attrs={"name": "description"})
            description = desc_elem.get("content", "").strip() if desc_elem else ""
            if not description:
                paragraph = soup.find("p")
                description = paragraph.get_text(" ", strip=True) if paragraph else ""

            discovered_links = []
            seen_links = set()
            for anchor in soup.select("a[href]"):
                href = urllib.parse.urljoin(onion_url, anchor.get("href", ""))
                normalized = _normalize_onion_url(href)
                key = normalized.rstrip("/").lower()
                if normalized and key not in seen_links:
                    seen_links.add(key)
                    discovered_links.append(normalized)
                if len(discovered_links) >= 8:
                    break

            results.append({
                "title": title or onion_url,
                "url": onion_url,
                "onion_host": urllib.parse.urlparse(onion_url).hostname or "",
                "description": description[:500],
                "status": response.status_code,
                "via_proxy": proxy,
                "links": discovered_links,
                "source": "Tor Direct (.onion)"
            })
        except Exception as e:
            error_text = str(e)
            if "SOCKS" in error_text or "socks" in error_text:
                error_text = "Install requests[socks]/PySocks and run Tor Browser or Tor service."
            results.append({
                "title": "Tor direct fetch failed",
                "url": onion_url,
                "onion_host": urllib.parse.urlparse(onion_url).hostname or "",
                "description": error_text[:500],
                "source": "Tor Direct (.onion)"
            })

    return results


def _deduplicate(results):
    """Remove duplicate results based on URL similarity."""
    seen_urls = set()
    deduped = []
    for r in results:
        url = r.get("url", "").rstrip("/").lower()
        if url and url not in seen_urls:
            seen_urls.add(url)
            deduped.append(r)
        elif not url:
            deduped.append(r)
    return deduped


# ─────────────────────────────────────────────
#  CHAT FORMATTERS (direct rendering)
# ─────────────────────────────────────────────

def format_images_for_chat(results, max_show=6):
    """
    Converts image results into embedded markdown for the Gradio chatbot.
    Uses DDG's 'thumbnail' field (CDN-hosted, reliable) instead of 'image'
    (third-party host, often ERR_CONNECTION_TIMED_OUT).
    """
    if not results:
        return ""
    md = "\n\n---\n### 🖼️ Image Results\n\n"
    shown = 0
    for r in results:
        # Prefer DDG thumbnail (CDN-cached, always reachable) over raw image URL
        display_url = r.get("thumbnail") or r.get("image", "")
        source_url = r.get("url", "")
        title = r.get("title", "Image") or "Image"
        if display_url and shown < max_show:
            safe_title = title.replace("[", "").replace("]", "").replace('"', "")[:80]
            md += f"![{safe_title}]({display_url})\n"
            if source_url:
                md += f"*[🔗 {safe_title}]({source_url})*\n\n"
            shown += 1
    return md if shown > 0 else ""


def format_videos_for_chat(results, max_show=5):
    """
    Converts video results into formatted clickable markdown cards for the Gradio chatbot.
    """
    if not results:
        return ""
    md = "\n\n---\n### 🎬 Video Results\n\n"
    for r in results[:max_show]:
        title = r.get("title", "Video") or "Video"
        video_url = r.get("content", "") or r.get("url", "")
        publisher = r.get("publisher", "")
        duration = r.get("duration", "")
        description = r.get("description", "")
        if video_url:
            safe_title = title.replace("[", "").replace("]", "")
            md += f"📹 **[{safe_title}]({video_url})**"
            if publisher:
                md += f" — *{publisher}*"
            if duration:
                md += f" ⏱ {duration}"
            md += "\n"
            if description:
                md += f"> {description[:200]}\n"
            md += "\n"
    return md


# ─────────────────────────────────────────────
#  MAIN AGGREGATOR
# ─────────────────────────────────────────────

def perform_search(query, engines=None, search_type="text"):
    """
    Executes search across multiple engines, deduplicates results,
    and returns:
      - formatted_text: rich string for the LLM context
      - raw_media: raw list of image/video dicts for direct chat embedding
    Supported engines: "google", "bing", "duckduckgo", "wikipedia", "ahmia", "tor"
    """
    if engines is None:
        engines = ["google", "duckduckgo", "wikipedia"]

    aggregated_data = {}
    raw_media = []

    if "google" in engines and search_type == "text":
        aggregated_data["Google"] = search_google(query)

    if "bing" in engines and search_type == "text":
        aggregated_data["Bing"] = search_bing(query)

    if "duckduckgo" in engines:
        ddg_results = search_duckduckgo(query, search_type=search_type)
        aggregated_data["DuckDuckGo"] = ddg_results
        if search_type in ("images", "videos"):
            raw_media = ddg_results

    if "wikipedia" in engines and search_type == "text":
        aggregated_data["Wikipedia"] = search_wikipedia(query)

    if "ahmia" in engines and search_type == "text":
        aggregated_data["Ahmia (Dark Web)"] = search_ahmia(query)

    if "tor" in engines and search_type == "text":
        aggregated_data["Tor Direct (.onion)"] = search_onion_direct(query)

    # Build formatted output for the LLM context
    formatted_text = f"=== LIVE SEARCH RESULTS FOR: \"{query}\" ===\n\n"

    for engine, results in aggregated_data.items():
        formatted_text += f"── {engine} ──\n"
        if engine in ("Ahmia (Dark Web)", "Tor Direct (.onion)") and results:
            formatted_text += "\n⚠️ **IMPORTANT**: These are .onion services. Access them **only** with the Tor Browser, keep it updated, and never download files from untrusted sources.\n\n"
        if not results:
            formatted_text += "  No results found or engine unavailable.\n\n"
            continue

        unique_results = _deduplicate(results)

        for i, res in enumerate(unique_results):
            if search_type == "text":
                title = res.get("title", "Untitled")
                url = res.get("url", "")
                desc = (res.get("description") or res.get("body") or res.get("summary") or "")
                age = res.get("age", "")
                onion = res.get("onion_host", "")
                status = res.get("status", "")
                via_proxy = res.get("via_proxy", "")
                links = res.get("links", [])
                formatted_text += f"  [{i+1}] {title}\n"
                formatted_text += f"       URL: {url}\n"
                if onion:
                    formatted_text += f"       Onion Host: {onion}\n"
                if status:
                    formatted_text += f"       HTTP Status: {status}\n"
                if via_proxy:
                    formatted_text += f"       Tor Proxy: {via_proxy}\n"
                if age:
                    formatted_text += f"       Last seen: {age} ago\n"
                if desc:
                    formatted_text += f"       Snippet: {desc[:300]}\n"
                if links:
                    formatted_text += "       Onion Links Found:\n"
                    for link in links[:8]:
                        formatted_text += f"         - {link}\n"
                formatted_text += "\n"

            elif search_type == "images":
                title = res.get("title", "Image")
                image_url = res.get("thumbnail") or res.get("image", "")
                source_url = res.get("url", "")
                formatted_text += f"  [{i+1}] {title}\n"
                formatted_text += f"       Thumbnail: {image_url}\n"
                formatted_text += f"       Source: {source_url}\n\n"

            elif search_type == "videos":
                title = res.get("title", "Video")
                video_url = res.get("content", "") or res.get("url", "")
                publisher = res.get("publisher", "")
                formatted_text += f"  [{i+1}] {title}\n"
                formatted_text += f"       Link: {video_url}\n"
                if publisher:
                    formatted_text += f"       Publisher: {publisher}\n"
                formatted_text += "\n"

            elif search_type == "news":
                title = res.get("title", "Article")
                url = res.get("url", "")
                body = res.get("body", "")
                date = res.get("date", "")
                source = res.get("source_name", "")
                formatted_text += f"  [{i+1}] {title}\n"
                if date:
                    formatted_text += f"       Date: {date}\n"
                if source:
                    formatted_text += f"       Source: {source}\n"
                formatted_text += f"       URL: {url}\n"
                if body:
                    formatted_text += f"       Snippet: {body[:300]}\n"
                formatted_text += "\n"

        formatted_text += "\n"

    return formatted_text, raw_media
