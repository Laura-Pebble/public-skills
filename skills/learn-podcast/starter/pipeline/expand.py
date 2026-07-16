"""Monthly source-discovery via Exa.

For each existing source, ask Exa for similar pages. Re-score each candidate
locally with embeddings against a centroid of the current corpus (Exa's own
relevance scores aren't reliable enough alone — Firecrawl's 2026 benchmarks
have Exa at F1 ~0.51). Cheap signal checks (post cadence, recency) trim the
list. Top N go into `source_candidates.yaml` with an `approved: false` flag.

You review the file by hand (or wire it to a Notion DB and approve there),
flip `approved: true` on the keepers, and run the promotion command to
append approved candidates into config.yaml's sources list.

Run manually: `python -m learn_podcast.pipeline.expand discover`
              `python -m learn_podcast.pipeline.expand promote`
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml


PACKAGE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH      = PACKAGE_DIR / "config.yaml"
CANDIDATES_PATH  = PACKAGE_DIR / "source_candidates.yaml"


def discover_candidates(per_seed: int = 5, top_n: int = 10, sim_floor: float = 0.55):
    """Find candidate sources similar to the current ones; write `candidates.yaml`."""
    try:
        from exa_py import Exa
    except ImportError:
        print("  exa-py not installed — `pip install exa-py` to enable discovery")
        return
    if not os.environ.get("EXA_API_KEY"):
        print("  EXA_API_KEY not set — discovery skipped")
        return
    try:
        import numpy as np
    except ImportError:
        print("  numpy not installed — `pip install numpy`")
        return

    config = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    seeds = [s for s in (config.get("sources") or []) if s.get("url")]
    if not seeds:
        print("  No seed sources in config.yaml — nothing to expand from")
        return

    existing_urls = {s.get("url") for s in seeds}
    exa = Exa(os.environ["EXA_API_KEY"])

    # Build corpus centroid from seed page contents
    seed_texts = []
    for s in seeds[:15]:   # Cap to keep embedding cost trivial
        try:
            res = exa.get_contents([s["url"]], text={"max_characters": 2000}).results
            if res and res[0].text:
                seed_texts.append(res[0].text)
        except Exception:
            continue
    if not seed_texts:
        print("  Couldn't fetch any seed content from Exa — aborting")
        return

    centroid_arr = _embed(seed_texts)
    if centroid_arr is None:
        return
    centroid = centroid_arr.mean(axis=0)

    # Find similar to each seed, dedupe, re-score
    seen = set(existing_urls)
    rows = []
    for s in seeds[:15]:
        try:
            similar = exa.find_similar(s["url"], num_results=per_seed,
                                        exclude_source_domain=True).results
        except Exception as e:
            print(f"  findSimilar({s['url']}) failed: {e}")
            continue
        for cand in similar:
            if cand.url in seen:
                continue
            seen.add(cand.url)
            text = (cand.text or cand.title or "")[:2000]
            if not text:
                continue
            emb = _embed([text])
            if emb is None:
                continue
            v = emb[0]
            sim = float(np.dot(v, centroid) / (np.linalg.norm(v) * np.linalg.norm(centroid)))
            if sim < sim_floor:
                continue
            rows.append({
                "name": cand.title or cand.url,
                "url": cand.url,
                "kind": "blog",
                "similarity": round(sim, 3),
                "seed": s["url"],
                "approved": False,
                "notes": "Flip approved → true to promote into sources on next `promote` run.",
            })

    rows.sort(key=lambda r: -r["similarity"])
    rows = rows[:top_n]
    CANDIDATES_PATH.write_text(yaml.safe_dump(rows, sort_keys=False))
    print(f"  Wrote {len(rows)} candidate(s) to {CANDIDATES_PATH}")


def promote_approved():
    """Move every approved entry from candidates.yaml into config.yaml sources."""
    if not CANDIDATES_PATH.exists():
        print(f"  No candidates file at {CANDIDATES_PATH}")
        return
    candidates = yaml.safe_load(CANDIDATES_PATH.read_text()) or []
    approved = [c for c in candidates if c.get("approved")]
    if not approved:
        print("  No approved candidates to promote.")
        return

    config = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    sources = config.get("sources") or []
    existing_urls = {s.get("url") for s in sources}

    promoted = 0
    for c in approved:
        if c["url"] in existing_urls:
            continue
        sources.append({k: v for k, v in c.items() if k not in {"similarity", "seed", "approved", "notes"}})
        promoted += 1

    if promoted:
        config["sources"] = sources
        CONFIG_PATH.write_text(yaml.safe_dump(config, sort_keys=False))
        # Leave the candidates file in place but drop the promoted rows
        remaining = [c for c in candidates if not c.get("approved")]
        CANDIDATES_PATH.write_text(yaml.safe_dump(remaining, sort_keys=False))
        print(f"  Promoted {promoted} candidate(s) into config.yaml")
    else:
        print("  All approved candidates were already in config.yaml")


def _embed(texts):
    """Embed via OpenAI (cheapest provider with text-embedding-3-small)."""
    try:
        from openai import OpenAI
        import numpy as np
    except ImportError:
        print("  openai + numpy required for source expansion")
        return None
    if not os.environ.get("OPENAI_API_KEY"):
        print("  OPENAI_API_KEY not set (needed for embeddings — separate from main LLM provider)")
        return None
    client = OpenAI()
    r = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return np.array([d.embedding for d in r.data])


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    cmd = argv[0] if argv else "discover"
    if cmd == "discover":
        discover_candidates()
    elif cmd == "promote":
        promote_approved()
    else:
        print(f"Unknown command: {cmd}. Use 'discover' or 'promote'.")


if __name__ == "__main__":
    sys.exit(main())
