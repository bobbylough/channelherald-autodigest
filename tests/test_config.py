import pytest

from digest.config import Config

REQUIRED_PROPS = """
imap_host=imap.example.com
imap_port=993
imap_user=user@example.com
smtp_user=user@example.com
imap_pass=secret
smtp_pass=secret
smtp_host=smtp.example.com
smtp_port=587
newsletter_senders=newsletters@example.com
email_to=recipient@example.com
llm_provider=groq
api_key=test_key
preferred_domains=example.com
""".strip()


def write_config(tmp_path, content: str) -> str:
    path = tmp_path / "config.properties"
    path.write_text(content)
    return str(path)


def test_missing_imap_host_raises(tmp_path):
    props = "\n".join(
        line
        for line in REQUIRED_PROPS.splitlines()
        if not line.startswith("imap_host=")
    )
    path = write_config(tmp_path, props)
    with pytest.raises(ValueError, match="imap_host"):
        Config.from_file(path)


def test_optional_defaults(tmp_path):
    path = write_config(tmp_path, REQUIRED_PROPS)
    config = Config.from_file(path)

    assert config.email_lookback_days == 1
    assert config.max_articles_per_email == 5
    assert config.max_articles == 0
    assert config.max_digest_stories == 7
    assert config.debug is False
    assert config.preferred_senders == []
    assert config.enable_rating is False
    assert config.rating_provider == "groq"  # defaults to llm_provider
    assert config.ollama_model == ""
    assert config.min_dinner_score == 4
    assert config.min_dinner_score_preferred == 3
    assert config.enable_summary_validation is False
    assert config.summary_min_score == 2


def test_required_fields_parsed(tmp_path):
    path = write_config(tmp_path, REQUIRED_PROPS)
    config = Config.from_file(path)

    assert config.imap_host == "imap.example.com"
    assert config.imap_port == 993
    assert config.smtp_port == 587
    assert config.llm_provider == "groq"
    assert config.newsletter_senders == ["newsletters@example.com"]
    assert config.preferred_domains == ["example.com"]


def test_optional_overrides(tmp_path):
    overrides = [
        "email_lookback_days=3",
        "debug=true",
        "preferred_senders=@trusted.com",
        "summary_min_score=3",
    ]
    props = REQUIRED_PROPS + "\n" + "\n".join(overrides)
    path = write_config(tmp_path, props)
    config = Config.from_file(path)

    assert config.email_lookback_days == 3
    assert config.debug is True
    assert config.preferred_senders == ["@trusted.com"]
    assert config.summary_min_score == 3
