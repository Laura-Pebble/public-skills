"""Source resolvers — pluggable fetchers for content that isn't plain RSS.

A source in config.yaml can set `resolver:` to pick a strategy:

  - "rss"             (default) — feedparser on the URL
  - "rss_app"         — wrap a JS-rendered or login-walled page through rss.app
  - "apify_linkedin"  — pull a person's LinkedIn posts via Apify's harvestapi actor
  - "podchaser_person" — pull recent podcast guest appearances for a named person

Each resolver returns the same shape as discover.discover(): a list of dicts
with {title, url, author, source, date, summary, full_text}.

Optional dependencies (boto3 / apify_client / podchaser SDK aren't pulled by
the core requirements.txt) — each resolver fails closed (empty list + log) if
the SDK is missing or the auth env var is unset.
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime, timezone, timedelta
from html import unescape

import feedparser
import requests


USER_AGENT = "LearnPodcast/1.0 (+https://github.com/)"


# ── Default RSS resolver — same path the discover stage already used ─────

def resolve_rss(source: dict, lookback_days: int, max_items: int) -> list:
    from .discover import discover  # avoid circular import at module load
    return discover([source], lookback_days=lookback_days, max_per_source=max_items)


# ── rss.app bridge — for Webflow / JS-rendered / paywalled sites ─────────

def resolve_rss_app(source: dict, lookback_days: int, max_items: int) -> list:
    """Fetch via rss.app's bridge.

    Two ways to wire this:
      1. Pre-create the feed in rss.app's UI and paste the rss.app feed URL
         into source.url — then this resolver is just plain feedparser.
      2. Provide RSS_APP_API_KEY and the source's `url` is the original page;
         the resolver creates/reuses a feed via the rss.app API and parses it.

    Path 1 is the simpler default — recommended for one-off sources.
    """
    feed_url = source.get("rss_app_feed") or source.get("url", "")
    if not feed_url:
        print(f"  [rss_app] {source.get('name')}: no feed URL")
        return []

    if not feed_url.startswith("https://rss.app/"):
        # User pasted the original page URL and expects on-the-fly creation
        api_key = os.environ.get("RSS_APP_API_KEY")
        if not api_key:
            print(f"  [rss_app] {source.get('name')}: paste the rss.app feed URL into source.url, or set RSS_APP_API_KEY")
            return []
        feed_url = _create_rss_app_feed(feed_url, api_key)
        if not feed_url:
            return []

    return resolve_rss({**source, "url": feed_url}, lookback_days, max_items)


def _create_rss_app_feed(page_url: str, api_key: str) -> str | None:
    """Create (or find) an rss.app feed for `page_url`. Returns feed URL or None."""
    try:
        r = requests.post(
            "https://api.rss.app/v1/feeds",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"url": page_url},
            timeout=30,
        )
        if r.status_code in (200, 201):
            return r.json().get("rss_feed_url")
        print(f"  [rss_app] API returned {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"  [rss_app] API call failed: {e}")
    return None


# ── Apify LinkedIn personal posts — via harvestapi/linkedin-profile-posts ─

def resolve_apify_linkedin(source: dict, lookback_days: int, max_items: int) -> list:
    """Pull a person's recent LinkedIn posts.

    Requires APIFY_TOKEN in env. Cost: roughly $3-4 per 1000 posts on the
    HarvestAPI actor. Recommended cadence: weekly, not daily.

    source.url should be the canonical profile URL, e.g.
      https://www.linkedin.com/in/jdoe/

    No cookies, no user account — relies on public-page scraping which is
    legally defensible in the US after hiQ v. LinkedIn and Meta v. Bright Data.
    """
    try:
        from apify_client import ApifyClient
    except ImportError:
        print(f"  [apify_linkedin] {source.get('name')}: apify-client not installed — `pip install apify-client`")
        return []

    token = os.environ.get("APIFY_TOKEN")
    if not token:
        print(f"  [apify_linkedin] {source.get('name')}: APIFY_TOKEN not set")
        return []

    profile_url = source.get("url", "")
    if not profile_url:
        return []

    client = ApifyClient(token)
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    try:
        run = client.actor("harvestapi/linkedin-profile-posts").call(
            run_input={"profileUrls": [profile_url], "maxPosts": max_items * 3},
            timeout_secs=180,
        )
    except Exception as e:
        print(f"  [apify_linkedin] {source.get('name')}: actor run failed: {e}")
        return []

    items = []
    for raw in client.dataset(run["defaultDatasetId"]).iterate_items():
        posted_at = raw.get("postedAt") or raw.get("publishedAt") or ""
        try:
            dt = datetime.fromisoformat(posted_at.replace("Z", "+00:00")) if posted_at else None
        except Exception:
            dt = None
        if dt and dt < cutoff:
            continue
        text = raw.get("text") or raw.get("content") or ""
        if not text.strip():
            continue
        items.append({
            "title": text.split("\n", 1)[0][:120],   # first line as title
            "url": raw.get("url", profile_url),
            "author": source.get("name", ""),
            "source": source.get("name", "LinkedIn"),
            "date": dt.date().isoformat() if dt else "",
            "summary": text[:1500],
            "full_text": text[:20000],
        })
        if len(items) >= max_items:
            break

    print(f"  [apify_linkedin] {source.get('name')}: {len(items)} post(s)")
    return items


# ── Podchaser — track a named person's podcast guest appearances ─────────

PODCHASER_GRAPHQL = "https://api.podchaser.com/graphql"

def resolve_podchaser_person(source: dict, lookback_days: int, max_items: int) -> list:
    """Find recent episodes where `source.name` was credited (host or guest).

    Requires PODCHASER_TOKEN in env. Free tier: 25k query points/month.
    For each match, returns the episode's title + URL + transcript-or-notes
    body via trafilatura on the episode page.
    """
    token = os.environ.get("PODCHASER_TOKEN")
    if not token:
        print(f"  [podchaser] {source.get('name')}: PODCHASER_TOKEN not set")
        return []

    person_name = source.get("name", "").strip()
    if not person_name:
        return []

    query = """
    query($n: String!, $first: Int!) {
      credits(filters: {searchTerm: $n}, first: $first) {
        data {
          ... on EpisodeCredit {
            role
            episode {
              title
              airDate
              link
              description
              podcast { title }
            }
          }
        }
      }
    }
    """
    try:
        r = requests.post(
            PODCHASER_GRAPHQL,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"query": query, "variables": {"n": person_name, "first": max_items * 2}},
            timeout=30,
        )
        if r.status_code != 200:
            print(f"  [podchaser] {person_name}: HTTP {r.status_code}")
            return []
        data = r.json().get("data", {}).get("credits", {}).get("data", []) or []
    except Exception as e:
        print(f"  [podchaser] {person_name}: query failed: {e}")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    items = []
    for credit in data:
        ep = credit.get("episode") or {}
        air = ep.get("airDate") or ""
        try:
            dt = datetime.fromisoformat(air.replace("Z", "+00:00")) if air else None
        except Exception:
            dt = None
        if dt and dt < cutoff:
            continue
        link = ep.get("link") or ""
        body = _fetch_full_text(link) if link else ""
        items.append({
            "title": ep.get("title", "Untitled episode"),
            "url": link,
            "author": person_name,
            "source": f"{ep.get('podcast', {}).get('title', 'Podcast')} (guest: {person_name})",
            "date": dt.date().isoformat() if dt else "",
            "summary": _strip_html(ep.get("description", ""))[:1500],
            "full_text": body[:20000] or _strip_html(ep.get("description", ""))[:20000],
        })
        if len(items) >= max_items:
            break

    print(f"  [podchaser] {person_name}: {len(items)} appearance(s)")
    return items


def _strip_html(text):
    if not text:
        return ""
    return unescape(re.sub(r"<[^>]+>", "", text)).strip()


def _fetch_full_text(url, timeout=15):
    try:
        import trafilatura
    except ImportError:
        return ""
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
        if r.status_code != 200:
            return ""
        return trafilatura.extract(r.text, include_comments=False, include_tables=False) or ""
    except Exception:
        return ""


# ── Dispatch ─────────────────────────────────────────────────────────────

RESOLVERS = {
    "rss":              resolve_rss,
    "rss_app":          resolve_rss_app,
    "apify_linkedin":   resolve_apify_linkedin,
    "podchaser_person": resolve_podchaser_person,
}


def resolve(source: dict, lookback_days: int, max_items: int) -> list:
    """Dispatch to the right resolver for this source."""
    name = (source.get("resolver") or "rss").lower()
    fn = RESOLVERS.get(name)
    if not fn:
        print(f"  Unknown resolver {name!r} for {source.get('name')} — falling back to plain RSS")
        return resolve_rss(source, lookback_days, max_items)
    return fn(source, lookback_days, max_items)
