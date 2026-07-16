"""Source-quality gates.

If you have Pebble's `research-verification` skill installed locally, you can
swap `judge_with_llm` for a call into that skill — both share the same
{accept, score, reason} contract. The skill will get richer signal (cross-
check against authoritative sources, author reputation, retraction history).
Without it, the LLM judge below is the baseline gate.

Three layers, each independent:

  1. Deterministic gate (`check_deterministic`) — recency, cadence, depth.
     Runs at pipeline startup on every active source. Fast, free, catches
     dead feeds and frothy content farms.

  2. LLM judge (`judge_with_llm`) — "does this source teach mechanics, or
     just aggregate headlines?" Returns {accept, score, reason}. Runs once
     per source when it's first added (during the skill interview, or when
     Exa-discovered sources are promoted). Cost: a few cents per source,
     once.

  3. Per-claim grounding gate — lives in verify.py, runs every episode.

A source that fails (1) is flagged but still pollable next run — it might
have published since. A source that fails (2) is hard-rejected from
config.yaml — the skill won't write it.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta

import feedparser

from .llm import complete, LLMError


# ── Deterministic gate ──────────────────────────────────────────────────

def check_deterministic(source: dict, *, min_post_count: int = 3,
                        max_days_since_last: int = 90,
                        min_avg_words: int = 250) -> dict:
    """Return {ok, reasons[], stats} for one source by sniffing its RSS.

    `reasons` is empty when ok=True.
    """
    url = source.get("url", "")
    if not url:
        return {"ok": False, "reasons": ["no url"], "stats": {}}

    try:
        feed = feedparser.parse(url)
    except Exception as e:
        return {"ok": False, "reasons": [f"feed unparseable: {e}"], "stats": {}}

    if getattr(feed, "bozo", False) and not feed.entries:
        return {"ok": False, "reasons": ["feed unreadable"], "stats": {}}

    entries = feed.entries or []
    if len(entries) < min_post_count:
        return {
            "ok": False,
            "reasons": [f"only {len(entries)} item(s) in feed (need {min_post_count})"],
            "stats": {"entry_count": len(entries)},
        }

    last_dates = []
    word_counts = []
    for e in entries[:10]:
        t = getattr(e, "published_parsed", None) or getattr(e, "updated_parsed", None)
        if t:
            try:
                last_dates.append(datetime(*t[:6], tzinfo=timezone.utc))
            except Exception:
                pass
        body = (getattr(e, "summary", "") or getattr(e, "description", "") or "")
        word_counts.append(len(body.split()))

    last_seen = max(last_dates) if last_dates else None
    days_since = (datetime.now(timezone.utc) - last_seen).days if last_seen else None
    avg_words = sum(word_counts) / len(word_counts) if word_counts else 0

    reasons = []
    if days_since is not None and days_since > max_days_since_last:
        reasons.append(f"last post {days_since}d ago (max {max_days_since_last})")
    if avg_words and avg_words < min_avg_words:
        reasons.append(f"avg body {avg_words:.0f} words (min {min_avg_words}); maybe just headlines")

    return {
        "ok": not reasons,
        "reasons": reasons,
        "stats": {
            "entry_count": len(entries),
            "days_since_last": days_since,
            "avg_summary_words": round(avg_words),
        },
    }


# ── LLM judge ───────────────────────────────────────────────────────────

JUDGE_PROMPT = """You are evaluating whether a single information source is worth subscribing to for a personalized learning podcast.

The podcast teaches MECHANICS — how things work — not headlines. The learner's topic is:

  {topic}

  Their starting point: {level}
  Their goal: {goal}

Here are 3 recent items from the source you're evaluating:

{recent_items}

Decide: is this source worth keeping?

Criteria for ACCEPT:
- The author explains how something works (mechanisms, decision rules, frameworks, real examples).
- Content is at or above the learner's level — not redundant with what they already know.
- The source has an identifiable point of view, not just a feed of links.

Criteria for REJECT:
- Headline aggregation, link roundups, listicle slop, generic thought-leadership.
- Marketing copy thinly disguised as content.
- Content that's a step or more below the learner's stated starting point.
- The author isn't actually teaching — they're advertising their product or service.

Return JSON only, no prose:
{{"accept": true|false, "score": 0-100, "reason": "one sentence — what this source actually does and whether that helps the learner"}}"""


def judge_with_llm(source: dict, *, learner: dict, recent_items: list,
                   provider: str) -> dict:
    """Use the configured LLM to judge whether `source` is worth keeping.

    `recent_items` is a list of {title, summary, full_text} dicts — typically
    the most recent 3 items from the source after `discover` resolves it.
    Returns {accept, score, reason}. On LLM error, returns accept=True (don't
    block the user on a judge failure — fall through to manual review).
    """
    if not recent_items:
        return {"accept": False, "score": 0, "reason": "no recent items in feed"}

    sample = "\n\n".join(
        f"ITEM {i+1}: {it.get('title', '')}\n  {(it.get('full_text') or it.get('summary') or '')[:1500]}"
        for i, it in enumerate(recent_items[:3])
    )

    prompt = JUDGE_PROMPT.format(
        topic=learner.get("topic", ""),
        level=learner.get("level", ""),
        goal=learner.get("goal", ""),
        recent_items=sample,
    )

    try:
        raw = complete(prompt, provider=provider, max_tokens=500, temperature=0.2)
    except LLMError as e:
        print(f"  Source-judge LLM failed ({e}) — defaulting to accept")
        return {"accept": True, "score": 50, "reason": f"judge unavailable ({e})"}

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
    try:
        result = json.loads(raw.strip())
        return {
            "accept": bool(result.get("accept", True)),
            "score": int(result.get("score", 50)),
            "reason": str(result.get("reason", "")),
        }
    except Exception:
        return {"accept": True, "score": 50, "reason": "judge response unparseable, defaulting to accept"}
