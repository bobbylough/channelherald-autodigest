from __future__ import annotations

import requests
from bs4 import BeautifulSoup, Tag


def scrape_article(url: str) -> dict[str, object]:
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception:
        return _empty_result(url)
    title_elem = soup.find("title")
    title = title_elem.get_text(strip=True) if isinstance(title_elem, Tag) else ""
    body = " ".join(p.get_text(strip=True) for p in soup.find_all("p"))
    word_count = len(body.split()) if body.strip() else 0
    return {
        "url": url,
        "title": title,
        "body": body,
        "word_count": word_count,
        "read_time": word_count // 200,
        "content_depth": min(word_count // 100, 5),
        "title_only": not body.strip() or word_count < 50,
    }


def _empty_result(url: str) -> dict[str, object]:
    return {
        "url": url,
        "title": "",
        "body": "",
        "word_count": 0,
        "read_time": 0,
        "content_depth": 0,
        "title_only": True,
    }
