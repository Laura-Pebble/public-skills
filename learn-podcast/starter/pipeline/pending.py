"""Watch for sources that don't exist yet.

`pending_sources.yaml` lists upcoming feeds — podcasts about to launch,
newsletters teased by a person you trust. A weekly job queries the free
iTunes Search API + PodcastIndex API and promotes any fuzzy-match that
clears the confidence threshold into `config.yaml`'s `sources:` list.

Run manually with `python -m learn_podcast.pipeline.pending`, or wire as
a separate GitHub Actions cron.
"""

from __future__ import annotations

import hashlib
import os
import sys
import time
from datetime import date
from pathlib import Path

import requests
import yaml

try:
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None


PACKAGE_DIR = Path(__file__).resolve().parents[1]
PENDING_PATH = PACKAGE_DIR / "pending_sources.yaml"
CONFIG_PATH  = PACKAGE_DIR / "config.yaml"


def _itunes_search(query, limit=5):
    try:
        r = requests.get(
            "https://itunes.apple.com/search",
            params={"term": query, "entity": "podcast", "limit": limit},
            timeout=15,
        )
        if r.status_code != 200:
            return []
        return [
            (it.get("collectionName", ""), it.get("artistName", ""), it.get("feedUrl", ""), "itunes")
            for it in r.json().get("results", []) if it.get("feedUrl")
        ]
    except Exception as e:
        print(f"  iTunes search failed: {e}")
        return []


def _podcastindex_search(query, limit=5):
    key, secret = os.environ.get("PODCASTINDEX_KEY"), os.environ.get("PODCASTINDEX_SECRET")
    if not (key and secret):
        return []
    ts = str(int(time.time()))
    sig = hashlib.sha1((key + secret + ts).encode()).hexdigest()
    try:
        r = requests.get(
            "https://api.podcastindex.org/api/1.0/search/byterm",
            params={"q": query, "max": limit},
            headers={
                "X-Auth-Key": key, "X-Auth-Date": ts, "Authorization": sig,
                "User-Agent": "LearnPodcast/1.0",
            },
            timeout=15,
        )
        if r.status_code != 200:
            return []
        return [
            (f.get("title", ""), f.get("author", ""), f.get("url", ""), "podcastindex")
            for f in r.json().get("feeds", []) if f.get("url")
        ]
    except Exception as e:
        print(f"  PodcastIndex search failed: {e}")
        return []


def _feed_alive(feed_url):
    """Confirm the feed parses and has at least one entry — drops dead matches."""
    try:
        import feedparser
        parsed = feedparser.parse(feed_url)
        return bool(parsed.entries)
    except Exception:
        return False


def check_one(entry: dict) -> dict | None:
    """Probe the world for `entry`. Return a promotion dict, or None."""
    if fuzz is None:
        print("  rapidfuzz not installed — skip with `pip install rapidfuzz`")
        return None

    if entry.get("earliest_launch") and date.today().isoformat() < entry["earliest_launch"]:
        return None

    candidates = _itunes_search(entry["query"]) + _podcastindex_search(entry["query"])
    min_conf = int(entry.get("min_confidence", 85))
    expected_author = entry.get("expected_author", "")

    for title, author, feed_url, source_api in candidates:
        title_score = fuzz.token_set_ratio(entry["name"], title)
        author_score = fuzz.token_set_ratio(expected_author, author) if expected_author else 100
        if min(title_score, author_score) < min_conf:
            continue
        if not _feed_alive(feed_url):
            continue
        return {
            "name": title,
            "url": feed_url,
            "kind": "podcast",
            "_promoted_from": entry["name"],
            "_promoted_via": source_api,
            "_promoted_confidence": min(title_score, author_score),
            "_promoted_at": date.today().isoformat(),
        }
    return None


def run() -> None:
    if not PENDING_PATH.exists():
        print(f"No pending sources at {PENDING_PATH} — nothing to watch.")
        return

    pending = yaml.safe_load(PENDING_PATH.read_text()) or []
    if not isinstance(pending, list):
        print(f"{PENDING_PATH} should be a YAML list — got {type(pending).__name__}")
        return

    config = yaml.safe_load(CONFIG_PATH.read_text()) or {}
    sources = config.get("sources", []) or []
    existing_urls = {s.get("url") for s in sources if s.get("url")}

    still_pending, promoted = [], []
    for entry in pending:
        hit = check_one(entry)
        if hit and hit["url"] not in existing_urls:
            promoted.append(hit)
            sources.append(hit)
        else:
            still_pending.append(entry)

    if promoted:
        config["sources"] = sources
        CONFIG_PATH.write_text(yaml.safe_dump(config, sort_keys=False))
        PENDING_PATH.write_text(yaml.safe_dump(still_pending, sort_keys=False))
        for p in promoted:
            print(f"  PROMOTED: {p['name']} (confidence={p['_promoted_confidence']}, via {p['_promoted_via']})")
    else:
        print("  No pending sources promoted this run.")


if __name__ == "__main__":
    sys.exit(run())
