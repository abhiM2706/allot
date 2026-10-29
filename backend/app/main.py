"""Tabbed API. FastAPI over SQLite. Routers are grouped by who uses them: rep (SMS), manager, finance, admin."""

import json
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import rules as R
from .adapters.crm import CRM
from .agent.conversation import handle_inbound
from .agent.receipt import sidecar_hints
from .config import FIXTURES_DIR, settings
from .db import connect, cursor, get_rules, init_db, set_rules

app = FastAPI(title="Tabbed", version="0.1.0", description="T&E tied to the customer it was for.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins + ["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/fixtures/receipts", StaticFiles(directory=FIXTURES_DIR / "receipts"), name="receipts")

_conn = connect()
init_db(_conn)


def db():
    return _conn


PEOPLE = json.loads((FIXTURES_DIR / "people.json").read_text())
REP_BY_PHONE = {r["phone"]: r["id"] for r in PEOPLE["reps"]}
REP_NAME = {r["id"]: r["name"] for r in PEOPLE["reps"]}


def _rows(rs):
    return [dict(r) for r in rs]


# ---------- Rep: SMS ----------

class SimulateIn(BaseModel):
    rep_id: str
    text: str | None = None
    receipt: str | None = None  # a fixture receipt filename, e.g. harbor_table.jpg
    hints: dict | None = None


@app.get("/reps")
def reps():
    return PEOPLE


@app.get("/fixtures")
def fixtures():
    out = []
    for p in sorted((FIXTURES_DIR / "receipts").glob("*.jpg")):
        h = sidecar_hints(p)
        out.append({"file": p.name, "url": f"/fixtures/receipts/{p.name}", **h})
    return sorted(out, key=lambda x: x.get("order", 99))


@app.post("/sms/simulate")
def simulate(body: SimulateIn, conn=Depends(db)):
    """The in-browser phone. Same handler as the Twilio webhook, no delivery."""
    image = None
    hints = body.hints
    media_url = None
    if body.receipt:
        p = FIXTURES_DIR / "receipts" / body.receipt
        if not p.exists():
            raise HTTPException(404, "unknown fixture receipt")
        image = p.read_bytes()
        hints = {**sidecar_hints(p), **(hints or {})}
        media_url = f"/fixtures/receipts/{body.receipt}"
    turn = handle_inbound(conn, body.rep_id, body.text, image, "image/jpeg", media_url, hints)
    return {"state": turn.state, "expense_id": turn.expense_id,
            "replies": [{"body": r.body, "card": r.card} for r in turn.replies]}


@app.post("/sms/upload")
async def simulate_upload(rep_id: str = Form(...), file: UploadFile = File(...), conn=Depends(db)):
    """Upload any receipt photo from the browser. Needs the Anthropic key to read it."""
    data = await file.read()
    turn = handle_inbound(conn, rep_id, None, data, file.content_type or "image/jpeg", None, {})
    return {"state": turn.state, "expense_id": turn.expense_id,
            "replies": [{"body": r.body, "card": r.card} for r in turn.replies]}


@app.post("/sms/twilio")
async def twilio_webhook(request: Request, conn=Depends(db)):
    """Twilio inbound webhook. Point your number's messaging webhook here (POST)."""
    form = await request.form()
    frm = form.get("From", "")
    rep_id = REP_BY_PHONE.get(frm)
    if not rep_id:
        return Response(_twiml("This number isn’t set up with Tabbed yet."), media_type="application/xml")
    image, mtype = None, "image/jpeg"
    if int(form.get("NumMedia", "0") or 0) > 0:
        url, mtype = form.get("MediaUrl0"), form.get("MediaContentType0", "image/jpeg")
        auth = (settings.twilio_account_sid, settings.twilio_auth_token) if settings.twilio_account_sid else None
        image = httpx.get(url, auth=auth, follow_redirects=True, timeout=20).content
    turn = handle_inbound(conn, rep_id, form.get("Body"), image, mtype, form.get("MediaUrl0"), {})
    return Response(_twiml(*[r.body for r in turn.replies]), media_type="application/xml")


def _twiml(*bodies: str) -> str:
    inner = "".join(f"<Message>{_x(b)}</Message>" for b in bodies)
    return f'<?xml version="1.0" encoding="UTF-8"?><Response>{inner}</Response>'


def _x(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@app.get("/thread/{rep_id}")
def thread(rep_id: str, conn=Depends(db)):
    rows = _rows(conn.execute("SELECT * FROM thread_message WHERE rep_id=? ORDER BY id", (rep_id,)))
    for r in rows:
        r["payload"] = json.loads(r.pop("payload_json")) if r.get("payload_json") else None
    return rows


@app.post("/thread/{rep_id}/reset")
def thread_reset(rep_id: str, conn=Depends(db)):
    with cursor(conn) as cur:
        cur.execute("DELETE FROM thread_message WHERE rep_id=?", (rep_id,))
        cur.execute("DELETE FROM thread_state WHERE rep_id=?", (rep_id,))
    return {"ok": True}


@app.get("/rep/{rep_id}/summary")
def rep_summary(rep_id: str, conn=Depends(db)):
    crm, rules = CRM(conn), get_rules(conn)
    recent = _rows(conn.execute(
        "SELECT e.*, a.name account_name FROM expense e LEFT JOIN account a ON a.id=e.account_id "
        "WHERE e.rep_id=? AND e.status!='draft' ORDER BY e.created_at DESC LIMIT 5", (rep_id,)))
    accounts = []
    for a in crm.accounts_for_rep(rep_id) + [a for a in crm.all_accounts() if a.owner_rep_id != rep_id and
                                              conn.execute("SELECT 1 FROM expense WHERE rep_id=? AND account_id=?", (rep_id, a.id)).fetchone()]:
        st = R.standing(conn, a, rules)
        accounts.append({"id": a.id, "name": a.name, "deal_value": a.deal_value, "te": st.te_to_date,
                         "ratio": st.ratio, "limit": st.limit, "over_limit": st.over_limit})
    questions = _rows(conn.execute(
        "SELECT * FROM thread_message WHERE rep_id=? AND direction='finance' ORDER BY id DESC LIMIT 1", (rep_id,)))
    return {"rep": {"id": rep_id, "name": REP_NAME.get(rep_id)}, "recent": recent, "accounts": accounts,
            "finance_question": questions[0] if questions else None}


# ---------- Manager ----------

@app.get("/approvals")
def approvals(conn=Depends(db)):
    rules, crm = get_rules(conn), CRM(conn)

    def enrich(rows):
        out = []
        for e in rows:
            acc = crm.get(e["account_id"]) if e["account_id"] else None
            st = R.standing(conn, acc, rules) if acc else None
            out.append({**e, "rep_name": REP_NAME.get(e["rep_id"]), "account_name": acc.name if acc else None,
                        "deal_type": acc.deal_type if acc else None, "deal_value": acc.deal_value if acc else None,
                        "ratio": st.ratio if st else None, "limit": st.limit if st else None,
                        "over_limit": st.over_limit if st else False, "te_to_date": st.te_to_date if st else None})
        return out

    pending = enrich(_rows(conn.execute("SELECT * FROM expense WHERE status='pending' ORDER BY created_at DESC")))
    approved = enrich(_rows(conn.execute(
        "SELECT * FROM expense WHERE status='approved' AND (approved_by='agent' OR date(created_at)=date('now')) ORDER BY created_at DESC LIMIT 5")))
    return {"pending": pending, "approved_today": approved, "rules": {"auto_approve_under": rules["auto_approve_under"]}}


@app.get("/expenses/{exp_id}")
def expense(exp_id: str, conn=Depends(db)):
    e = conn.execute("SELECT * FROM expense WHERE id=?", (exp_id,)).fetchone()
    if not e:
        raise HTTPException(404)
    e = dict(e)
    crm, rules = CRM(conn), get_rules(conn)
    acc = crm.get(e["account_id"]) if e["account_id"] else None
    st = R.standing(conn, acc, rules) if acc else None
    return {**e, "rep_name": REP_NAME.get(e["rep_id"]), "items": json.loads(e.pop("items_json") or "[]"),
            "account": acc.__dict__ if acc else None,
            "standing": st.__dict__ if st else None}


class Decision(BaseModel):
    question: str | None = None


@app.post("/expenses/{exp_id}/approve")
def approve(exp_id: str, conn=Depends(db)):
    with cursor(conn) as cur:
        cur.execute("UPDATE expense SET status='approved', approved_by='mgr_priya' WHERE id=? AND status='pending'", (exp_id,))
    e = conn.execute("SELECT * FROM expense WHERE id=?", (exp_id,)).fetchone()
    if e and e["account_id"]:
        acc = CRM(conn).get(e["account_id"])
        R.refresh_flag(conn, acc, R.standing(conn, acc))
        conn.execute("INSERT INTO activity (account_id, at, text) VALUES (?,?,?)",
                     (acc.id, datetime.now().isoformat(), f"{REP_NAME.get(e['rep_id'])} logged ${e['amount']:,.0f}, approved by Priya"))
        conn.commit()
    return {"ok": True, "status": e["status"] if e else None}


@app.post("/expenses/{exp_id}/question")
def ask_rep_about_expense(exp_id: str, body: Decision, conn=Depends(db)):
    e = conn.execute("SELECT * FROM expense WHERE id=?", (exp_id,)).fetchone()
    if not e:
        raise HTTPException(404)
    text = body.question or f"Quick one on your {e['merchant']} expense: what was this for?"
    conn.execute("INSERT INTO thread_message (rep_id, direction, body, created_at) VALUES (?,?,?,?)",
                 (e["rep_id"], "manager", text, datetime.now().isoformat()))
    conn.commit()
    return {"ok": True}


# ---------- Finance ----------

@app.get("/accounts")
def accounts(conn=Depends(db)):
    crm, rules = CRM(conn), get_rules(conn)
    rows, total_deal, total_te = [], 0.0, 0.0
    for a in crm.all_accounts():
        st = R.standing(conn, a, rules)
        flag = conn.execute("SELECT * FROM flag WHERE account_id=?", (a.id,)).fetchone()
        rows.append({"id": a.id, "name": a.name, "deal_type": a.deal_type, "deal_value": a.deal_value, "stage": a.stage,
                     "owner": REP_NAME.get(a.owner_rep_id), "te": st.te_to_date, "ratio": st.ratio, "limit": st.limit,
                     "over_limit": st.over_limit, "expense_count": st.expense_count,
                     "flag": dict(flag) if flag else None})
        total_deal += a.deal_value
        total_te += st.te_to_date
    tagged = conn.execute("SELECT COUNT(*) n, SUM(CASE WHEN match_confidence>=0.8 AND match_evidence NOT LIKE 'Rep picked%' THEN 1 ELSE 0 END) auto "
                          "FROM expense WHERE status IN ('approved','pending')").fetchone()
    over = [r for r in rows if r["over_limit"] and (r["flag"] or {}).get("status") == "open"]
    return {"accounts": rows,
            "totals": {"deal_value": total_deal, "te": total_te, "ratio": total_te / total_deal if total_deal else 0,
                       "over_limit_count": len(over), "over_limit_names": [r["name"] for r in over],
                       "auto_tag_rate": (tagged["auto"] or 0) / tagged["n"] if tagged["n"] else 0},
            "default_limit": rules["default_limit"]}


@app.get("/accounts/{account_id}")
def account_detail(account_id: str, conn=Depends(db)):
    crm, rules = CRM(conn), get_rules(conn)
    a = crm.get(account_id)
    if not a:
        raise HTTPException(404)
    st = R.standing(conn, a, rules)
    exps = _rows(conn.execute("SELECT * FROM expense WHERE account_id=? AND status IN ('approved','pending') ORDER BY occurred_at DESC", (a.id,)))
    for e in exps:
        e["rep_name"] = REP_NAME.get(e["rep_id"])
    # Signals: last 30 days vs prior 30, stage age, close date pushes (fixture: Pinecrest pushed twice)
    now = datetime.fromisoformat("2026-10-29T12:00:00-07:00")
    def window(days_from, days_to):
        return sum(e["amount"] for e in exps if days_to < (now - datetime.fromisoformat(e["occurred_at"])).days <= days_from)
    last30, prior30 = window(30, 0), window(60, 30)
    stage_days = (now.date() - datetime.fromisoformat(a.stage_changed_at).date()).days
    owner = REP_NAME.get(a.owner_rep_id, "the rep").split()[0]
    draft = (f"Hi {owner}, {a.name} T&E is at ${st.te_to_date/1000:.1f}K against a ${a.deal_value/1000:.0f}K deal"
             f"{' that hasn’t moved since ' + datetime.fromisoformat(a.stage_changed_at).strftime('%B') if stage_days > 45 else ''}. "
             f"Is there an expansion we should add to the CRM, or should we slow spend until it moves?")
    flag = conn.execute("SELECT * FROM flag WHERE account_id=?", (a.id,)).fetchone()
    activity = _rows(conn.execute("SELECT at, text FROM activity WHERE account_id=? ORDER BY at DESC LIMIT 6", (a.id,)))
    return {"account": {**a.__dict__, "owner": REP_NAME.get(a.owner_rep_id)}, "standing": st.__dict__,
            "deal_value_to_clear": R.deal_value_to_clear(st), "expenses": exps,
            "signals": {"last30": last30, "prior30": prior30, "stage_days": stage_days,
                        "close_date_pushes": 2 if a.id == "acc_pinecrest" else 0},
            "draft_message": draft, "flag": dict(flag) if flag else None, "activity": activity,
            "reps": sorted({e["rep_name"] for e in exps})}


class FlagAction(BaseModel):
    action: str  # expected | clear | ask
    note: str | None = None
    message: str | None = None


@app.post("/accounts/{account_id}/flag")
def flag_action(account_id: str, body: FlagAction, conn=Depends(db)):
    a = CRM(conn).get(account_id)
    if not a:
        raise HTTPException(404)
    now = datetime.now().isoformat()
    with cursor(conn) as cur:
        if body.action in ("expected", "clear"):
            cur.execute("UPDATE flag SET status=?, note=? WHERE account_id=?",
                        ("expected" if body.action == "expected" else "cleared", body.note, account_id))
            cur.execute("INSERT INTO activity (account_id, at, text) VALUES (?,?,?)",
                        (account_id, now, f"Marked as expected by Dana{': ' + body.note if body.note else ''}"))
        elif body.action == "ask":
            cur.execute("INSERT INTO thread_message (rep_id, direction, body, created_at) VALUES (?,?,?,?)",
                        (a.owner_rep_id, "finance", body.message or "", now))
            cur.execute("UPDATE flag SET status='asked' WHERE account_id=?", (account_id,))
            cur.execute("INSERT INTO activity (account_id, at, text) VALUES (?,?,?)",
                        (account_id, now, f"Dana asked {REP_NAME.get(a.owner_rep_id)} by text"))
        else:
            raise HTTPException(400, "unknown action")
    return {"ok": True}


@app.get("/events")
def events(conn=Depends(db)):
    rows = _rows(conn.execute("SELECT * FROM event ORDER BY start DESC"))
    for r in rows:
        r["reps"] = json.loads(r.pop("reps_json"))
        r["reached"] = json.loads(r.pop("reached_json"))
        r["ratio"] = r["spend"] / r["pipeline_sourced"] if r["pipeline_sourced"] else None
        r["return_per_dollar"] = r["pipeline_sourced"] / r["spend"] if r["spend"] else None
    spend = sum(r["spend"] for r in rows)
    pipe = sum(r["pipeline_sourced"] for r in rows)
    return {"events": rows, "totals": {"spend": spend, "pipeline_sourced": pipe, "ratio": spend / pipe if pipe else 0,
                                       "tag_rate": 0.88}}


# ---------- Admin ----------

@app.get("/settings")
def read_settings(conn=Depends(db)):
    rules = get_rules(conn)
    crm = CRM(conn)
    rules["strategic_accounts"] = [{"id": a.id, "name": a.name, "limit": a.limit_override}
                                   for a in crm.all_accounts() if a.limit_override is not None]
    rules["integrations"] = [
        {"name": "Ramp", "detail": "Transactions, receipts, memos. Read and write.", "connected": True},
        {"name": "Salesforce", "detail": "Accounts, opportunities, stage. Read only (fixture).", "connected": True},
        {"name": "Google Calendar", "detail": "Event titles and attendees. Read only (fixture).", "connected": True},
        {"name": "Twilio SMS", "detail": settings.twilio_from_number or "Simulator only. Add Twilio env vars to go live.",
         "connected": bool(settings.twilio_from_number)},
        {"name": "Claude" + (" via Amazon Bedrock" if settings.provider == "bedrock" else ""),
         "detail": settings.model_label if settings.llm_enabled else "No credentials. Running deterministic matcher.",
         "connected": settings.llm_enabled},
        {"name": "HubSpot", "detail": "Not connected", "connected": False},
    ]
    return rules


class SettingsIn(BaseModel):
    default_limit: float | None = None
    small_deal_threshold: float | None = None
    small_deal_cap: float | None = None
    auto_approve_under: float | None = None
    copy_finance_on_over_limit: bool | None = None
    ask_rep_before_flagging: bool | None = None
    agent_can_tag_without_asking: bool | None = None
    agent_writes_memo: bool | None = None
    agent_drafts_messages: bool | None = None


@app.put("/settings")
def write_settings(body: SettingsIn, conn=Depends(db)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    rules = set_rules(conn, updates)
    crm = CRM(conn)
    for a in crm.all_accounts():
        R.refresh_flag(conn, a, R.standing(conn, a, rules))
    return rules


@app.post("/admin/reset")
def reset(conn=Depends(db)):
    init_db(conn, reset=True)
    return {"ok": True}


@app.get("/health")
def health():
    return {"ok": True, "provider": settings.provider if settings.llm_enabled else "mock",
            "model": settings.model_label if settings.llm_enabled else None, "twilio": bool(settings.twilio_from_number)}
