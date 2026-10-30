"""The SMS agent's conversation state machine. One thread per rep.

idle ──photo──▶ read receipt ──▶ match
    confident: tag, ask "who joined you?"           ──▶ awaiting_attendees ──reply──▶ memo, route, done
    unsure:    ask "which account?" (≤3 options)   ──▶ awaiting_account   ──reply──▶ tag, memo, route, done
"""

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from ..adapters.calendar import Calendar
from ..adapters.crm import CRM
from ..adapters.sms import send_sms
from ..db import cursor, get_rules
from .. import rules as R
from .matcher import match, remember
from .memo import draft_memo
from .receipt import Receipt, read_receipt

MANAGER_NAME = "Priya"


@dataclass
class Reply:
    body: str
    card: dict | None = None  # structured bits the simulator renders (account, memo, options)


@dataclass
class Turn:
    replies: list[Reply] = field(default_factory=list)
    expense_id: str | None = None
    state: str = "idle"


def _state(conn, rep_id) -> dict:
    r = conn.execute("SELECT state_json FROM thread_state WHERE rep_id=?", (rep_id,)).fetchone()
    return json.loads(r["state_json"]) if r else {"name": "idle"}


def _set_state(conn, rep_id, state: dict):
    conn.execute("INSERT OR REPLACE INTO thread_state VALUES (?,?)", (rep_id, json.dumps(state)))
    conn.commit()


def _log(conn, rep_id, direction, body, media_url=None, payload=None):
    conn.execute("INSERT INTO thread_message (rep_id, direction, body, media_url, payload_json, created_at) VALUES (?,?,?,?,?,?)",
                 (rep_id, direction, body, media_url, json.dumps(payload) if payload else None, datetime.now().isoformat()))
    conn.commit()


def _clock(dt: datetime) -> str:
    return dt.strftime('%-I %p') if dt.minute == 0 else dt.strftime('%-I:%M %p')


def _money(x: float) -> str:
    return f"${x:,.2f}"


def _k(x: float) -> str:
    return f"${x/1000:.0f}K" if x >= 1000 else f"${x:,.0f}"


def _rep_phone(rep_id: str) -> str | None:
    from ..config import FIXTURES_DIR
    people = json.loads((FIXTURES_DIR / "people.json").read_text())
    for r in people["reps"]:
        if r["id"] == rep_id:
            return r["phone"]
    return None


def handle_inbound(conn: sqlite3.Connection, rep_id: str, text: str | None = None, image: bytes | None = None,
                   media_type: str = "image/jpeg", media_url: str | None = None, hints: dict | None = None,
                   now: datetime | None = None, deliver: bool = False, thread_id: str | None = None) -> Turn:
    """Process one inbound message. `thread_id` separates conversations that share a rep persona (demo guests).
    `deliver=True` also sends replies over SMS (Twilio path)."""
    crm, cal = CRM(conn), Calendar()
    tid = thread_id or rep_id
    state = _state(conn, tid)
    _log(conn, tid, "in", text or "", media_url, {"hints": hints} if hints else None)
    turn = Turn()

    if image is not None or (hints and hints.get("merchant")):
        turn = _on_receipt(conn, rep_id, image, media_type, hints or {}, now, crm, cal, tid)
    elif state["name"] == "awaiting_attendees":
        turn = _on_attendees(conn, rep_id, state, text or "", crm, cal, tid)
    elif state["name"] == "awaiting_account":
        turn = _on_account_choice(conn, rep_id, state, text or "", crm, cal, tid)
    else:
        turn.replies.append(Reply("Text me a photo of a receipt and I’ll log it, tag the customer, and send it for approval."))

    for r in turn.replies:
        _log(conn, tid, "out", r.body, None, r.card)
        if deliver:
            phone = _rep_phone(rep_id)
            if phone:
                send_sms(phone, r.body)
    return turn


def _on_receipt(conn, rep_id, image, media_type, hints, now, crm, cal, tid=None) -> Turn:
    tid = tid or rep_id
    turn = Turn()
    receipt: Receipt = read_receipt(image, media_type, hints, now)
    when = datetime.fromisoformat(receipt.occurred_at) if receipt.occurred_at else (now or datetime.now())
    if when.tzinfo is None:
        # The receipt prints local time. Use the timezone of the rep's calendar events that day; else this machine's.
        same_day = [e for e in cal.events if e.rep_id == rep_id and e.start.date() == when.date()]
        tz = same_day[0].start.tzinfo if same_day else datetime.now().astimezone().tzinfo
        when = when.replace(tzinfo=tz)
        receipt.occurred_at = when.isoformat()

    if receipt.total is None:
        turn.replies.append(Reply("I couldn’t read a total on that one. Can you send a clearer photo, or text me the amount?"))
        return turn

    exp_id = f"exp_{uuid.uuid4().hex[:8]}"
    with cursor(conn) as cur:
        cur.execute(
            "INSERT INTO expense (id, rep_id, merchant, amount, occurred_at, city, items_json, guest_count, status, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (exp_id, rep_id, receipt.merchant, receipt.total, when.isoformat(), receipt.city,
             json.dumps(receipt.items or []), receipt.guest_count, "draft", datetime.now().isoformat()))
    turn.expense_id = exp_id

    res = match(conn, rep_id, receipt, when, crm, cal)

    if res.auto_tagged and res.account:
        acc = res.account
        with cursor(conn) as cur:
            cur.execute("UPDATE expense SET account_id=?, match_confidence=?, match_evidence=? WHERE id=?",
                        (acc.id, res.confidence, res.evidence, exp_id))
        ev_bit = f"Your {res.event.start.strftime('%-I %p')} event is “{res.event.title}”, and " if res.event else ""
        body = (f"Got it: {_money(receipt.total)} at {receipt.merchant}. {ev_bit}{acc.name} has an open "
                f"{_k(acc.deal_value)} {acc.deal_type.lower()}. Tagging it there. Who joined you?")
        turn.replies.append(Reply(body, {"kind": "tagged", "account": acc.name, "confidence": round(res.confidence, 2),
                                         "evidence": res.evidence}))
        _set_state(conn, tid, {"name": "awaiting_attendees", "expense_id": exp_id, "event_id": res.event.id if res.event else None})
        turn.state = "awaiting_attendees"
        return turn

    # Need to ask. Build options: top candidates, else the rep's own accounts.
    opts = [c.account for c in res.options] or crm.accounts_for_rep(rep_id)[:2]
    option_rows = [{"n": i + 1, "account_id": a.id, "label": f"{a.name}, {a.deal_type.lower()}, {_k(a.deal_value)}"}
                   for i, a in enumerate(opts[:2 if len(opts) > 2 else len(opts)])]
    option_rows.append({"n": len(option_rows) + 1, "account_id": None, "label": "Not a customer expense"})
    why = res.evidence if res.options else "I don’t see a calendar event or a known account near this receipt."
    nearby = cal.around(rep_id, when)
    if nearby and not any(e.external_domains for e in nearby):
        why = f"I see {len(nearby)} meeting{'s' if len(nearby) != 1 else ''} around {when.strftime('%-I %p')} and no attendees on {'either' if len(nearby) == 2 else 'them' if len(nearby) > 1 else 'it'}."
    body = f"{_money(receipt.total)} at {receipt.merchant}. {why} Which account was this for?\n" + \
           "\n".join(f"{o['n']}. {o['label']}" for o in option_rows)
    turn.replies.append(Reply(body, {"kind": "ask_account", "options": option_rows, "confidence": round(res.confidence, 2)}))
    _set_state(conn, tid, {"name": "awaiting_account", "expense_id": exp_id, "options": option_rows,
                              "event_id": res.event.id if res.event else None})
    turn.state = "awaiting_account"
    return turn


def _on_account_choice(conn, rep_id, state, text, crm, cal, tid=None) -> Turn:
    tid = tid or rep_id
    turn = Turn(expense_id=state["expense_id"])
    choice = None
    t = text.strip().lower()
    for o in state["options"]:
        if t == str(o["n"]) or (o["account_id"] and crm.get(o["account_id"]).name.split()[0].lower() in t):
            choice = o
            break
    if choice is None:
        turn.replies.append(Reply("Reply with 1, 2 or 3 and I’ll take it from there."))
        turn.state = "awaiting_account"
        return turn

    exp = conn.execute("SELECT * FROM expense WHERE id=?", (state["expense_id"],)).fetchone()
    when = datetime.fromisoformat(exp["occurred_at"])
    if choice["account_id"] is None:
        with cursor(conn) as cur:
            cur.execute("UPDATE expense SET status='personal', memo='Not a customer expense' WHERE id=?", (exp["id"],))
        _set_state(conn, tid, {"name": "idle"})
        turn.replies.append(Reply("Noted. I’ll leave it untagged for you to handle in Ramp."))
        return turn

    acc = crm.get(choice["account_id"])
    remember(conn, rep_id, exp["merchant"], when, acc.id)
    receipt = Receipt(exp["merchant"], exp["amount"], occurred_at=exp["occurred_at"], city=exp["city"],
                      guest_count=exp["guest_count"])
    event = next((e for e in cal.events if e.id == state.get("event_id")), None)
    memo = draft_memo(receipt, acc, event, None)
    evidence = f"Rep picked {acc.name} from {len(state['options'])} options"
    with cursor(conn) as cur:
        cur.execute("UPDATE expense SET account_id=?, memo=?, match_confidence=1.0, match_evidence=? WHERE id=?",
                    (acc.id, memo, evidence, exp["id"]))
    status = _route(conn, exp["id"], acc, exp["amount"])
    hour = when.strftime('%-I %p')
    body = (f"{acc.name} it is. I’ll remember that {hour} visits to {exp['merchant']} are usually {acc.name.split()[0]}. "
            f"Memo: “{memo}.” {_routed_text(status)}")
    turn.replies.append(Reply(body, {"kind": "done", "account": acc.name, "memo": memo, "status": status}))
    _set_state(conn, tid, {"name": "idle"})
    return turn


def _on_attendees(conn, rep_id, state, text, crm, cal, tid=None) -> Turn:
    tid = tid or rep_id
    turn = Turn(expense_id=state["expense_id"])
    exp = conn.execute("SELECT * FROM expense WHERE id=?", (state["expense_id"],)).fetchone()
    acc = crm.get(exp["account_id"])
    event = next((e for e in cal.events if e.id == state.get("event_id")), None)
    receipt = Receipt(exp["merchant"], exp["amount"], occurred_at=exp["occurred_at"], city=exp["city"],
                      guest_count=exp["guest_count"])
    attendees = text.strip() or None
    memo = draft_memo(receipt, acc, event, attendees)
    with cursor(conn) as cur:
        cur.execute("UPDATE expense SET memo=?, attendees=? WHERE id=?", (memo, attendees, exp["id"]))
    remember(conn, rep_id, exp["merchant"], datetime.fromisoformat(exp["occurred_at"]), acc.id)
    status = _route(conn, exp["id"], acc, exp["amount"])
    body = f"Done. {_routed_text(status)}"
    turn.replies.append(Reply(body, {"kind": "done", "account": acc.name, "memo": memo, "status": status}))
    _set_state(conn, tid, {"name": "idle"})
    return turn


def _route(conn, exp_id: str, acc, amount: float) -> str:
    rules = get_rules(conn)
    st = R.standing(conn, acc, rules)  # includes this expense: it is in 'draft', so recompute with it counted
    st_with = R.AccountStanding(acc.id, st.te_to_date + amount, acc.deal_value,
                                (st.te_to_date + amount) / acc.deal_value if acc.deal_value else 0, st.limit,
                                ((st.te_to_date + amount) / acc.deal_value if acc.deal_value else 0) > st.limit,
                                st.expense_count + 1)
    if R.auto_approve(amount, st_with, rules):
        status, by = "approved", "agent"
    else:
        status, by = "pending", None
    with cursor(conn) as cur:
        cur.execute("UPDATE expense SET status=?, approved_by=? WHERE id=?", (status, by, exp_id))
    R.refresh_flag(conn, acc, R.standing(conn, acc, rules))
    conn.execute("INSERT INTO activity (account_id, at, text) VALUES (?,?,?)",
                 (acc.id, datetime.now().isoformat(), f"Logged {_money(amount)}, {'auto-approved' if status == 'approved' else 'sent to ' + MANAGER_NAME}"))
    conn.commit()
    return status


def _routed_text(status: str) -> str:
    return "Logged and approved, it was under the routine limit." if status == "approved" \
        else f"Logged and sent to {MANAGER_NAME} for approval."
