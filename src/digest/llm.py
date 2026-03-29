from __future__ import annotations

import json
from pathlib import Path

import requests

from digest.config import Config

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_MAX_WORDS_LOCAL = 600
_MAX_WORDS_CLOUD = 1200

_ENDPOINTS: dict[str, str] = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
    "ollama": "http://localhost:11434/v1/chat/completions",
}


def summarize_batch(
    articles: list[dict[str, object]], config: Config
) -> list[dict[str, object]]:
    system_prompt = _load_system_prompt()
    is_local = config.llm_provider == "ollama"
    max_words = _MAX_WORDS_LOCAL if is_local else _MAX_WORDS_CLOUD
    payload = [_prepare_article(a, max_words) for a in articles]
    raw = _call_llm(system_prompt, json.dumps(payload), config)
    return list(json.loads(raw)["summaries"])


def _load_system_prompt() -> str:
    schema = (_PROMPTS_DIR / "summary_schema.txt").read_text()
    guidelines = (_PROMPTS_DIR / "summary_system.txt").read_text()
    return schema + "\n\n" + guidelines


def _prepare_article(
    article: dict[str, object], max_words: int
) -> dict[str, object]:
    body = str(article.get("body", ""))
    truncated = " ".join(body.split()[:max_words])
    return {
        "id": article["id"],
        "title": article["title"],
        "body": truncated,
        "word_count": article["word_count"],
        "read_time": article["read_time"],
        "title_only": article.get("title_only", False),
    }


def validate_summary(
    summary: dict[str, object], config: Config
) -> dict[str, object]:
    prompt = (
        "Would you forward this summary to a smart friend? "
        "Reply with a single integer only: 1=no, 2=maybe, 3=yes.\n\n"
        f"Summary: {summary['summary']}"
    )
    raw = _call_llm("", prompt, config)
    score = int(raw.strip())
    if score < config.summary_min_score:
        short_take = f"**Short take:** {summary['title']} — {summary['summary']}"
        return {**summary, "summary": short_take}
    return summary


def _call_llm(system: str, user: str, config: Config) -> str:
    endpoint = _ENDPOINTS.get(config.llm_provider, _ENDPOINTS["groq"])
    headers = {"Authorization": f"Bearer {config.api_key}"}
    model = config.ollama_model or "llama3-8b-8192"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    resp = requests.post(endpoint, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    return str(resp.json()["choices"][0]["message"]["content"])
