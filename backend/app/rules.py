"""The money rules. Plain arithmetic, no model, so a CFO can audit every flag."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from .adapters.crm import Account
from .db import get_rules


@dataclass
class AccountStanding:
    account_id: str
    te_to_date: float
    deal_value: float
    ratio: float
    limit: float
    over_limit: bool
    expense_count: int


def account_limit(acc: Account, rules: dict) -> float:
    if acc.limit_override is not None:
        return float(acc.limit_override)
    if acc.deal_value < rules["small_deal_threshold"]:
        # Flat cap expressed as a ratio of this deal's value so the comparison stays a ratio
        return rules["small_deal_cap"] / max(acc.deal_value, 1)
    return float(rules["default_limit"])


def standing(conn: sqlite3.Connection, acc: Account, rules: dict | None = None,
             include_pending: bool = True) -> AccountStanding:
    rules = rules or get_rules(conn)
    statuses = ("approved", "pending") if include_pending else ("approved",)
    q = f"SELECT COALESCE(SUM(amount),0) s, COUNT(*) n FROM expense WHERE account_id=? AND status IN ({','.join('?'*len(statuses))})"
    row = conn.execute(q, (acc.id, *statuses)).fetchone()
    te = float(row["s"])
    lim = account_limit(acc, rules)
    ratio = te / acc.deal_value if acc.deal_value else 0.0
    return AccountStanding(acc.id, te, acc.deal_value, ratio, lim, ratio > lim, int(row["n"]))


def auto_approve(amount: float, st: AccountStanding, rules: dict) -> bool:
    return amount < rules["auto_approve_under"] and not st.over_limit


def deal_value_to_clear(st: AccountStanding) -> float:
    """How large the deal would need to be for current T&E to sit at the limit."""
    return st.te_to_date / st.limit if st.limit else 0.0


def refresh_flag(conn: sqlite3.Connection, acc: Account, st: AccountStanding) -> None:
    row = conn.execute("SELECT status FROM flag WHERE account_id=?", (acc.id,)).fetchone()
    now = datetime.now().isoformat()
    if st.over_limit and (row is None or row["status"] == "cleared"):
        conn.execute("INSERT OR REPLACE INTO flag VALUES (?,?,?,?,?)", (acc.id, now, st.ratio, "open", None))
        conn.execute("INSERT INTO activity (account_id, at, text) VALUES (?,?,?)",
                     (acc.id, now, f"Flagged: crossed {round(st.limit*100)}% limit"))
    elif row and row["status"] == "open":
        conn.execute("UPDATE flag SET ratio=? WHERE account_id=?", (st.ratio, acc.id))
    conn.commit()
