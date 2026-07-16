"""Build an Apple/Spotify-compatible podcast RSS feed.

The pipeline calls `add_episode()` after rendering the MP3. The feed is
rebuilt from scratch every run so namespace prefixes stay clean.

If `delivery.s3` is configured the orchestrator uploads the MP3 + feed.xml
afterwards; otherwise the feed sits in `output/podcast/` for the user to
serve however they like.
"""

from __future__ import annotations

import os
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import formatdate
from pathlib import Path


ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ET.register_namespace("itunes", ITUNES_NS)


def _itunes(tag):
    return f"{{{ITUNES_NS}}}{tag}"


def add_episode(mp3_path: str, *, script: str, episode_title: str,
                episode_slug: str, feed_meta: dict, base_url: str) -> tuple:
    """Add this episode to the feed and return (feed_path, episode_url, dated_mp3)."""
    base_url = (base_url or "").rstrip("/")
    output_dir = Path(mp3_path).parent
    feed_dir = output_dir / "podcast"
    feed_dir.mkdir(exist_ok=True)
    feed_path = feed_dir / feed_meta.get("feed_filename", "feed.xml")

    stem = episode_slug or datetime.now().strftime("%Y-%m-%d")
    episode_filename = f"{feed_meta.get('episode_prefix', 'episode')}-{stem}.mp3"
    episode_dest = feed_dir / episode_filename
    shutil.copy2(mp3_path, episode_dest)
    file_size = os.path.getsize(str(episode_dest))

    existing = []
    if feed_path.exists():
        try:
            old_root = ET.parse(str(feed_path)).getroot()
            old_channel = old_root.find("channel")
            if old_channel is not None:
                existing = list(old_channel.findall("item"))
        except ET.ParseError:
            print("  Warning: old feed unparseable, starting fresh")

    root = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(root, "channel")

    ET.SubElement(channel, "title").text = feed_meta.get("title", "Learn Podcast")
    ET.SubElement(channel, "description").text = feed_meta.get("description", "")
    ET.SubElement(channel, "link").text = base_url or ""
    ET.SubElement(channel, "language").text = feed_meta.get("language", "en-us")
    ET.SubElement(channel, "lastBuildDate").text = formatdate(localtime=True)

    ET.SubElement(channel, _itunes("author")).text = feed_meta.get("author", "")
    ET.SubElement(channel, _itunes("type")).text = "episodic"
    ET.SubElement(channel, _itunes("explicit")).text = "false"
    ET.SubElement(channel, _itunes("summary")).text = feed_meta.get("description", "")

    owner = ET.SubElement(channel, _itunes("owner"))
    ET.SubElement(owner, _itunes("name")).text = feed_meta.get("author", "")
    ET.SubElement(owner, _itunes("email")).text = feed_meta.get("email", "")

    cat = ET.SubElement(channel, _itunes("category"))
    cat.set("text", feed_meta.get("category", "Education"))
    sub = feed_meta.get("subcategory")
    if sub:
        ET.SubElement(cat, _itunes("category")).set("text", sub)

    cover = feed_meta.get("cover_image", "cover.png")
    if base_url:
        ET.SubElement(channel, _itunes("image")).set("href", f"{base_url}/{cover}")
        img = ET.SubElement(channel, "image")
        ET.SubElement(img, "url").text = f"{base_url}/{cover}"
        ET.SubElement(img, "title").text = feed_meta.get("title", "Learn Podcast")
        ET.SubElement(img, "link").text = base_url

    episode_url = f"{base_url}/{episode_filename}" if base_url else episode_filename
    if not any(_episode_matches(it, episode_filename) for it in existing):
        channel.append(_new_item(episode_url, file_size, script, episode_title))
        print(f"  Episode added: {episode_filename} ({file_size / 1024:.0f} KB)")

    for old in existing:
        if old.find("title") is None:
            continue
        channel.append(old)

    for stale in channel.findall("item")[30:]:
        channel.remove(stale)

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(str(feed_path), xml_declaration=True, encoding="utf-8")
    print(f"  Feed updated: {feed_path}")
    return str(feed_path), episode_url, str(episode_dest)


def _episode_matches(item, filename):
    guid = item.find("guid")
    return guid is not None and guid.text and filename in guid.text


def _new_item(episode_url, file_size, script, episode_title):
    item = ET.Element("item")
    ET.SubElement(item, "title").text = episode_title
    desc = (script[:500] + "…") if len(script) > 500 else script
    ET.SubElement(item, "description").text = desc

    enc = ET.SubElement(item, "enclosure")
    enc.set("url", episode_url)
    enc.set("length", str(file_size))
    enc.set("type", "audio/mpeg")

    guid = ET.SubElement(item, "guid")
    guid.set("isPermaLink", "true")
    guid.text = episode_url
    ET.SubElement(item, "pubDate").text = formatdate(localtime=True)
    ET.SubElement(item, _itunes("summary")).text = desc
    ET.SubElement(item, _itunes("episodeType")).text = "full"

    estimated_seconds = max(60, int(len(script) / 5 / 150 * 60))
    ET.SubElement(item, _itunes("duration")).text = (
        f"{estimated_seconds // 60}:{estimated_seconds % 60:02d}"
    )
    return item
