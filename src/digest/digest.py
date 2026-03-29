from __future__ import annotations

from digest.article_rater import rate_article
from digest.config import Config
from digest.imap_fetch import fetch_emails
from digest.link_extractor import extract_links
from digest.llm import summarize_batch, validate_summary
from digest.scraper import scrape_article
from digest.seen_urls import SeenUrls


def run_pipeline(config: Config) -> list[dict[str, object]]:
    emails = fetch_emails(config)
    articles = _collect_articles(emails, config)
    if config.enable_rating:
        articles = _rate_and_filter(articles, config)
    articles = _sort_and_dedup(articles)
    summaries = summarize_batch(articles, config)
    if config.enable_summary_validation:
        summaries = [validate_summary(s, config) for s in summaries]
    return summaries


def _collect_articles(
    emails: list[dict[str, object]], config: Config
) -> list[dict[str, object]]:
    seen = SeenUrls("seen_urls.db")
    articles: list[dict[str, object]] = []
    for email in emails:
        for url in extract_links(email, config):
            if seen.contains(url):
                continue
            article = dict(scrape_article(url))
            seen.add(url)
            article["is_preferred"] = email.get("is_preferred", False)
            articles.append(article)
    return articles


def _rate_and_filter(
    articles: list[dict[str, object]], config: Config
) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for article in articles:
        is_preferred = bool(article.get("is_preferred"))
        rated = dict(rate_article(article, config))
        threshold = (
            config.min_dinner_score_preferred
            if is_preferred
            else config.min_dinner_score
        )
        if _int_field(rated, "dinner_score") >= threshold:
            result.append(rated)
    return result


def _sort_and_dedup(
    articles: list[dict[str, object]],
) -> list[dict[str, object]]:
    articles = sorted(
        articles,
        key=lambda a: (-_int_field(a, "dinner_score"), -_int_field(a, "content_depth")),
    )
    return _jaccard_dedup(articles)


def _jaccard_dedup(
    articles: list[dict[str, object]],
) -> list[dict[str, object]]:
    kept: list[dict[str, object]] = []
    for article in articles:
        tokens = set(str(article.get("title", "")).lower().split())
        duplicate = any(
            _jaccard(tokens, set(str(k.get("title", "")).lower().split())) > 0.5
            for k in kept
        )
        if not duplicate:
            kept.append(article)
    return kept


def _int_field(d: dict[str, object], key: str) -> int:
    val = d.get(key)
    return val if isinstance(val, int) else 0


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)
