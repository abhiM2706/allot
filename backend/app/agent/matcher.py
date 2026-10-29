"""Account matching.

Two layers, on purpose:
1. Deterministic scoring from hard signals (time gap to a calendar event, attendee email domains, title words,
   the rep's memory of past answers, account ownership). This runs always and is fully auditable.
2. When Claude is available, it adjudicates between the top candidates using the same evidence and may lower
   confidence (never raise it above the evidence allows). It also writes the one-line explanation.

The agent tags without asking only when confidence >= AUTO_TAG_THRESHOLD and the lead over the runner-up is clear.
Otherwise it returns up to three options for the rep to pick from by text."""

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime

from ..adapters.calendar import Calendar, CalendarEvent
from ..adapters.crm import CRM, Account
from ..config import settings
from . import llm
from .receipt import Receipt

AUTO_TAG_THRESHOLD = 0.80
CLEAR_LEAD = 0.25


@dataclass
class Candidate:
    account: Account
    score: float
    reasons: list[str] = field(default_factory=list)
    event: CalendarEvent | None = None


@dataclass
class MatchResult:
    account: Account | None
    confidence: float
    evidence: str
    event: CalendarEvent | None
    options: list[Candidate]  # non-empty when the agent needs to ask
    auto_tagged: bool


def _hour(ts: datetime) -> int:
    return ts.hour


def score_candidates(conn: sqlite3.Connection, rep_id: str, receipt: Receipt, when: datetime,
                     crm: CRM, cal: Calendar) -> list[Candidate]:
    by_id: dict[str, Candidate] = {}

    def bump(acc: Account, pts: float, why: str, event: CalendarEvent | None = None):
        c = by_id.setdefault(acc.id, Candidate(acc, 0.0))
        c.score += pts
        c.reasons.append(why)
        if event and c.event is None:
            c.event = event

    events = cal.around(rep_id, when, window_hours=3)
    for ev in events:
        # Distance from the receipt time to the event window. Paying the bill after the event ends is normal.
        if ev.start <= when <= ev.end:
            gap_min = 0.0
        else:
            edge = ev.start if when < ev.start else ev.end
            gap_min = abs((edge - when).total_seconds()) / 60
        time_pts = 0.35 if gap_min <= 90 else 0.2
        # Attendee domains are the strongest signal
        for acc in crm.accounts_for_domains(ev.external_domains):
            bump(acc, 0.45 + time_pts, f"Calendar event “{ev.title}” with attendees from {acc.domain}", ev)
        # Title mentions an account name
        title_l = ev.title.lower()
        for acc in crm.all_accounts():
            first = acc.name.split()[0].lower()
            if first in title_l and acc.id not in {a.id for a in crm.accounts_for_domains(ev.external_domains)}:
                bump(acc, 0.25 + time_pts, f"Calendar event “{ev.title}” names {acc.name}", ev)

    # Rep memory: same merchant around the same hour before
    row = conn.execute("SELECT account_id FROM memory WHERE rep_id=? AND merchant=? AND ABS(hour-?)<=1",
                       (rep_id, receipt.merchant, _hour(when))).fetchone()
    if row:
        acc = crm.get(row["account_id"])
        if acc:
            bump(acc, 0.75, f"You tagged {receipt.merchant} around this time to {acc.name} before")

    # Weak prior: accounts the rep owns
    for acc in crm.accounts_for_rep(rep_id):
        bump(acc, 0.08, "Account owned by this rep")

    cands = sorted(by_id.values(), key=lambda c: -c.score)
    for c in cands:
        c.score = min(c.score, 0.98)
    return cands


LLM_SYSTEM = """You adjudicate which customer account a sales expense belongs to. You get the receipt, the rep's
nearby calendar events, and scored candidates with their evidence. Return JSON:
{"account_id": string or null, "confidence": 0-1, "explanation": one sentence citing the evidence,
 "ask": boolean}. Set ask=true when the evidence does not clearly point to one account. Never set confidence
above the strongest candidate's heuristic score + 0.05. If no candidate fits, account_id null and ask true.
Two rules override your judgement: (1) if a candidate's evidence says the rep tagged this merchant around this time
to that account before, that is the rep's own answer: pick it, ask=false, confidence at least 0.85, unless the receipt
plainly contradicts it (different city, a different company named on it). (2) a calendar event whose external
attendees belong to the candidate's domain is decisive on its own: ask=false."""


def match(conn: sqlite3.Connection, rep_id: str, receipt: Receipt, when: datetime,
          crm: CRM, cal: Calendar) -> MatchResult:
    cands = score_candidates(conn, rep_id, receipt, when, crm, cal)
    if not cands:
        return MatchResult(None, 0.0, "No calendar event or known account near this receipt.", None, [], False)

    top = cands[0]
    runner = cands[1].score if len(cands) > 1 else 0.0
    confidence = top.score
    evidence = "; ".join(top.reasons[:2])
    ask = not (confidence >= AUTO_TAG_THRESHOLD and confidence - runner >= CLEAR_LEAD)

    if settings.llm_enabled:
        try:
            payload = {
                "receipt": receipt.to_dict(),
                "events": [{"title": e.title, "start": e.start.isoformat(), "attendees": e.attendees}
                           for e in cal.around(rep_id, when)],
                "candidates": [{"account_id": c.account.id, "name": c.account.name, "deal_type": c.account.deal_type,
                                "deal_value": c.account.deal_value, "heuristic_score": round(c.score, 2),
                                "evidence": c.reasons} for c in cands[:3]],
            }
            out = llm.ask_json(LLM_SYSTEM, f"Decide.\n{payload}")
            if out.get("account_id") in {c.account.id for c in cands[:3]}:
                chosen = next(c for c in cands if c.account.id == out["account_id"])
                cap = chosen.score + 0.05
                confidence = min(float(out.get("confidence", confidence)), cap)
                evidence = out.get("explanation") or evidence
                ask = bool(out.get("ask", ask)) or confidence < AUTO_TAG_THRESHOLD
                top = chosen
            else:
                ask = True
        except Exception as exc:  # the heuristic result stands if the model call fails
            evidence = evidence + f" (model unavailable: {type(exc).__name__})"

    if ask:
        return MatchResult(None, confidence, evidence, top.event, cands[:3], False)
    return MatchResult(top.account, confidence, evidence, top.event, [], True)


def remember(conn: sqlite3.Connection, rep_id: str, merchant: str, when: datetime, account_id: str) -> None:
    conn.execute("INSERT OR REPLACE INTO memory VALUES (?,?,?,?,?)",
                 (rep_id, merchant, _hour(when), account_id, datetime.now().isoformat()))
    conn.commit()
