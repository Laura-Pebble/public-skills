"""Text → MP3 via Microsoft Edge TTS (free, no API key)."""

from __future__ import annotations

import asyncio
import os


FALLBACK_VOICES = ["en-US-AriaNeural", "en-US-GuyNeural", "en-US-JennyNeural"]


async def _generate(text: str, voice: str, output_path: str) -> None:
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def text_to_mp3(script: str, *, voice: str, output_path: str) -> str:
    """Render `script` to `output_path`. Falls through a few voices on failure."""
    if not script.strip():
        raise ValueError("Empty script — nothing to convert to speech")

    voices = [voice] + [v for v in FALLBACK_VOICES if v != voice]
    last_err = None

    for v in voices:
        try:
            print(f"  Generating audio with voice: {v}")
            asyncio.run(_generate(script, v, output_path))
            size = os.path.getsize(output_path)
            if size < 1000:
                raise ValueError("Audio file too small — likely empty")
            print(f"  Audio saved: {output_path} ({size / (1024 * 1024):.1f} MB)")
            return output_path
        except Exception as e:
            print(f"  Voice {v} failed: {e}")
            last_err = e

    raise RuntimeError(f"All TTS voices failed: {voices} (last error: {last_err})")
