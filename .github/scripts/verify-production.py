from __future__ import annotations

import re
import sys
import time
from html import unescape
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.request import Request, urlopen

BASE_URL = "https://shabilev.github.io/"
USER_AGENT = "ShabiLev-Portfolio-Production-Smoke/1.1"

PAGES = {
    BASE_URL: ("en", "ltr", "Quality & Release Engineering Leader"),
    urljoin(BASE_URL, "he/"): ("he", "rtl", "שבי לבנדה"),
    urljoin(BASE_URL, "projects/cwl-office/"): ("en", "ltr", "Confidentiality boundary"),
    urljoin(BASE_URL, "he/projects/cwl-office/"): ("he", "rtl", "CWL Office"),
}

BLOCKED_TEXT = (
    "you@example.com",
    "+972-52-000-0000",
    "G-XXXXXXX",
    "mongodb+srv",
    "ShabiLevanda-Cello",
)


class ResourceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []
        self.resources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        href = values.get("href")
        src = values.get("src")
        if tag == "a" and href:
            self.hrefs.append(href)
        if tag in {"link", "a"} and href:
            self.resources.append(href)
        if tag in {"script", "img"} and src:
            self.resources.append(src)


def fetch(url: str, *, attempts: int = 4, allow_redirects: bool = True) -> tuple[bytes, str, int]:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT, "Cache-Control": "no-cache"})
            with urlopen(request, timeout=25) as response:
                status = response.status
                body = response.read()
                content_type = response.headers.get("content-type", "")
                final_url = response.geturl()
                if not allow_redirects and final_url != url:
                    raise AssertionError(f"Unexpected redirect: {url} -> {final_url}")
                if status != 200:
                    raise AssertionError(f"Expected HTTP 200 for {url}, got {status}")
                return body, content_type, status
        except (HTTPError, URLError, TimeoutError, AssertionError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(4)
    raise AssertionError(f"Failed to fetch {url}: {last_error}")


def assert_html_contract(url: str, html: str, lang: str, direction: str, marker: str) -> ResourceParser:
    html_tag = re.search(r"<html\b[^>]*>", html, flags=re.IGNORECASE)
    assert html_tag, f"Missing html element in {url}"
    tag = html_tag.group(0)
    assert re.search(rf'\blang=["\']{re.escape(lang)}["\']', tag, flags=re.IGNORECASE), f"Wrong lang in {url}"
    assert re.search(rf'\bdir=["\']{re.escape(direction)}["\']', tag, flags=re.IGNORECASE), f"Wrong dir in {url}"
    rendered_source = unescape(html)
    assert marker in rendered_source, f"Missing expected marker in {url}: {marker}"
    for blocked in BLOCKED_TEXT:
        assert blocked not in rendered_source, f"Blocked public text found in {url}: {blocked}"

    parser = ResourceParser()
    parser.feed(html)
    assert parser.hrefs, f"No links found in {url}"
    for href in parser.hrefs:
        assert href != "#", f"Placeholder href found in {url}"
        assert not href.lower().startswith("javascript:"), f"javascript: href found in {url}"
    return parser


def wait_for_html_contract(
    url: str,
    lang: str,
    direction: str,
    marker: str,
    *,
    attempts: int = 15,
    delay_seconds: int = 4,
) -> ResourceParser:
    """Wait until the live GitHub Pages response satisfies the current release contract."""

    last_error: AssertionError | None = None
    for attempt in range(1, attempts + 1):
        try:
            body, content_type, _ = fetch(url, attempts=1)
            assert "text/html" in content_type.lower(), f"Unexpected content type for {url}: {content_type}"
            html = body.decode("utf-8")
            parser = assert_html_contract(url, html, lang, direction, marker)
            if attempt > 1:
                print(f"Pages propagation observed after attempt {attempt}: {url}")
            return parser
        except AssertionError as exc:
            last_error = exc
            if attempt < attempts:
                print(f"WAIT Pages propagation ({attempt}/{attempts}): {url} — {exc}")
                time.sleep(delay_seconds)

    raise AssertionError(f"Live content contract did not converge for {url}: {last_error}")


def main() -> int:
    internal_urls: set[str] = set()
    github_urls: set[str] = set()
    mailto_links: set[str] = set()
    other_external: set[str] = set()

    for page_url, (lang, direction, marker) in PAGES.items():
        parser = wait_for_html_contract(page_url, lang, direction, marker)
        print(f"PASS page: {page_url} lang={lang} dir={direction}")

        for raw in set(parser.hrefs + parser.resources):
            if raw.startswith("mailto:"):
                mailto_links.add(raw)
                continue
            if raw.startswith("tel:"):
                continue
            absolute = urldefrag(urljoin(page_url, raw)).url
            parsed = urlparse(absolute)
            if parsed.scheme not in {"http", "https"}:
                continue
            if parsed.hostname == "shabilev.github.io":
                internal_urls.add(absolute)
            elif parsed.hostname in {"github.com", "www.github.com"}:
                github_urls.add(absolute)
            else:
                other_external.add(absolute)

    assert mailto_links, "Expected at least one mailto contact link"
    for link in mailto_links:
        address = link.removeprefix("mailto:").split("?", 1)[0]
        assert "@" in address and "example.com" not in address, f"Invalid mailto link: {link}"
    print(f"PASS mailto links: {len(mailto_links)}")

    for url in sorted(internal_urls):
        body, content_type, _ = fetch(url)
        if url.endswith("Shabi-Levanda-CV-EN.pdf"):
            assert body.startswith(b"%PDF"), "CV does not have a PDF signature"
            assert len(body) > 50_000, f"CV is unexpectedly small: {len(body)} bytes"
            assert "application/pdf" in content_type.lower(), f"Unexpected CV content type: {content_type}"
            print(f"PASS CV: {url} bytes={len(body)}")
        else:
            assert len(body) > 0, f"Empty internal resource: {url}"
    print(f"PASS internal live links/resources: {len(internal_urls)}")

    for url in sorted(github_urls):
        body, _, _ = fetch(url, attempts=3)
        assert len(body) > 0, f"Empty GitHub response: {url}"
    print(f"PASS public GitHub links: {len(github_urls)}")

    # Platforms such as LinkedIn may actively block CI bots. Validate these links
    # structurally rather than creating a false-negative release gate.
    for url in sorted(other_external):
        parsed = urlparse(url)
        assert parsed.scheme == "https", f"External link must use HTTPS: {url}"
        assert parsed.hostname, f"External link lacks hostname: {url}"
        assert "example.com" not in parsed.hostname, f"Placeholder external link: {url}"
    print(f"PASS structurally validated external links: {len(other_external)}")

    cv_url = urljoin(BASE_URL, "assets/cv/Shabi-Levanda-CV-EN.pdf")
    assert cv_url in internal_urls, "CV link was not discovered from the live pages"

    print("PRODUCTION SMOKE: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"PRODUCTION SMOKE: FAIL — {exc}", file=sys.stderr)
        raise SystemExit(1)
