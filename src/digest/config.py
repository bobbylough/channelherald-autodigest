from __future__ import annotations

from dataclasses import dataclass, field

_REQUIRED = [
    "imap_host",
    "imap_port",
    "imap_user",
    "smtp_user",
    "imap_pass",
    "smtp_pass",
    "smtp_host",
    "smtp_port",
    "newsletter_senders",
    "email_to",
    "llm_provider",
    "api_key",
    "preferred_domains",
]


@dataclass
class Config:
    imap_host: str
    imap_port: int
    imap_user: str
    smtp_user: str
    imap_pass: str
    smtp_pass: str
    smtp_host: str
    smtp_port: int
    newsletter_senders: list[str]
    email_to: str
    llm_provider: str
    api_key: str
    preferred_domains: list[str]
    email_lookback_days: int = 1
    max_articles_per_email: int = 5
    max_articles: int = 0
    max_digest_stories: int = 7
    debug: bool = False
    preferred_senders: list[str] = field(default_factory=list)
    enable_rating: bool = False
    rating_provider: str = ""
    ollama_model: str = ""
    min_dinner_score: int = 4
    min_dinner_score_preferred: int = 3
    enable_summary_validation: bool = False
    summary_min_score: int = 2

    @classmethod
    def from_file(cls, path: str) -> Config:
        raw = _parse_properties(path)
        _check_required(raw)
        return cls(
            imap_host=raw["imap_host"],
            imap_port=int(raw["imap_port"]),
            imap_user=raw["imap_user"],
            smtp_user=raw["smtp_user"],
            imap_pass=raw["imap_pass"],
            smtp_pass=raw["smtp_pass"],
            smtp_host=raw["smtp_host"],
            smtp_port=int(raw["smtp_port"]),
            newsletter_senders=_split_list(raw["newsletter_senders"]),
            email_to=raw["email_to"],
            llm_provider=raw["llm_provider"],
            api_key=raw["api_key"],
            preferred_domains=_split_list(raw["preferred_domains"]),
            email_lookback_days=int(raw.get("email_lookback_days", "1")),
            max_articles_per_email=int(raw.get("max_articles_per_email", "5")),
            max_articles=int(raw.get("max_articles", "0")),
            max_digest_stories=int(raw.get("max_digest_stories", "7")),
            debug=raw.get("debug", "false").lower() == "true",
            preferred_senders=_split_list(raw.get("preferred_senders", "")),
            enable_rating=raw.get("enable_rating", "false").lower() == "true",
            rating_provider=raw.get("rating_provider", raw["llm_provider"]),
            ollama_model=raw.get("ollama_model", ""),
            min_dinner_score=int(raw.get("min_dinner_score", "4")),
            min_dinner_score_preferred=int(raw.get("min_dinner_score_preferred", "3")),
            enable_summary_validation=(
                raw.get("enable_summary_validation", "false").lower() == "true"
            ),
            summary_min_score=int(raw.get("summary_min_score", "2")),
        )


def _parse_properties(path: str) -> dict[str, str]:
    raw: dict[str, str] = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            raw[key.strip()] = value.strip()
    return raw


def _check_required(raw: dict[str, str]) -> None:
    for key in _REQUIRED:
        if key not in raw:
            raise ValueError(f"Missing required config key: {key}")


def _split_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]
