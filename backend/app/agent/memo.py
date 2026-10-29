"""Memo drafting: one line, from the event title, attendees and receipt. Claude when available, template otherwise."""

from ..adapters.calendar import CalendarEvent
from ..adapters.crm import Account
from ..config import settings
from . import llm
from .receipt import Receipt

SYSTEM = """Write a one-line expense memo a finance team would accept, max 10 words, in this shape:
"<Purpose> with <account short name>[, <N> attendees]". Purpose is dinner, lunch, coffee, flight, hotel, or ground
transport. Use the calendar event title to sharpen the purpose (e.g. "Renewal dinner"). No amount, no city, no
merchant name, no parentheses, no trailing period. Return JSON {"memo": string}."""


def draft_memo(receipt: Receipt, account: Account, event: CalendarEvent | None, attendees: str | None) -> str:
    kind = _kind(receipt)
    if settings.llm_enabled:
        try:
            out = llm.ask_json(SYSTEM, f"Receipt: {receipt.to_dict()}\nAccount: {account.name} ({account.deal_type})\n"
                                       f"Calendar event: {event.title if event else 'none'}\nAttendees: {attendees or 'unknown'}")
            if out.get("memo"):
                return out["memo"].strip().rstrip(".")
        except Exception:
            pass
    n = _count(attendees) or receipt.guest_count
    tail = f", {n} attendees" if n else ""
    purpose = event.title if event else kind.capitalize()
    purpose = purpose.replace(" - ", " with ")
    if account.name.split()[0].lower() not in purpose.lower():
        purpose = f"{kind.capitalize()} with {account.name}"
    return f"{purpose}{tail}"


def _kind(r: Receipt) -> str:
    m = (r.merchant or "").lower()
    if any(w in m for w in ["coffee", "cafe", "café", "blue bottle", "blue door"]):
        return "coffee"
    if any(w in m for w in ["airlines", "united", "delta", "southwest", "flight"]):
        return "flight"
    if any(w in m for w in ["lyft", "uber", "taxi", "parking"]):
        return "ground transport"
    if any(w in m for w in ["hotel", "inn", "marriott", "hyatt"]):
        return "hotel"
    return "dinner" if (r.occurred_at and int(r.occurred_at[11:13] or 12) >= 17) else "meal"


def _count(attendees: str | None) -> int | None:
    if not attendees:
        return None
    parts = [p for p in attendees.replace(" and ", ",").split(",") if p.strip()]
    return len(parts) or None
