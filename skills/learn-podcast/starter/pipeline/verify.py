"""Verification pass — claim-grounded check with paragraph rewrite on failure.

This is the LIGHTWEIGHT, automated complement to a heavyweight manual
verification protocol (e.g. Pebble Marketing's research-verification skill).
The heavyweight pass — source URL fetching, independent corroboration,
methodology review, credibility rating — is what to run before quoting an
episode publicly or feeding its claims into a client artifact. This module
covers the in-pipeline subset that can run on every episode without human
review: does the script actually say what the curated source bodies say.

Two-stage gate, following Chain-of-Verification (Dhuliawala et al. 2023)
adapted to the source-grounded case:

  Stage 1 — extract atomic claims from the draft script and judge each
            against the curated source set. Returns VERIFIED / FLAGGED /
            BLOCKED for each claim (terminology aligned with the
            research-verification closed-enum taxonomy).

  Stage 2 — for paragraphs containing ≥1 FLAGGED or BLOCKED claim, rewrite
            just that paragraph constrained to the supporting sources.

Tunable: a `strict` mode that rejects the whole episode if the VERIFIED
fraction drops below `min_supported_fraction` (default 0.7 lenient; push to
0.85+ for high-stakes content).

Verdict tags (closed enum):
  VERIFIED  — claim is directly supported by one of the curated sources.
  FLAGGED   — claim mismatch: source covers the topic but the script
              materially distorts it.
  BLOCKED   — no source covers the claim.
"""

from __future__ import annotations

import json
import re

from .llm import complete, LLMError


EXTRACT_PROMPT = """You are auditing a podcast script for source-grounding violations.

<SCRIPT DRAFT>
{script}
</SCRIPT DRAFT>

<CURATED SOURCES>
{sources_block}
</CURATED SOURCES>

For every factual claim in the script — every concrete assertion about how something works, what someone said, what a number is, what a study found — classify it as one of:

  VERIFIED — the claim is directly stated or clearly implied by one of the sources. Quote the supporting phrase from the source (max ~30 words).
  FLAGGED     — the source says something related but the script's version is materially different (different number, different mechanism, attributed wrongly, etc.).
  UNVERIFIED — no source covers this claim at all. The script invented it or pulled from outside the sources.

Ignore: rhetorical questions, generic transitions, the learner-direct-address parts (act 4 "try this week"), structural framing. Only audit factual claims.

Return JSON only, no prose:
{{
  "claims": [
    {{
      "claim": "exact sentence or phrase from the script",
      "verdict": "VERIFIED|FLAGGED|UNVERIFIED",
      "source_index": 0,                                   // 0-based index into the sources, or null
      "supporting_phrase": "quote from source if VERIFIED, or null"
    }}
  ]
}}

Cap at 50 claims — focus on the load-bearing ones if there are more."""


REWRITE_PROMPT = """The following paragraph from a podcast script contains claims that don't match the available sources. Rewrite it so EVERY factual claim is directly grounded in one of the sources below. Drop any claim you can't ground. Keep the same conversational voice and approximate length.

<PARAGRAPH>
{paragraph}
</PARAGRAPH>

<AVAILABLE SOURCES (factual backbone)>
{sources_block}
</AVAILABLE SOURCES>

<FLAGGED CLAIMS>
{flagged_block}
</FLAGGED CLAIMS>

Return ONLY the rewritten paragraph. No preamble. No markdown."""


def verify_and_rewrite(*, script: str, curated: list, provider: str,
                       min_supported_fraction: float = 0.7,
                       strict: bool = False) -> dict:
    """Audit `script` against `curated`, rewrite drifty paragraphs.

    Returns {script, report} where `script` is the (possibly rewritten) text
    and `report` contains the per-claim verdicts + stats. If strict=True and
    the supported fraction is below the threshold even after rewriting, the
    returned script is None (caller decides whether to ship or abort).
    """
    if not curated or not script.strip():
        return {"script": script, "report": {"skipped": True}}

    sources_block = _format_sources(curated)

    extract_prompt = EXTRACT_PROMPT.format(script=script, sources_block=sources_block)
    try:
        raw = complete(extract_prompt, provider=provider, max_tokens=6000, temperature=0.1)
    except LLMError as e:
        print(f"  Verify LLM failed ({e}) — shipping unverified")
        return {"script": script, "report": {"error": str(e)}}

    parsed = _parse_json(raw)
    if not parsed or "claims" not in parsed:
        print(f"  Verify parse failed — shipping unverified")
        return {"script": script, "report": {"error": "parse_failed"}}

    claims = parsed.get("claims", [])
    stats = _summarize(claims)
    print(f"  Verify: {stats['verified']}/{stats['total']} verified "
          f"({stats['flagged']} flagged, {stats['blocked']} blocked)")

    if stats["needs_rewrite"] == 0:
        return {"script": script, "report": {"claims": claims, "stats": stats}}

    rewritten = _rewrite_paragraphs(script, claims, curated, sources_block, provider)

    if strict and stats["verified_fraction"] < min_supported_fraction:
        print(f"  STRICT mode: verified_fraction {stats['verified_fraction']:.0%} "
              f"< {min_supported_fraction:.0%} — episode rejected")
        return {"script": None, "report": {"claims": claims, "stats": stats, "rejected": True}}

    return {"script": rewritten, "report": {"claims": claims, "stats": stats, "rewrote": True}}


def audit_for_strategist(*, script: str, curated: list, episode_title: str = "") -> str:
    """Export the episode's claims-with-sources for a heavyweight manual audit.

    Use this when you want to run an external research-verification protocol
    on an episode (e.g. before quoting it publicly). Output is a markdown
    block you paste into a Claude.ai project where the verification skill
    runs. The in-pipeline gate above is the per-episode automated baseline;
    this is the escape hatch for higher-rigor passes.
    """
    if not curated:
        return f"# {episode_title}\n\nNo curated sources to audit.\n"

    lines = [
        f"# Verification request — {episode_title or 'episode'}",
        "",
        "The pipeline ran its automated VERIFIED/FLAGGED/BLOCKED gate already.",
        "Run the full external six-check protocol on the load-bearing claims below.",
        "",
        "## Sources cited",
        "",
    ]
    for i, s in enumerate(curated, start=1):
        lines.append(
            f"{i}. **{s.get('title', '')}** — {s.get('author', '')}, "
            f"{s.get('source', '')} ({s.get('date', '')})\n"
            f"   URL: {s.get('url', '')}\n"
        )

    lines.extend(["", "## Episode script (verify every factual claim)", "", script])
    return "\n".join(lines)


def _format_sources(curated):
    blocks = []
    for i, s in enumerate(curated):
        body = (s.get("full_text") or s.get("summary") or "")[:5000]
        blocks.append(
            f"SOURCE {i}: {s.get('title', '')}\n"
            f"  Author: {s.get('author', '')} ({s.get('source', '')})\n"
            f"  URL: {s.get('url', '')}\n"
            f"  Body: {body}"
        )
    return "\n\n".join(blocks)


def _parse_json(raw):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
    try:
        return json.loads(raw.strip())
    except Exception:
        return None


def _summarize(claims):
    total = len(claims) or 1
    verified = sum(1 for c in claims if c.get("verdict") == "VERIFIED")
    flagged = sum(1 for c in claims if c.get("verdict") == "FLAGGED")
    blocked = sum(1 for c in claims if c.get("verdict") == "BLOCKED")
    return {
        "total": len(claims),
        "verified": verified,
        "flagged": flagged,
        "blocked": blocked,
        "verified_fraction": verified / total,
        "needs_rewrite": flagged + blocked,
    }


def _rewrite_paragraphs(script, claims, curated, sources_block, provider):
    paragraphs = re.split(r"\n\s*\n", script)
    flagged_by_para = {}
    for c in claims:
        if c.get("verdict") in ("FLAGGED", "BLOCKED"):
            for idx, para in enumerate(paragraphs):
                if c.get("claim", "")[:60] in para:
                    flagged_by_para.setdefault(idx, []).append(c)
                    break

    if not flagged_by_para:
        return script

    for idx, flagged in flagged_by_para.items():
        flagged_block = "\n".join(f"- [{c['verdict']}] {c['claim']}" for c in flagged)
        prompt = REWRITE_PROMPT.format(
            paragraph=paragraphs[idx],
            sources_block=sources_block,
            flagged_block=flagged_block,
        )
        try:
            new_para = complete(prompt, provider=provider, max_tokens=1500, temperature=0.3).strip()
            if new_para and len(new_para.split()) >= 10:
                paragraphs[idx] = new_para
                print(f"  Rewrote paragraph {idx} ({len(flagged)} flagged claim(s))")
        except LLMError as e:
            print(f"  Rewrite paragraph {idx} failed ({e}) — keeping original")

    return "\n\n".join(paragraphs)
