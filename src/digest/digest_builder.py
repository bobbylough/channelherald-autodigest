from __future__ import annotations

from digest.config import Config

_CATEGORY_ORDER = ["AI", "Business", "Technology"]


def build_html(
    summaries: list[dict[str, object]], config: Config
) -> str:
    grouped = _group_by_category(summaries)
    body_parts: list[str] = []
    for category in _CATEGORY_ORDER:
        stories = grouped.get(category, [])
        if stories:
            body_parts.append(f'<h2 style="color:#333">{category}</h2>')
            for story in stories:
                body_parts.append(_render_story(story))
    return _wrap_html("\n".join(body_parts))


def _group_by_category(
    summaries: list[dict[str, object]],
) -> dict[str, list[dict[str, object]]]:
    groups: dict[str, list[dict[str, object]]] = {}
    for summary in summaries:
        cat = str(summary.get("category", "Technology"))
        groups.setdefault(cat, []).append(summary)
    return groups


def _render_story(story: dict[str, object]) -> str:
    title = story.get("title", "")
    summary = story.get("summary", "")
    read_time = story.get("read_time", 0)
    engagers = story.get("engagers", [])
    badge = _engagers_badge(engagers) if engagers else ""
    return (
        f'<div style="margin-bottom:1.5em">'
        f'<h3 style="margin:0">{title}</h3>'
        f'<p style="margin:0.25em 0">{summary}</p>'
        f'<p style="margin:0.25em 0;color:#888;font-size:0.85em">'
        f"{read_time} min read{badge}</p>"
        f"</div>"
    )


def _engagers_badge(engagers: object) -> str:
    if not isinstance(engagers, list) or not engagers:
        return ""
    names = ", ".join(str(e) for e in engagers)
    return (
        f' &nbsp;<span style="color:#999;font-size:0.85em">For: {names}</span>'
    )


def _wrap_html(body: str) -> str:
    return (
        "<!DOCTYPE html><html><head>"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "</head><body>"
        f"{body}"
        "</body></html>"
    )
