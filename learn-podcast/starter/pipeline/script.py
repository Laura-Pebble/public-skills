"""Generate the spoken-word teaching script for one episode.

Two modes:

  propose_lesson(...)
    Source-first generation. Given curated sources + learner profile, the
    LLM proposes WHAT lesson is actually teachable from these sources this
    week (concept inventory + lesson topic + 3-4 sub-concepts the sources
    cover with ≥2 sources of corroboration). Used in organic mode and when
    a planned lesson fails the coverage check.

  generate_script(...)
    Turn an approved lesson + sources into a spoken-word script. Heavy
    grounding rules (every claim names its source, ≥2-source rule for
    consensus claims, "skip what isn't covered"). Returns TTS-ready prose.
"""

from __future__ import annotations

import json

from .llm import complete, LLMError


# ── Source-first lesson proposal ────────────────────────────────────────

PROPOSE_PROMPT = """You are picking what THIS WEEK's episode of a personalized teaching podcast should cover, based on what's actually in the curated sources right now.

<LEARNER>
Topic area: {topic}
Starting point: {level}
How they'll apply this: {goal}
</LEARNER>

<CURATED SOURCES THIS WEEK>
{sources_block}
</CURATED SOURCES>

Your job: propose ONE lesson the sources actually support, not a lesson you think the learner needs.

Hard rules:
- Only propose a lesson where at least 2 of the curated sources cover it. Single-source lessons risk groupthink and hallucination; skip them.
- Match the learner's level — skip anything that re-explains what they already know.
- Return ONE lesson, not three. Be specific. "Context engineering" is too vague; "When to use prompt caching vs. RAG vs. fine-tuning, with cost rules of thumb" is right.

Return JSON only, no prose:
{{
  "lesson_topic": "concrete, specific lesson title",
  "sub_concepts": [
    {{"concept": "name", "source_indexes": [0, 2], "why_it_matters": "one sentence"}},
    ...
  ],
  "skipped_topics": ["topics that surfaced but only one source covered — note them so the learner knows they were considered"],
  "coverage_confidence": "high|medium|low",
  "notes": "anything the script-writer needs to know — e.g. sources disagree on X, source 1 is the only one with a worked example"
}}

A `coverage_confidence: low` triggers an organic-roundup episode instead of a deep lesson — say so explicitly in `notes`."""


def propose_lesson(*, learner: dict, curated: list, provider: str) -> dict:
    """Return a source-grounded lesson proposal."""
    if not curated:
        return {"lesson_topic": "", "sub_concepts": [], "coverage_confidence": "low",
                "notes": "no curated sources this week"}

    sources_block = _format_sources(curated)
    prompt = PROPOSE_PROMPT.format(
        topic=learner.get("topic", ""),
        level=learner.get("level", ""),
        goal=learner.get("goal", ""),
        sources_block=sources_block,
    )

    try:
        raw = complete(prompt, provider=provider, max_tokens=2500, temperature=0.4)
    except LLMError as e:
        print(f"  Lesson-propose LLM failed ({e})")
        return {"lesson_topic": "", "sub_concepts": [], "coverage_confidence": "low", "notes": str(e)}

    parsed = _parse_json(raw)
    if not parsed:
        return {"lesson_topic": "", "sub_concepts": [], "coverage_confidence": "low",
                "notes": "lesson proposal unparseable"}
    return parsed


def check_planned_lesson_coverage(*, planned_lesson: dict, curated: list, provider: str,
                                  min_sources: int = 2) -> dict:
    """Confirm the planned lesson is genuinely supported by the curated sources.

    Returns {covered: bool, supporting_indexes: [...], reason: str}. If
    `covered` is False, the orchestrator postpones the planned lesson and
    switches to organic mode for this episode.
    """
    if not (planned_lesson and curated):
        return {"covered": False, "supporting_indexes": [], "reason": "missing inputs"}

    sources_block = _format_sources(curated)
    prompt = f"""Does this week's curated source set actually cover the planned lesson topic well enough to teach a 20-minute episode without making things up?

<PLANNED LESSON>
{planned_lesson.get('topic', '')}
Goal: {planned_lesson.get('goal', '')}
Gaps to address: {planned_lesson.get('gaps', '')}
</PLANNED LESSON>

<CURATED SOURCES>
{sources_block}
</CURATED SOURCES>

Require: at least {min_sources} sources directly addressing the lesson topic with mechanism-level explanation (not just keyword mentions).

Return JSON only:
{{"covered": true|false, "supporting_indexes": [0, 1, ...], "reason": "one-sentence justification"}}"""

    try:
        raw = complete(prompt, provider=provider, max_tokens=400, temperature=0.1)
    except LLMError as e:
        # Be conservative on LLM failure — treat as covered to avoid blocking the user
        return {"covered": True, "supporting_indexes": list(range(len(curated))),
                "reason": f"coverage check failed ({e}), defaulting to covered"}

    parsed = _parse_json(raw) or {}
    return {
        "covered": bool(parsed.get("covered", True)),
        "supporting_indexes": parsed.get("supporting_indexes", []),
        "reason": parsed.get("reason", ""),
    }


# ── Spoken-word script generation ───────────────────────────────────────

SCRIPT_PROMPT = """You are writing one episode of a personalized teaching podcast.

<LEARNER>
Topic area: {topic}
Starting point: {level}
How they will apply this: {goal}
</LEARNER>

<TODAY'S LESSON (source-grounded — only teach what's actually here)>
Lesson: {lesson_topic}
Sub-concepts to cover (each backed by ≥2 sources from below):
{sub_concepts_block}
Notes from the lesson-proposer: {notes}
</TODAY'S LESSON>

<CURATED SOURCES — the ONLY factual backbone>
{sources_block}
</CURATED SOURCES>

WRITE A SPOKEN SCRIPT. Plain prose. No markdown, no headers spoken aloud, no bullet lists.
Target length: {word_min}-{word_max} words ({min_min}-{max_min} minutes spoken).

GROUNDING RULES (these are NON-NEGOTIABLE — violating any one fails the episode):

1. Every factual claim — every concrete assertion about how something works, what someone said, what a number is — must come from one of the SOURCES above. If a claim isn't in the sources, do not make it.
2. Name the source (outlet or author) for every non-trivial claim. "Anthropic's recent post said…" / "according to Mollick…" / "Penn argued…" — natural conversational attribution.
3. Quote a short phrase (5-15 words) from a source when the quote IS the point — when the wording carries the insight. Don't read URLs aloud. Don't read a bibliography list aloud. Don't say [1] or footnote-style citations.
4. Two-source rule: present a claim as the field's consensus only when ≥2 sources agree. If just one source says it, frame it AS that source's view: "Simon Willison argues X — he's the only one in today's sources making this claim." Never claim consensus from a single source.
5. If sources disagree, surface the disagreement explicitly and name both sides.
6. If a sub-concept isn't fully covered by the sources, say so and skip it: "Today's sources don't go deep on Y, so we'll come back to it." Do NOT fill in from general knowledge.

TEACHING RULES (Mollick / Khanmigo / Bloom's-aligned):

7. Define every technical term on first use, calibrated to the learner's stated starting point. Skip definitions for things they said they already know.
8. One worked example per concept, with real numbers / real prompts / real model names pulled directly from a source. No invented examples.
9. Surface one likely misconception the learner might hold and walk through why it's wrong, citing the source that corrects it.
10. End with one specific retrieval-practice question the learner could answer to prove they got it (Mollick strategy #3). Not a homework assignment — a 30-second self-check.

STRUCTURE (four acts, in this order):

ACT 1 — HOOK (≈ 10% of words): open with a concrete moment from one of the sources. Name the source. State the question this episode answers.
ACT 2 — MECHANICS (≈ 55%): teach each sub-concept in order. Define, explain the mechanic, give the worked example, attribute each claim.
ACT 3 — PRACTICAL APPLICATION (≈ 25%): translate the mechanics into how the learner applies this given their stated goal. Decision rules, common failure modes.
ACT 4 — RETRIEVAL + TRY THIS WEEK (≈ 10%): the retrieval-practice question, then one concrete experiment to run. End with "Today's sources were [name], [name], [name]." Then stop.

FORBIDDEN — fail-conditions for the episode:
- Greetings, intros, "welcome back," "in this episode we'll cover," "let's dive in"
- Filler: "X is revolutionizing," "the future of Y," "leverage Z to," "unlock the power of"
- Generic platitudes. Be specific.
- Sycophancy about the learner, sources, or anyone else. Teach.
- Reading URLs, reading citation lists, footnote-style numbering.
- Any factual claim not grounded in one of the sources.

Return ONLY the spoken script. Nothing before, nothing after."""


def generate_script(*, learner: dict, lesson: dict, curated: list,
                    word_budget: tuple, provider: str,
                    lesson_proposal: dict | None = None) -> str:
    """Return the spoken script as a single string.

    `lesson` is the curriculum lesson (may be empty in organic mode).
    `lesson_proposal` is the source-grounded proposal from propose_lesson()
    (preferred when present — its sub-concepts have already been gated to
    ≥2-source coverage).
    """
    if not curated:
        return _fallback(lesson, word_budget)

    word_min, word_max = word_budget
    min_min, max_min = round(word_min / 150), round(word_max / 150)

    if lesson_proposal and lesson_proposal.get("lesson_topic"):
        lesson_topic = lesson_proposal["lesson_topic"]
        sub_concepts = lesson_proposal.get("sub_concepts", [])
        notes = lesson_proposal.get("notes", "")
    elif lesson:
        lesson_topic = lesson.get("topic", "")
        sub_concepts = []
        notes = lesson.get("gaps", "") or ""
    else:
        lesson_topic = "open episode — teach what the sources collectively cover"
        sub_concepts = []
        notes = ""

    sub_concepts_block = "\n".join(
        f"  - {s.get('concept', '')} (sources: {s.get('source_indexes', [])}) — {s.get('why_it_matters', '')}"
        for s in sub_concepts
    ) or "  (no pre-selected sub-concepts — let the script writer pick from the sources)"

    sources_block = _format_sources(curated, include_full_text=True)

    prompt = SCRIPT_PROMPT.format(
        topic=learner.get("topic", ""),
        level=learner.get("level", ""),
        goal=learner.get("goal", ""),
        lesson_topic=lesson_topic,
        sub_concepts_block=sub_concepts_block,
        notes=notes,
        sources_block=sources_block,
        word_min=word_min,
        word_max=word_max,
        min_min=min_min,
        max_min=max_min,
    )

    try:
        script = complete(prompt, provider=provider, max_tokens=12000, temperature=0.6)
    except LLMError as e:
        print(f"  Script LLM failed ({e}) — using fallback")
        return _fallback(lesson, word_budget)

    word_count = len(script.split())
    print(f"  Script: {word_count} words (target {word_min}-{word_max})")
    if word_count < word_min * 0.7:
        print(f"  Warning: script well below target — model returned a short version")
    return script.strip()


# ── Helpers ─────────────────────────────────────────────────────────────

def _format_sources(curated, include_full_text=True):
    blocks = []
    for i, s in enumerate(curated):
        body = (s.get("full_text") or s.get("summary") or "")[:6000] if include_full_text else ""
        block = (
            f"SOURCE {i}: {s.get('title', '')}\n"
            f"  Author: {s.get('author', '')}\n"
            f"  Outlet: {s.get('source', '')} ({s.get('date', '')})\n"
            f"  URL: {s.get('url', '')}\n"
            f"  One-line take: {s.get('one_line_take', '')}"
        )
        if body:
            block += f"\n  Body:\n{body}"
        blocks.append(block)
    return "\n\n".join(blocks)


def _parse_json(raw):
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
    try:
        return json.loads(raw.strip())
    except Exception:
        return None


def _fallback(lesson, word_budget):
    topic = (lesson or {}).get("topic") or "today's lesson"
    return (
        f"Today's episode on {topic} couldn't be generated automatically — the script "
        f"generator was unavailable. The pipeline will retry on its next scheduled run."
    )
