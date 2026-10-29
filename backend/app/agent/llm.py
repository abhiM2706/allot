"""Thin wrapper around Claude, via Amazon Bedrock or the Anthropic API. Every call asks for JSON and parses it.
If the provider is 'mock' or no credentials are set, callers fall back to deterministic logic."""

import base64
import json
import re

from ..config import settings

_client = None


def client():
    global _client
    if _client is None:
        if settings.provider == "bedrock":
            from anthropic import AnthropicBedrock
            kwargs = {"aws_region": settings.aws_region}
            if settings.aws_bearer_token_bedrock:
                kwargs["api_key"] = settings.aws_bearer_token_bedrock
            elif settings.aws_access_key_id and settings.aws_secret_access_key:
                kwargs.update(aws_access_key=settings.aws_access_key_id, aws_secret_key=settings.aws_secret_access_key,
                              aws_session_token=settings.aws_session_token)
            # otherwise the SDK uses the default AWS credential chain (env vars, ~/.aws, instance role)
            _client = AnthropicBedrock(**kwargs)
        else:
            import anthropic
            _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def model() -> str:
    return settings.model_label


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
    msg = client().messages.create(model=model(), max_tokens=max_tokens, system=system,
                                   messages=[{"role": "user", "content": content}])
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    return _extract_json(text)
