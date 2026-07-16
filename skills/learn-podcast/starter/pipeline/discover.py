"""Pull recent posts from every configured source, apply filters.

Each source in config.yaml has:
  - name, url                                    # required
  - kind?       blog | podcast | newsletter | youtube | linkedin | person
  - resolver?   rss (default) | rss_app | apify_linkedin | podchaser_person
  - filter?     {author, keyword_any, keyword_all, min_words, published_after}

Plain RSS sources are fetched directly here for backwards compat. Anything
with an explicit `resolver:` is dispatched through resolvers.resolve().

Returns a flat list of dicts: {title, url, author, source, date, summary, full_text}.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone, timedelta
from html import unescape

import feedparser
import requests

try:
    import trafilatura
except ImportError:
    trafilatura = None

from .filters import apply as apply_filters
from .resolvers import resolve as resolve_source


USER_AGENT = "LearnPodcast/1.0 (+https://github.com/)"


def discover(sources: list, *, lookback_days: int = 7, max_per_source: int = 3) -> list:
    """Walk every source, return items with full text + filters applied."""
    if not sources:
        return []

    items = []
    for src in sources:
        resolver_name = (src.get("resolver") or "rss").lower()

        if resolver_name == "rss":
            raw_items = _fetch_rss(src, lookback_days, max_per_source * 2)
        else:
            raw_items = resolve_source(src, lookback_days, max_per_source * 2)

        filtered = apply_filters(raw_items, src.get("filter"))
        if not filtered and raw_items:
            print(f"    (all {len(raw_items)} item(s) filtered out)")
        items.extend(filtered[:max_per_source])

    print(f"  Discovered {len(items)} item(s) total (post-filter)")
    return items


def _fetch_rss(src: dict, lookback_days: int, max_items: int) -> list:
    """The original plain-RSS path, factored out so resolvers.resolve_rss can reuse."""
    name = src.get("name", "Unknown")
    url = src.get("url", "")
    if not url:
        return []

    print(f"  [{src.get('kind', 'blog')}] {name}…")
    try:
        feed = feedparser.parse(url)
    except Exception as e:
        print(f"    feedparser error: {e}")
        return []

    if getattr(feed, "bozo", False) and not feed.entries:
        print(f"    (feed unreadable, skipping)")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    out = []
    for entry in feed.entries:
        if len(out) >= max_items:
            break
        published_iso = _parsed_published(entry)
        if not _is_recent(published_iso, cutoff):
            continue

        entry_url = getattr(entry, "link", "")
        title = getattr(entry, "title", "Untitled")
        author = getattr(entry, "author", "") or name
        summary = _strip_html(getattr(entry, "summary", "") or getattr(entry, "description", ""))

        full_text = _fetch_full_text(entry_url) if entry_url else ""
        if entry_url:
            time.sleep(0.3)

        out.append({
            "title": title,
            "url": entry_url,
            "author": author,
            "source": name,
            "date": published_iso[:10] if published_iso else "",
            "summary": summary[:1500],
            "full_text": full_text[:20000],
        })

    print(f"    +{len(out)} item(s)")
    return out


def _strip_html(text):
    if not text:
        return ""
    return unescape(re.sub(r"<[^>]+>", "", text)).strip()


def _parsed_published(entry):
    for key in ("published_parsed", "updated_parsed"):
        t = getattr(entry, key, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc).isoformat()
            except Exception:
                continue
    return ""


def _is_recent(published_iso, cutoff):
    if not published_iso:
        return True
    try:
        dt = datetime.fromisoformat(published_iso.replace("Z", "+00:00"))
        return dt >= cutoff
    except Exception:
        return True


def _fetch_full_text(url, timeout=15):
    if trafilatura is None:
        return ""
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
        if r.status_code != 200:
            return ""
        return trafilatura.extract(r.text, include_comments=False, include_tables=False) or ""
    except Exception:
        return ""
