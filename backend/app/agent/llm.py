"""Thin wrapper around the Anthropic API. Every call asks for JSON and parses it.
If the provider is 'mock' or no key is set, callers fall back to deterministic logic."""

import base64
import json
import re

from ..config import settings

_client = None


def client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def _extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError(f"No JSON in model output: {text[:200]}")
    return json.loads(m.group(0))


def ask_json(system: str, user_text: str, image: bytes | None = None, image_media_type: str = "image/jpeg",
             max_tokens: int = 800) -> dict:
    content: list[dict] = []
    if image is not None:
        content.append({"type": "image", "source": {"type": "base64", "media_type": image_media_type,
                                                    "data": base64.b64encode(image).decode()}})
    content.append({"type": "text", "text": user_text})
    msg = client().messages.create(model=settings.anthropic_model, max_tokens=max_tokens, system=system,
                                   messages=[{"role": "user", "content": content}])
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    return _extract_json(text)
