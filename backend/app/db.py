"""SQLite storage. Five tables, as described in the product brief, plus thread state for the SMS agent."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .config import FIXTURES_DIR, settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS account (
    id TEXT PRIMARY KEY, name TEXT, domain TEXT, deal_type TEXT, deal_value REAL,
    stage TEXT, close_date TEXT, owner_rep_id TEXT, stage_changed_at TEXT,
    contacts_json TEXT, limit_override REAL, synced_at TEXT
);
CREATE TABLE IF NOT EXISTS expense (
    id TEXT PRIMARY KEY, rep_id TEXT, account_id TEXT, merchant TEXT, amount REAL,
    occurred_at TEXT, city TEXT, items_json TEXT, guest_count INTEGER,
    memo TEXT, attendees TEXT, status TEXT,
    match_confidence REAL, match_evidence TEXT, approved_by TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS event (
    id TEXT PRIMARY KEY, name TEXT, start TEXT, end TEXT, city TEXT,
    reps_json TEXT, spend REAL, pipeline_sourced REAL, reached_json TEXT
);
CREATE TABLE IF NOT EXISTS rule (key TEXT PRIMARY KEY, value_json TEXT);
CREATE TABLE IF NOT EXISTS memory (
    rep_id TEXT, merchant TEXT, hour INTEGER, account_id TEXT, created_at TEXT,
    PRIMARY KEY (rep_id, merchant, hour)
);
CREATE TABLE IF NOT EXISTS thread_message (
    id INTEGER PRIMARY KEY AUTOINCREMENT, rep_id TEXT, direction TEXT, body TEXT,
    media_url TEXT, payload_json TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS thread_state (rep_id TEXT PRIMARY KEY, state_json TEXT);
CREATE TABLE IF NOT EXISTS flag (
    account_id TEXT PRIMARY KEY, flagged_at TEXT, ratio REAL, status TEXT, note TEXT
);
CREATE TABLE IF NOT EXISTS activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT, account_id TEXT, at TEXT, text TEXT
);
"""

DEFAULT_RULES = {
    "default_limit": 0.15,
    "small_deal_threshold": 25000,
    "small_deal_cap": 5000,
    "auto_approve_under": 100,
    "copy_finance_on_over_limit": True,
    "ask_rep_before_flagging": False,
    "agent_can_tag_without_asking": True,
    "agent_writes_memo": True,
    "agent_drafts_messages": True,
    "strategic_overrides": {"acc_northwind": 0.25, "acc_harborvale": 0.25},
}


def connect(path: Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or settings.database_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def cursor(conn: sqlite3.Connection):
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    finally:
        cur.close()


def init_db(conn: sqlite3.Connection, reset: bool = False) -> None:
    if reset:
        for t in ["account", "expense", "event", "rule", "memory", "thread_message", "thread_state", "flag", "activity"]:
            conn.execute(f"DROP TABLE IF EXISTS {t}")
    conn.executescript(SCHEMA)
    if conn.execute("SELECT COUNT(*) FROM account").fetchone()[0] == 0:
        seed(conn)


def _load(name: str):
    return json.loads((FIXTURES_DIR / name).read_text())


def seed(conn: sqlite3.Connection) -> None:
    rules = DEFAULT_RULES
    with cursor(conn) as cur:
        for a in _load("accounts.json"):
            cur.execute(
                "INSERT INTO account VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (a["id"], a["name"], a["domain"], a["deal_type"], a["deal_value"], a["stage"], a["close_date"],
                 a["owner_rep_id"], a["stage_changed_at"], json.dumps(a["contacts"]),
                 rules["strategic_overrides"].get(a["id"]), "2026-10-29T08:55:00-07:00"),
            )
        for e in _load("expenses_seed.json"):
            cur.execute(
                "INSERT INTO expense (id, rep_id, account_id, merchant, amount, occurred_at, memo, attendees, status, match_confidence, match_evidence, approved_by, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (e["id"], e["rep_id"], e["account_id"], e["merchant"], e["amount"], e["occurred_at"], e["memo"],
                 e.get("attendees"), e["status"], e["match_confidence"], e["match_evidence"], "mgr_priya", e["occurred_at"]),
            )
        for ev in _load("events.json"):
            cur.execute(
                "INSERT INTO event VALUES (?,?,?,?,?,?,?,?,?)",
                (ev["id"], ev["name"], ev["start"], ev["end"], ev["city"], json.dumps(ev["reps"]), ev["spend"],
                 ev["pipeline_sourced"], json.dumps(ev["reached"])),
            )
        for k, v in rules.items():
            cur.execute("INSERT INTO rule VALUES (?,?)", (k, json.dumps(v)))
        cur.execute("INSERT INTO flag VALUES (?,?,?,?,?)",
                    ("acc_pinecrest", "2026-10-15T09:00:00-07:00", 0.28, "open", None))
        for at, text in [
            ("2026-10-15T09:00:00-07:00", "Flagged: crossed 15% limit"),
            ("2026-10-14T22:30:00-07:00", "Tom Reyes logged $1,240, approved by Priya"),
            ("2026-10-02T17:00:00-07:00", "Maya Okafor logged $3,620, approved by Priya"),
        ]:
            cur.execute("INSERT INTO activity (account_id, at, text) VALUES (?,?,?)", ("acc_pinecrest", at, text))


def get_rules(conn: sqlite3.Connection) -> dict:
    rows = conn.execute("SELECT key, value_json FROM rule").fetchall()
    return {r["key"]: json.loads(r["value_json"]) for r in rows}


def set_rules(conn: sqlite3.Connection, updates: dict) -> dict:
    with cursor(conn) as cur:
        for k, v in updates.items():
            cur.execute("INSERT OR REPLACE INTO rule VALUES (?,?)", (k, json.dumps(v)))
    return get_rules(conn)
