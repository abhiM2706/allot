"""End-to-end tests on the five sample scenarios, running the deterministic path (no API key needed).
With ANTHROPIC_API_KEY set and TABBED_TEST_LIVE=1 they run against Claude too."""

import os
import sqlite3
from pathlib import Path

import pytest

os.environ["PROVIDER"] = "mock"
from app import db as DB  # noqa: E402
from app import rules as R  # noqa: E402
from app.adapters.crm import CRM  # noqa: E402
from app.agent.conversation import handle_inbound  # noqa: E402
from app.agent.receipt import sidecar_hints  # noqa: E402

FIX = Path(__file__).resolve().parent.parent / "fixtures" / "receipts"


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:", check_same_thread=False)
    c.row_factory = sqlite3.Row
    DB.init_db(c)
    return c


def send(conn, rep, receipt=None, text=None):
    image, hints = None, {}
    if receipt:
        p = FIX / receipt
        image, hints = p.read_bytes(), sidecar_hints(p)
    return handle_inbound(conn, rep, text, image, "image/jpeg", None, hints)


def test_seed_numbers_match_the_mockups(conn):
    crm = CRM(conn)
    st = {a.id: R.standing(conn, a) for a in crm.all_accounts()}
    assert round(st["acc_pinecrest"].te_to_date) == 9804
    assert st["acc_pinecrest"].over_limit and round(st["acc_pinecrest"].ratio, 2) == 0.28
    assert round(st["acc_northwind"].ratio, 3) == 0.011  # becomes 1.3% after the demo dinner
    assert not st["acc_northwind"].over_limit
    assert st["acc_northwind"].limit == 0.25  # strategic override


def test_dinner_with_calendar_and_crm_is_auto_tagged(conn):
    t = send(conn, "rep_maya", receipt="harbor_table.jpg")
    assert t.state == "awaiting_attendees"
    assert t.replies[0].card["account"] == "Northwind Logistics"
    assert t.replies[0].card["confidence"] >= 0.8
    assert "Who joined you?" in t.replies[0].body

    t2 = send(conn, "rep_maya", text="Me, Dana, Chris, and Jordan from SE")
    assert t2.state == "idle"
    e = conn.execute("SELECT * FROM expense WHERE id=?", (t.expense_id,)).fetchone()
    assert e["account_id"] == "acc_northwind"
    assert e["status"] == "pending"  # $412 is over the $100 routine threshold
    assert "Northwind" in e["memo"] and "4 attendees" in e["memo"]
    st = R.standing(conn, CRM(conn).get("acc_northwind"))
    assert round(st.te_to_date) == 3100 and round(st.ratio, 3) == 0.013


def test_coffee_without_attendees_asks_and_remembers(conn):
    t = send(conn, "rep_maya", receipt="blue_door.jpg")
    assert t.state == "awaiting_account"
    opts = t.replies[0].card["options"]
    assert len(opts) == 3 and opts[-1]["account_id"] is None
    assert "Which account" in t.replies[0].body

    t2 = send(conn, "rep_maya", text="1")
    assert t2.state == "idle"
    e = conn.execute("SELECT * FROM expense WHERE id=?", (t.expense_id,)).fetchone()
    assert e["account_id"] == opts[0]["account_id"]
    assert e["status"] == "approved" and e["approved_by"] == "agent"  # $18.40 under threshold, account in limit

    # Second coffee at the same place and hour is now tagged without asking
    t3 = send(conn, "rep_maya", receipt="blue_door.jpg")
    assert t3.state == "awaiting_attendees"
    assert t3.replies[0].card["account"] == CRM(conn).get(opts[0]["account_id"]).name


def test_over_limit_account_never_auto_approves(conn):
    t = send(conn, "rep_tom", receipt="osteria_nove.jpg")
    assert t.state == "awaiting_attendees" and t.replies[0].card["account"] == "Pinecrest Health"
    t2 = send(conn, "rep_tom", text="Me, Elena, Raj and 3 from Pinecrest")
    e = conn.execute("SELECT * FROM expense WHERE id=?", (t.expense_id,)).fetchone()
    assert e["status"] == "pending"
    flag = conn.execute("SELECT * FROM flag WHERE account_id='acc_pinecrest'").fetchone()
    assert flag["status"] == "open"


def test_not_a_customer_expense_is_left_untagged(conn):
    t = send(conn, "rep_maya", receipt="blue_door.jpg")
    send(conn, "rep_maya", text="3")
    e = conn.execute("SELECT * FROM expense WHERE id=?", (t.expense_id,)).fetchone()
    assert e["status"] == "personal" and e["account_id"] is None


def test_raising_the_limit_clears_nothing_silently(conn):
    rules = DB.set_rules(conn, {"default_limit": 0.30})
    st = R.standing(conn, CRM(conn).get("acc_pinecrest"), rules)
    assert not st.over_limit  # 28% < 30%
    # The flag record stays until finance clears it; arithmetic changes, history does not
    assert conn.execute("SELECT status FROM flag WHERE account_id='acc_pinecrest'").fetchone()["status"] == "open"
