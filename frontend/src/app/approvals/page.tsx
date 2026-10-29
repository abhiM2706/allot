"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { get, money, pct } from "@/lib/api";
import { Phone, Header } from "@/components/ui";

type Row = { id: string; rep_name: string; merchant: string; amount: number; account_name: string | null; deal_type: string | null; ratio: number | null; over_limit: boolean; status: string; approved_by: string | null };
type Data = { pending: Row[]; approved_today: Row[]; rules: { auto_approve_under: number } };

export default function Approvals() {
  const [d, setD] = useState<Data | null>(null);
  useEffect(() => { const load = () => get<Data>("/approvals").then(setD); load(); const t = setInterval(load, 4000); return () => clearInterval(t); }, []);
  return (
    <div className="min-h-screen flex flex-col lg:flex-row gap-10 items-start justify-center px-6 py-10">
      <Phone clock="8:02">
        <Header eyebrow="Approvals" title={d ? `${d.pending.length} waiting` : "…"} />
        <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-3">
          {d?.pending.map((r) => <RowCard key={r.id} r={r} />)}
          {d && d.pending.length === 0 && <div className="text-sm text-mute">Nothing waiting. Send a receipt from the rep screen.</div>}
          <div className="label mt-2">APPROVED</div>
          {d?.approved_today.map((r) => <RowCard key={r.id} r={r} dim />)}
          <div className="card p-4 mt-auto">
            <div className="font-semibold">Routine approvals are handled for you</div>
            <div className="text-[13px] text-mute mt-1">Under {money(d?.rules.auto_approve_under ?? 100, false)} and under the account limit: approved automatically. You only see the rest.</div>
          </div>
        </div>
      </Phone>
      <aside className="max-w-md card p-5 text-sm text-mute">
        <div className="font-semibold text-ink text-lg mb-1">Priya&apos;s queue</div>
        Each row shows the account the agent tagged and that account&apos;s T&amp;E as a share of deal value. Tap a row for the full context. Rows the agent approved on its own are listed under Approved with no action needed.
        <div className="mt-4"><Link href="/finance" className="btn h-10 text-sm">Go to finance →</Link></div>
      </aside>
    </div>
  );
}

function RowCard({ r, dim }: { r: Row; dim?: boolean }) {
  return (
    <Link href={`/approvals/${r.id}`} className={`p-4 rounded-2xl border flex justify-between items-center gap-3 ${r.over_limit ? "bg-orange-soft border-orange-line" : "bg-white border-line"} ${dim ? "opacity-60" : ""}`}>
      <div className="min-w-0"><div className="font-semibold">{r.rep_name}, {money(r.amount)}</div>
        <div className="text-[13px] text-mute">{r.merchant}. {r.account_name ?? "No account"}{r.deal_type ? `, ${r.deal_type.toLowerCase()}` : ""}{r.over_limit ? ", over limit" : ""}{r.approved_by === "agent" ? " · auto" : ""}</div></div>
      {r.ratio !== null && <span className={`chip ${r.over_limit ? "chip-warn" : "chip-ok"}`}>{pct(r.ratio)}</span>}
    </Link>
  );
}
