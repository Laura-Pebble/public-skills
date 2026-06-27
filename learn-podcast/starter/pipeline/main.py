"""Orchestrator — one episode end to end, source-first.

Run: `python -m learn_podcast.pipeline.main`

Stages:
  1. Load config + curriculum
  2. Discover (RSS / resolvers) → apply per-source filters
  3. Source-quality sniff (cheap deterministic check — log warnings, don't block)
  4. Curate (LLM ranks items against the planned lesson, OR all items if organic)
  5. Coverage check:
       - Structured + planned lesson → confirm ≥2 sources actually cover it.
         If not, postpone the lesson and switch to organic mode for this episode.
       - Organic → LLM proposes a lesson from what's in the sources.
  6. Generate script (heavy grounding rules — every claim names its source)
  7. Verification pass (claim-grounded; rewrite drift paragraphs)
  8. TTS → MP3
  9. Publish (feed + ntfy + optional S3)

Configuration lives in `learn_podcast/config.yaml`. Curriculum in
`learn_podcast/curriculum.yaml`. Pending sources in `pending_sources.yaml`.
Output drops in `learn_podcast/output/`.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .discover import discover
from .source_quality import check_deterministic
from .curate import curate
from .script import (
    propose_lesson, check_planned_lesson_coverage, generate_script,
)
from .verify import verify_and_rewrite
from .tts import text_to_mp3
from .feed import add_episode
from .notify import push_ntfy, upload_s3


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = Path(__file__).resolve().parents[1]


# ── Config / curriculum I/O ─────────────────────────────────────────────

def load_config() -> dict:
    cfg_path = PACKAGE_DIR / "config.yaml"
    if not cfg_path.exists():
        cfg_path = ROOT / "config.yaml"
    with open(cfg_path) as f:
        return yaml.safe_load(f) or {}


def load_curriculum() -> list:
    for candidate in (PACKAGE_DIR / "curriculum.yaml", ROOT / "curriculum.yaml"):
        if candidate.exists():
            with open(candidate) as f:
                data = yaml.safe_load(f) or {}
            return data.get("lessons", []) if isinstance(data, dict) else (data or [])
    return []


def next_lesson(curriculum: list) -> dict | None:
    for lesson in curriculum:
        if lesson.get("status", "planned") == "planned":
            return lesson
    return None


def mark_shipped(curriculum: list, lesson: dict) -> None:
    if not lesson:
        return
    for l in curriculum:
        if l.get("number") == lesson.get("number"):
            l["status"] = "shipped"
            l["shipped_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            break
    path = PACKAGE_DIR / "curriculum.yaml"
    if not path.exists():
        path = ROOT / "curriculum.yaml"
    with open(path, "w") as f:
        yaml.safe_dump({"lessons": curriculum}, f, sort_keys=False)


def word_budget_for(minutes: int) -> tuple:
    target = minutes * 150
    return (int(target * 0.85), int(target * 1.15))


# ── Stage helpers ────────────────────────────────────────────────────────

def _quality_sniff(sources: list) -> None:
    """Log dead/thin feeds. Doesn't block — discover will skip them on its own."""
    print("\n[1.5] Sniffing source quality (deterministic only)")
    for s in sources:
        if (s.get("resolver") or "rss").lower() != "rss":
            continue   # resolvers don't expose a stable feed URL to check
        report = check_deterministic(s)
        if not report["ok"]:
            print(f"  WARN {s.get('name')}: {'; '.join(report['reasons'])}")


# ── Main ─────────────────────────────────────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("Learn Podcast")
    print("=" * 60)

    cfg = load_config()
    learner = cfg.get("learner", {})
    sources = cfg.get("sources", [])
    delivery = cfg.get("delivery", {})
    feed_meta = cfg.get("feed", {})
    llm_cfg = cfg.get("llm", {})
    provider = llm_cfg.get("provider", "anthropic")
    verify_strict = bool(cfg.get("verify_strict", False))

    output_dir = PACKAGE_DIR / "output"
    output_dir.mkdir(exist_ok=True)

    # ── Lesson queue (structured) ──────────────────────────────────────
    print("\n[1/9] Lesson queue")
    curriculum = load_curriculum()
    planned_lesson = next_lesson(curriculum) if curriculum else None
    if planned_lesson:
        print(f"  Next planned: Lesson {planned_lesson.get('number')} — {planned_lesson.get('topic')}")
    else:
        print("  No planned lesson — organic mode")

    # ── Source quality sniff ───────────────────────────────────────────
    _quality_sniff(sources)

    # ── Discover ───────────────────────────────────────────────────────
    print("\n[2/9] Discovering sources")
    items = discover(
        sources,
        lookback_days=cfg.get("lookback_days", 7),
        max_per_source=cfg.get("max_per_source", 3),
    )
    if not items:
        print("\nNo recent items — skipping this run.")
        return

    # ── Curate ─────────────────────────────────────────────────────────
    print("\n[3/9] Curating")
    target = cfg.get("target_sources_per_episode", 5)
    curated = curate(
        items,
        lesson=planned_lesson or {},
        learner=learner,
        target_count=target,
        provider=provider,
    )
    if not curated:
        print("\nNothing passed curation — skipping this run.")
        return

    # ── Coverage check + lesson resolution ─────────────────────────────
    print("\n[4/9] Lesson coverage check")
    lesson_for_script = planned_lesson
    lesson_proposal = None
    use_planned = False

    if planned_lesson:
        coverage = check_planned_lesson_coverage(
            planned_lesson=planned_lesson,
            curated=curated,
            provider=provider,
            min_sources=cfg.get("min_sources_per_lesson", 2),
        )
        print(f"  {coverage['reason']}")
        if coverage["covered"]:
            use_planned = True
        else:
            print(f"  Postponing Lesson {planned_lesson.get('number')} — sources don't cover it this week")
            lesson_for_script = None   # Switch to organic

    if not use_planned:
        print("  Asking sources what's actually teachable…")
        lesson_proposal = propose_lesson(
            learner=learner,
            curated=curated,
            provider=provider,
        )
        if lesson_proposal.get("coverage_confidence") == "low":
            print(f"  Low coverage confidence — switching to organic roundup. Notes: {lesson_proposal.get('notes')}")
        print(f"  Proposed: {lesson_proposal.get('lesson_topic', '(none)')}")
        for sc in lesson_proposal.get("sub_concepts", []):
            print(f"    - {sc.get('concept')} (sources {sc.get('source_indexes')})")

    # ── Script ─────────────────────────────────────────────────────────
    print("\n[5/9] Writing script")
    minutes = cfg.get("episode_minutes", 20)
    script = generate_script(
        learner=learner,
        lesson=lesson_for_script or {},
        curated=curated,
        word_budget=word_budget_for(minutes),
        provider=provider,
        lesson_proposal=lesson_proposal,
    )
    episode_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    script_draft = output_dir / f"{episode_date}-script-draft.txt"
    script_draft.write_text(script)

    # ── Verification ───────────────────────────────────────────────────
    print("\n[6/9] Verifying grounding")
    result = verify_and_rewrite(
        script=script, curated=curated, provider=provider,
        min_supported_fraction=cfg.get("min_supported_fraction", 0.7),
        strict=verify_strict,
    )
    if result["script"] is None:
        print("\nVerification rejected the episode (strict mode). Draft saved, no audio.")
        report_path = output_dir / f"{episode_date}-verify-report.json"
        import json as _json
        report_path.write_text(_json.dumps(result["report"], indent=2))
        return
    script = result["script"]
    script_path = output_dir / f"{episode_date}-script.txt"
    script_path.write_text(script)
    print(f"  Script saved: {script_path}")

    # ── TTS ────────────────────────────────────────────────────────────
    print("\n[7/9] Rendering audio")
    mp3_path = str(output_dir / f"{episode_date}.mp3")
    try:
        text_to_mp3(script, voice=cfg.get("voice", "en-US-AriaNeural"), output_path=mp3_path)
    except Exception as e:
        print(f"  TTS failed: {e}")
        return

    # ── Publish ────────────────────────────────────────────────────────
    print("\n[8/9] Publishing")
    if use_planned and planned_lesson:
        episode_title = f"Ep {planned_lesson.get('number')}: {planned_lesson.get('topic')}"
    elif lesson_proposal and lesson_proposal.get("lesson_topic"):
        episode_title = lesson_proposal["lesson_topic"]
    else:
        episode_title = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")

    s3 = delivery.get("s3", {}) or {}
    base_url = s3.get("public_url", "")
    feed_path = None
    episode_url = mp3_path

    if delivery.get("podcast_feed"):
        feed_path, episode_url, dated_mp3 = add_episode(
            mp3_path, script=script, episode_title=episode_title,
            episode_slug=episode_date, feed_meta=feed_meta, base_url=base_url,
        )
        if s3.get("bucket"):
            uploads = upload_s3(
                [dated_mp3, feed_path],
                bucket=s3.get("bucket", ""), endpoint=s3.get("endpoint", ""),
                access_key=os.environ.get("S3_ACCESS_KEY", ""),
                secret_key=os.environ.get("S3_SECRET_KEY", ""),
                public_url=base_url,
            )
            episode_url = uploads.get(dated_mp3, episode_url)

    ntfy_topic = delivery.get("ntfy_topic", "")
    if ntfy_topic:
        push_ntfy(ntfy_topic, episode_url=episode_url, script=script)

    # ── Mark shipped ───────────────────────────────────────────────────
    print("\n[9/9] Bookkeeping")
    if use_planned and planned_lesson and curriculum:
        mark_shipped(curriculum, planned_lesson)
        print(f"  Lesson {planned_lesson.get('number')} marked shipped")
    elif planned_lesson and not use_planned:
        print(f"  Lesson {planned_lesson.get('number')} stays planned — coverage check failed this week")

    print("\n" + "=" * 60)
    print(f"Done. Episode: {len(script.split())} words.")
    print(f"  Local MP3: {mp3_path}")
    if delivery.get("podcast_feed"):
        print(f"  Feed:      {feed_path}")
    if base_url:
        print(f"  Public:    {episode_url}")
    print("=" * 60)


if __name__ == "__main__":
    sys.exit(run())
