"""Push notification + S3 upload — both optional, both gated on config."""

from __future__ import annotations

import os
from pathlib import Path

import requests


def push_ntfy(topic: str, *, episode_url: str, script: str) -> None:
    """Send a push notification via ntfy.sh — no account needed."""
    if not topic:
        return
    preview = (script or "").strip().split("\n")[0][:200]
    body = f"New episode ready.\n{preview}"
    if episode_url:
        body += f"\n\n{episode_url}"
    try:
        requests.post(
            f"https://ntfy.sh/{topic}",
            data=body.encode("utf-8"),
            headers={"Title": "Learn Podcast", "Priority": "default"},
            timeout=10,
        )
        print(f"  ntfy notification sent → {topic}")
    except Exception as e:
        print(f"  ntfy failed: {e}")


def upload_s3(paths: list, *, bucket: str, endpoint: str, access_key: str,
              secret_key: str, public_url: str) -> dict:
    """Upload each file to S3-compatible storage; return {path: public_url}.

    Works with Cloudflare R2, AWS S3, Backblaze B2 — anything boto3 speaks to.
    """
    if not (bucket and endpoint and access_key and secret_key):
        print("  S3 not configured — skipping upload")
        return {}
    try:
        import boto3
    except ImportError:
        print("  boto3 not installed — `pip install boto3` to enable feed hosting")
        return {}

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

    out = {}
    base = (public_url or "").rstrip("/")
    for p in paths:
        p = Path(p)
        if not p.exists():
            continue
        key = p.name
        content_type = {
            ".mp3": "audio/mpeg",
            ".xml": "application/rss+xml",
            ".png": "image/png",
            ".jpg": "image/jpeg",
        }.get(p.suffix.lower(), "application/octet-stream")
        try:
            s3.upload_file(
                str(p), bucket, key,
                ExtraArgs={"ContentType": content_type, "ACL": "public-read"},
            )
            url = f"{base}/{key}" if base else f"{endpoint.rstrip('/')}/{bucket}/{key}"
            out[str(p)] = url
            print(f"  Uploaded {key}")
        except Exception as e:
            print(f"  Upload failed for {p.name}: {e}")
    return out
