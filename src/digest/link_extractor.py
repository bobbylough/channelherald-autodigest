from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from bs4 import BeautifulSoup, Tag

from digest.config import Config


def extract_links(
    email_dict: dict[str, object], config: Config
) -> list[str]:
    body = str(email_dict.get("body", ""))
    is_preferred = bool(email_dict.get("is_preferred", False))
    cap = config.max_articles_per_email * (2 if is_preferred else 1)
    soup = BeautifulSoup(body, "html.parser")
    candidates: list[tuple[float, str]] = []
    for idx, tag in enumerate(soup.find_all("a", href=True)):
        href = str(tag["href"])
        if urlparse(href).scheme not in ("http", "https"):
            continue
        score = _score(idx, tag, href, config.preferred_domains)
        candidates.append((score, _strip_utm(href)))
    candidates.sort(key=lambda x: x[0], reverse=True)
    return [url for _, url in candidates[:cap]]


def _score(
    idx: int, tag: Tag, url: str, preferred_domains: list[str]
) -> float:
    score = max(0.0, 1.0 - (idx / 50))
    score += min(len(tag.get_text(strip=True)) / 80, 1.0)
    domain = (urlparse(url).netloc or "").lower().removeprefix("www.")
    if any(domain == d or domain.endswith("." + d) for d in preferred_domains):
        score += 1.5
    return score


def _strip_utm(url: str) -> str:
    parsed = urlparse(url)
    kept = {k: v for k, v in parse_qs(parsed.query).items()
            if not k.startswith("utm_")}
    clean = urlencode({k: v[0] for k, v in kept.items()})
    return urlunparse(parsed._replace(query=clean))
