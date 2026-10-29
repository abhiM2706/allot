"""Receipt reading. Claude's vision reads the photo; the mock path parses a sidecar JSON next to fixture images
or the hints passed by the simulator, so the pipeline runs end to end without an API key."""

import json
from dataclasses import dataclass, asdict
from datetime import datetime

from ..config import settings
from . import llm

SYSTEM = """You read receipt photos for an expense tool. Return only JSON with keys:
merchant (string), total (number), currency (string, ISO), occurred_at (ISO 8601 with offset if printed, else null),
city (string or null), guest_count (integer or null, from 'guests', 'covers', or number of entrees), items (array of
{name, amount}), confidence (0-1). Never invent a total; if unreadable, set total to null and confidence under 0.3."""


@dataclass
class Receipt:
    merchant: str
    total: float | None
    currency: str = "USD"
    occurred_at: str | None = None
    city: str | None = None
    guest_count: int | None = None
    items: list[dict] | None = None
    confidence: float = 1.0

    def to_dict(self):
        return asdict(self)


def read_receipt(image: bytes | None, media_type: str = "image/jpeg", hints: dict | None = None,
                 now: datetime | None = None) -> Receipt:
    """`hints` lets the simulator (and tests) pass known fields. The live path uses the model."""
    hints = hints or {}
    if image is not None and settings.llm_enabled:
        out = llm.ask_json(SYSTEM, "Read this receipt.", image=image, image_media_type=media_type)
        return Receipt(
            merchant=out.get("merchant") or hints.get("merchant") or "Unknown merchant",
            total=out.get("total") if out.get("total") is not None else hints.get("total"),
            currency=out.get("currency") or "USD",
            occurred_at=out.get("occurred_at") or hints.get("occurred_at") or (now or datetime.now()).isoformat(),
            city=out.get("city") or hints.get("city"),
            guest_count=out.get("guest_count") or hints.get("guest_count"),
            items=out.get("items") or [],
            confidence=float(out.get("confidence", 0.8)),
        )
    # Mock / hint path
    return Receipt(
        merchant=hints.get("merchant", "Unknown merchant"),
        total=hints.get("total"),
        occurred_at=hints.get("occurred_at") or (now or datetime.now()).isoformat(),
        city=hints.get("city"),
        guest_count=hints.get("guest_count"),
        items=hints.get("items", []),
        confidence=0.95 if hints.get("total") is not None else 0.2,
    )


def sidecar_hints(image_path) -> dict:
    """Fixture receipts ship with a .json sidecar so the mock path knows what the photo says."""
    p = image_path.with_suffix(".json")
    return json.loads(p.read_text()) if p.exists() else {}
