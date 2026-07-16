"""Per-source filters applied at the discover stage.

A source can declare an optional `filter:` block in config.yaml:

    filter:
      author: "Michael Burch"        # case-insensitive contains match on entry author
      keyword_any: ["AI", "LLM"]     # at least one keyword must appear in title or body
      keyword_all: ["agent", "tool"] # every keyword must appear
      min_words: 300                 # drop short marketing posts
      published_after: "2026-01-01"  # ISO date — drop older items

All filters are AND-combined. Empty filter dict = pass-through.
"""

from __future__ import annotations

from datetime import datetime


def apply(items: list, filter_spec: dict | None) -> list:
    """Return only the items that pass every declared filter."""
    if not filter_spec:
        return items

    author = (filter_spec.get("author") or "").strip().lower()
    keyword_any = [k.lower() for k in (filter_spec.get("keyword_any") or [])]
    keyword_all = [k.lower() for k in (filter_spec.get("keyword_all") or [])]
    min_words = int(filter_spec.get("min_words") or 0)
    published_after = _parse_date(filter_spec.get("published_after"))

    out = []
    for item in items:
        if author and author not in (item.get("author") or "").lower():
            continue
        haystack = f"{item.get('title', '')} {item.get('summary', '')} {item.get('full_text', '')}".lower()
        if keyword_any and not any(k in haystack for k in keyword_any):
            continue
        if keyword_all and not all(k in haystack for k in keyword_all):
            continue
        if min_words:
            wc = len((item.get("full_text") or item.get("summary") or "").split())
            if wc < min_words:
                continue
        if published_after:
            item_date = _parse_date(item.get("date"))
            if item_date and item_date < published_after:
                continue
        out.append(item)
    return out


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).date()
    except Exception:
        return None
