import json
from unittest.mock import MagicMock, patch

from digest.config import Config
from digest.llm import summarize_batch

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
)

_PATCH = "digest.llm.requests.post"


def _config(**kwargs: object) -> Config:
    return Config(**{**_BASE, **kwargs})  # type: ignore[arg-type]


def _article(idx: int = 1, word_count: int = 100) -> dict[str, object]:
    return {
        "id": idx,
        "title": f"Article {idx}",
        "body": " ".join(["word"] * word_count),
        "word_count": word_count,
        "read_time": word_count // 200,
        "title_only": False,
    }


def _llm_response(summaries: list[dict[str, object]]) -> MagicMock:
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"summaries": summaries})}}]
    }
    return mock


def test_system_prompt_is_schema_then_guidelines():
    config = _config()
    article = _article()
    summary = {"id": 1, "category": "AI", "summary": "A summary.", "read_time": 0}
    captured: list[dict[str, object]] = []

    def capture_call(*args: object, **kwargs: object) -> MagicMock:
        captured.append(kwargs)  # type: ignore[arg-type]
        return _llm_response([summary])

    with patch(_PATCH, side_effect=capture_call):
        summarize_batch([article], config)

    messages = captured[0]["json"]["messages"]  # type: ignore[index]
    system_content = messages[0]["content"]
    assert "summaries" in system_content  # from schema
    assert "SUMMARY GUIDELINES" in system_content  # from system
    schema_pos = system_content.index("summaries")
    guidelines_pos = system_content.index("SUMMARY GUIDELINES")
    assert schema_pos < guidelines_pos


def test_ollama_truncates_body_at_600_words():
    config = _config(llm_provider="ollama", ollama_model="qwen2.5:14b")
    article = _article(word_count=1000)
    summary = {"id": 1, "category": "AI", "summary": "Short.", "read_time": 0}
    captured: list[dict[str, object]] = []

    def capture_call(*args: object, **kwargs: object) -> MagicMock:
        captured.append(kwargs)  # type: ignore[arg-type]
        return _llm_response([summary])

    with patch(_PATCH, side_effect=capture_call):
        summarize_batch([article], config)

    messages = captured[0]["json"]["messages"]  # type: ignore[index]
    user_content = messages[1]["content"]
    articles_sent = json.loads(user_content)
    body_words = articles_sent[0]["body"].split()
    assert len(body_words) == 600


def test_cloud_provider_truncates_body_at_1200_words():
    config = _config(llm_provider="groq")
    article = _article(word_count=2000)
    summary = {"id": 1, "category": "AI", "summary": "Long article.", "read_time": 0}
    captured: list[dict[str, object]] = []

    def capture_call(*args: object, **kwargs: object) -> MagicMock:
        captured.append(kwargs)  # type: ignore[arg-type]
        return _llm_response([summary])

    with patch(_PATCH, side_effect=capture_call):
        summarize_batch([article], config)

    messages = captured[0]["json"]["messages"]  # type: ignore[index]
    user_content = messages[1]["content"]
    articles_sent = json.loads(user_content)
    body_words = articles_sent[0]["body"].split()
    assert len(body_words) == 1200


def test_word_count_field_in_payload():
    config = _config()
    article = _article(word_count=300)
    summary = {"id": 1, "category": "AI", "summary": "Summary.", "read_time": 0}
    captured: list[dict[str, object]] = []

    def capture_call(*args: object, **kwargs: object) -> MagicMock:
        captured.append(kwargs)  # type: ignore[arg-type]
        return _llm_response([summary])

    with patch(_PATCH, side_effect=capture_call):
        summarize_batch([article], config)

    messages = captured[0]["json"]["messages"]  # type: ignore[index]
    user_content = messages[1]["content"]
    articles_sent = json.loads(user_content)
    assert "word_count" in articles_sent[0]
    assert articles_sent[0]["word_count"] == 300


def test_returns_list_of_summary_dicts():
    config = _config()
    article = _article()
    summary = {
        "id": 1,
        "category": "Technology",
        "summary": "Something interesting.",
        "read_time": 1,
    }
    with patch(_PATCH, return_value=_llm_response([summary])):
        result = summarize_batch([article], config)

    assert len(result) == 1
    assert result[0]["id"] == 1
    assert result[0]["category"] == "Technology"
    assert result[0]["summary"] == "Something interesting."
    assert result[0]["read_time"] == 1
