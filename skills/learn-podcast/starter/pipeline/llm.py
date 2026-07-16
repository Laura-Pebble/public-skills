"""LLM provider abstraction — Anthropic / Gemini / OpenAI.

One call: `complete(prompt, max_tokens=...)` returns a string. The provider is
picked from `config.yaml`'s `llm.provider` field, and the matching API key
must be in the environment.
"""

from __future__ import annotations

import os
from typing import Optional


class LLMError(RuntimeError):
    pass


def complete(prompt: str, *, provider: str, model: Optional[str] = None,
             max_tokens: int = 8000, temperature: float = 0.7) -> str:
    """Return the model's text completion for `prompt`.

    Raises LLMError if the provider library is missing, the API key is unset,
    or the call fails after one retry on a smaller model.
    """
    provider = (provider or "").lower()
    if provider == "anthropic":
        return _anthropic(prompt, model or "claude-sonnet-4-6", max_tokens, temperature)
    if provider == "gemini":
        return _gemini(prompt, model or "gemini-2.5-pro", max_tokens, temperature)
    if provider == "openai":
        return _openai(prompt, model or "gpt-4o", max_tokens, temperature)
    raise LLMError(f"Unknown provider: {provider!r}. Set llm.provider in config.yaml to anthropic, gemini, or openai.")


def _anthropic(prompt, model, max_tokens, temperature):
    try:
        from anthropic import Anthropic
    except ImportError as e:
        raise LLMError("anthropic SDK not installed — `pip install anthropic`") from e
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise LLMError("ANTHROPIC_API_KEY not set")
    client = Anthropic(api_key=key)
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    except Exception as e:
        # Retry once on Haiku if Sonnet fails
        if "haiku" not in model:
            print(f"  Claude {model} failed ({e}) — retrying on Haiku")
            return _anthropic(prompt, "claude-haiku-4-5", max_tokens, temperature)
        raise LLMError(f"Anthropic call failed: {e}") from e


def _gemini(prompt, model, max_tokens, temperature):
    try:
        from google import genai
    except ImportError as e:
        raise LLMError("google-genai SDK not installed — `pip install google-genai`") from e
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise LLMError("GEMINI_API_KEY not set")
    client = genai.Client(api_key=key)
    try:
        resp = client.models.generate_content(
            model=model,
            contents=prompt,
            config={"max_output_tokens": max_tokens, "temperature": temperature},
        )
        return (resp.text or "").strip()
    except Exception as e:
        if "flash" not in model:
            print(f"  Gemini {model} failed ({e}) — retrying on Flash")
            return _gemini(prompt, "gemini-2.5-flash", max_tokens, temperature)
        raise LLMError(f"Gemini call failed: {e}") from e


def _openai(prompt, model, max_tokens, temperature):
    try:
        from openai import OpenAI
    except ImportError as e:
        raise LLMError("openai SDK not installed — `pip install openai`") from e
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise LLMError("OPENAI_API_KEY not set")
    client = OpenAI(api_key=key)
    try:
        resp = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        if model != "gpt-4o-mini":
            print(f"  OpenAI {model} failed ({e}) — retrying on gpt-4o-mini")
            return _openai(prompt, "gpt-4o-mini", max_tokens, temperature)
        raise LLMError(f"OpenAI call failed: {e}") from e
