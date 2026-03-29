from unittest.mock import MagicMock, patch

import requests

from digest.scraper import scrape_article

_URL = "https://example.com/article"


def _mock_get(html: str, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.text = html
    if status_code >= 400:
        mock.raise_for_status.side_effect = requests.HTTPError(
            response=MagicMock(status_code=status_code)
        )
    else:
        mock.raise_for_status.return_value = None
    return mock


def _html(body_text: str, title: str = "Test Title") -> str:
    return (
        f"<html><head><title>{title}</title></head>"
        f"<body><p>{body_text}</p></body></html>"
    )


def test_word_count_read_time_content_depth():
    words = " ".join(["word"] * 200)
    with patch("digest.scraper.requests.get", return_value=_mock_get(_html(words))):
        result = scrape_article(_URL)

    assert result["word_count"] == 200
    assert result["read_time"] == 1
    assert result["content_depth"] == 2
    assert result["title_only"] is False


def test_403_response_sets_title_only_and_zero_word_count():
    with patch(
        "digest.scraper.requests.get",
        return_value=_mock_get("", status_code=403),
    ):
        result = scrape_article(_URL)

    assert result["title_only"] is True
    assert result["word_count"] == 0
    assert result["url"] == _URL


def test_empty_body_sets_title_only():
    with patch(
        "digest.scraper.requests.get",
        return_value=_mock_get(_html("")),
    ):
        result = scrape_article(_URL)

    assert result["title_only"] is True
    assert result["word_count"] == 0


def test_below_50_words_sets_title_only():
    words = " ".join(["word"] * 30)
    with patch("digest.scraper.requests.get", return_value=_mock_get(_html(words))):
        result = scrape_article(_URL)

    assert result["title_only"] is True
    assert result["word_count"] == 30


def test_title_extracted():
    words = " ".join(["word"] * 100)
    with patch(
        "digest.scraper.requests.get",
        return_value=_mock_get(_html(words, title="My Great Article")),
    ):
        result = scrape_article(_URL)

    assert result["title"] == "My Great Article"


def test_content_depth_capped_at_5():
    words = " ".join(["word"] * 600)
    with patch("digest.scraper.requests.get", return_value=_mock_get(_html(words))):
        result = scrape_article(_URL)

    assert result["content_depth"] == 5
