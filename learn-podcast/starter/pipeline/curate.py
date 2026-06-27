"""Rank discovered items against the lesson and the user's learning goal.

The LLM picks the top N items that best teach this lesson, given the user's
starting point and how they'll apply the learning. Returns the curated subset
with a one-line take for each.
"""

from __future__ import annotations

import json

from .llm import complete, LLMError


CURATE_PROMPT = """You are curating sources for one episode of a personalized teaching podcast.

<LEARNER PROFILE>
Topic: {topic}
Starting point: {level}
How they'll apply this: {goal}
</LEARNER PROFILE>

<TODAY'S LESSON>
{lesson_block}
</TODAY'S LESSON>

<CANDIDATE SOURCES>
{candidates_block}
</CANDIDATE SOURCES>

Pick the {target_count} sources that best teach this lesson FOR THIS LEARNER. Optimize for:
- Mechanic-level explanation (how something actually works), not surface news.
- Diversity of viewpoints — don't pick 3 items that say the same thing.
- Calibration to their starting point — skip items they'd find obvious.
- Relevance to how they'll apply this.

Return JSON ONLY, no prose, no code fence:
{{"picks": [{{"index": 0, "one_line_take": "..."}}, ...]}}

`index` is the 0-based position in the candidate list above. `one_line_take` is your
one-sentence take on what THIS source teaches the learner about today's lesson — used
later as the bridge in the spoken script. Max {target_count} picks. Fewer is fine if
some candidates aren't relevant; do NOT pad."""


def curate(items: list, *, lesson: dict, learner: dict, target_count: int,
           provider: str) -> list:
    """Return the curated subset of items, each enriched with `one_line_take`."""
    if not items:
        return []
    if len(items) <= target_count:
        # Nothing to rank — return all, with empty takes filled in by the script stage
        return [{**it, "one_line_take": ""} for it in items]

    candidates_block = "\n\n".join(
        f"INDEX {i}:\n"
        f"  Title: {it.get('title', '')}\n"
        f"  Source: {it.get('source', '')} ({it.get('author', '')})\n"
        f"  Date: {it.get('date', '')}\n"
        f"  Summary: {(it.get('summary') or it.get('full_text') or '')[:600]}"
        for i, it in enumerate(items)
    )

    lesson_block = (
        f"Lesson {lesson.get('number', '?')}: {lesson.get('topic', '(open)')}\n"
        f"Goal: {lesson.get('goal', '')}\n"
        f"Gaps to address: {lesson.get('gaps', '(none specified)')}"
    ) if lesson else "(no structured lesson — pick what best serves the learner this week)"

    prompt = CURATE_PROMPT.format(
        topic=learner.get("topic", ""),
        level=learner.get("level", ""),
        goal=learner.get("goal", ""),
        lesson_block=lesson_block,
        candidates_block=candidates_block,
        target_count=target_count,
    )

    try:
        raw = complete(prompt, provider=provider, max_tokens=2000, temperature=0.3)
    except LLMError as e:
        print(f"  Curate LLM failed ({e}) — falling back to first {target_count} items")
        return [{**it, "one_line_take": ""} for it in items[:target_count]]

    picks = _parse_picks(raw, len(items))
    if not picks:
        print(f"  Curate parse failed — falling back to first {target_count} items")
        return [{**it, "one_line_take": ""} for it in items[:target_count]]

    out = []
    for p in picks[:target_count]:
        idx = p.get("index")
        if isinstance(idx, int) and 0 <= idx < len(items):
            out.append({**items[idx], "one_line_take": p.get("one_line_take", "")})
    print(f"  Curated {len(out)} item(s)")
    return out


def _parse_picks(raw: str, n_items: int) -> list:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
    try:
        data = json.loads(raw.strip())
        picks = data.get("picks", []) if isinstance(data, dict) else []
        return [p for p in picks if isinstance(p, dict) and isinstance(p.get("index"), int)]
    except Exception:
        return []
