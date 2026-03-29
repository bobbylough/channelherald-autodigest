from __future__ import annotations

import json

import requests

from digest.config import Config

_PROMPT = (
    "Rate this article. Respond with JSON only — no preamble, no fences.\n"
    "Required fields: dinner_score (int 1-5), novelty_score (int 1-3), "
    "engagers (list of strings from: software engineer, entrepreneur, surgeon, "
    "CEO, business analyst), rating_explanation (string, one sentence).\n\n"
    "Title: {title}\n\nBody: {body}"
)

_ENDPOINTS: dict[str, str] = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
    "ollama": "http://localhost:11434/v1/chat/completions",
    "anthropic": "https://api.groq.com/openai/v1/chat/completions",
}


def rate_article(
    article: dict[str, object], config: Config
) -> dict[str, object]:
    prompt = _PROMPT.format(title=article["title"], body=article["body"])
    raw = _call_llm(prompt, config)
    parsed = json.loads(raw)
    _validate(parsed)
    return {**article, **{
        "dinner_score": int(parsed["dinner_score"]),
        "novelty_score": parsed.get("novelty_score"),
        "engagers": parsed.get("engagers", []),
        "rating_explanation": parsed.get("rating_explanation", ""),
    }}


def _call_llm(prompt: str, config: Config) -> str:
    provider = config.rating_provider or config.llm_provider
    endpoint = _ENDPOINTS.get(provider, _ENDPOINTS["openai"])
    headers = {"Authorization": f"Bearer {config.api_key}"}
    payload = {
        "model": config.ollama_model or "llama3-8b-8192",
        "messages": [{"role": "user", "content": prompt}],
    }
    resp = requests.post(endpoint, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return str(resp.json()["choices"][0]["message"]["content"])


def _validate(parsed: dict[str, object]) -> None:
    score = parsed.get("dinner_score")
    if score is None or not isinstance(score, int):
        raise ValueError(f"Invalid or missing dinner_score: {score!r}")
