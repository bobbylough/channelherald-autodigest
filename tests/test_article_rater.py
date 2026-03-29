import json
from unittest.mock import MagicMock, patch

import pytest

from digest.article_rater import rate_article
from digest.config import Config

_BASE = dict(
    imap_host="imap.example.com",
    imap_port=993,
    imap_user="user@example.com",
    smtp_user="user@example.com",
    imap_pass="secret",
    smtp_pass="secret",
    smtp_host="smtp.example.com",
    smtp_port=587,
    email_to="recipient@example.com",
    llm_provider="groq",
    api_key="test_key",
    newsletter_senders=["@example.com"],
    preferred_domains=["example.com"],
    rating_provider="groq",
    enable_rating=True,
)

_PATCH = "digest.article_rater.requests.post"


def _config(**kwargs: object) -> Config:
    return Config(**{**_BASE, **kwargs})  # type: ignore[arg-type]


def _article() -> dict[str, object]:
    return {
        "url": "https://example.com/article",
        "title": "Test Article Title",
        "body": "This is the article body with enough content to rate.",
        "word_count": 10,
        "read_time": 1,
        "content_depth": 1,
        "title_only": False,
    }


def _llm_response(payload: dict[str, object]) -> MagicMock:
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = {
        "choices": [{"message": {"content": json.dumps(payload)}}]
    }
    return mock


def test_valid_response_parsed_into_four_fields():
    config = _config()
    rating = {
        "dinner_score": 4,
        "novelty_score": 2,
        "engagers": ["software engineer", "entrepreneur"],
        "rating_explanation": "Covers a real deployment case.",
    }
    with patch(_PATCH, return_value=_llm_response(rating)):
        result = rate_article(_article(), config)

    assert result["dinner_score"] == 4
    assert result["novelty_score"] == 2
    assert result["engagers"] == ["software engineer", "entrepreneur"]
    assert result["rating_explanation"] == "Covers a real deployment case."


def test_original_article_fields_preserved():
    config = _config()
    rating = {
        "dinner_score": 3,
        "novelty_score": 1,
        "engagers": ["CEO"],
        "rating_explanation": "Mildly interesting.",
    }
    with patch(_PATCH, return_value=_llm_response(rating)):
        result = rate_article(_article(), config)

    assert result["url"] == "https://example.com/article"
    assert result["title"] == "Test Article Title"


def test_missing_dinner_score_raises_value_error():
    config = _config()
    bad_rating = {
        "novelty_score": 2,
        "engagers": [],
        "rating_explanation": "No dinner score here.",
    }
    with patch(_PATCH, return_value=_llm_response(bad_rating)):
        with pytest.raises(ValueError, match="dinner_score"):
            rate_article(_article(), config)


def test_invalid_dinner_score_type_raises_value_error():
    config = _config()
    bad_rating = {
        "dinner_score": "high",
        "novelty_score": 2,
        "engagers": [],
        "rating_explanation": "Bad type.",
    }
    with patch(_PATCH, return_value=_llm_response(bad_rating)):
        with pytest.raises(ValueError, match="dinner_score"):
            rate_article(_article(), config)
