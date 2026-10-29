"""CRM adapter. The fixture version reads accounts.json; a Salesforce version implements the same two methods
with SOQL against Account, Contact and Opportunity. Read-only by design."""

import json
import sqlite3
from dataclasses import dataclass


@dataclass
class Account:
    id: str
    name: str
    domain: str
    deal_type: str
    deal_value: float
    stage: str
    close_date: str
    owner_rep_id: str
    stage_changed_at: str
    contacts: list[dict]
    limit_override: float | None
    synced_at: str


class CRM:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _row(self, r) -> Account:
        return Account(r["id"], r["name"], r["domain"], r["deal_type"], r["deal_value"], r["stage"], r["close_date"],
                       r["owner_rep_id"], r["stage_changed_at"], json.loads(r["contacts_json"]), r["limit_override"],
                       r["synced_at"])

    def all_accounts(self) -> list[Account]:
        return [self._row(r) for r in self.conn.execute("SELECT * FROM account ORDER BY deal_value DESC")]

    def get(self, account_id: str) -> Account | None:
        r = self.conn.execute("SELECT * FROM account WHERE id=?", (account_id,)).fetchone()
        return self._row(r) if r else None

    def accounts_for_domains(self, domains: set[str]) -> list[Account]:
        return [a for a in self.all_accounts() if a.domain in domains]

    def accounts_for_rep(self, rep_id: str) -> list[Account]:
        return [a for a in self.all_accounts() if a.owner_rep_id == rep_id]
