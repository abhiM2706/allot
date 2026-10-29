"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { get, send, money, k, pct, when } from "@/lib/api";
import { Shell, Stat } from "@/components/ui";

type Data = {
  account: { id: string; name: string; deal_type: string; deal_value: number; stage: string; close_date: string; owner: string; stage_changed_at: string; synced_at: string };
  standing: { te_to_date: number; ratio: number; limit: number; over_limit: boolean; expense_count: number };
  deal_value_to_clear: number;
  expenses: { id: string; occurred_at: string; merchant: string; memo: string; rep_name: string; amount: number; status: string }[];
  signals: { last30: number; prior30: number; stage_days: number; close_date_pushes: number };
  draft_message: string; flag: { status: string } | null; activity: { at: string; text: string }[]; reps: string[];
};

export default function AccountDetail() {
  const { id } = useParams<{ id: string }>();
  const [d, setD] = useState<Data | null>(null);
  const [msg, setMsg] = useState("");
  const [sent, setSent] = useState(false);
  const load = () => get<Data>(`/accounts/${id}`).then((x) => { setD(x); setMsg((m) => m || x.draft_message); });
  useEffect(() => { load(); }, [id]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!d) return <Shell><div /></Shell>;
  const a = d.account, st = d.standing, owner = a.owner.split(" ")[0];
  const over = st.over_limit;
  return (
    <Shell>
      <Link href="/finance" className="text-sm text-mute">‹ Accounts</Link>
      <div className="flex flex-wrap items-end justify-between gap-4 mt-3 mb-6">
        <div>
          <div className="flex items-center gap-3"><h1 className="text-3xl font-bold">{a.name}</h1>
            {over && d.flag?.status === "open" && <span className="chip chip-warn">Over the {pct(st.limit, 0)} limit</span>}
            {d.flag?.status === "expected" && <span className="chip chip-ok">Marked as expected</span>}
            {d.flag?.status === "asked" && <span className="chip chip-ok">Asked {owner}</span>}</div>
          <div className="text-sm text-mute mt-1">{a.deal_type} · Opportunity owner {a.owner} · Stage: {a.stage} · Close date {when(a.close_date)}</div>
        </div>
        <div className="flex gap-2.5">
          <button className="btn-ghost" onClick={async () => { await send(`/accounts/${id}/flag`, { action: "expected", note: "Expansion expected" }); load(); }}>Mark as expected</button>
          <a href="#draft" className="btn">Ask {owner}</a>
        </div>
      </div>
      <div className="flex flex-wrap gap-4 mb-6">
        <Stat label="Open deal value" value={k(a.deal_value)} sub="From Salesforce (fixture)" />
        <Stat label="T&E to date" value={k(st.te_to_date)} sub={`${st.expense_count} expenses, ${d.reps.length} rep${d.reps.length === 1 ? "" : "s"}`} warn={over} />
        <Stat label="T&E as % of deal" value={pct(st.ratio)} sub={`Limit ${pct(st.limit, 0)}`} warn={over} />
        <Stat label="Deal value needed to clear limit" value={k(d.deal_value_to_clear)} sub={over ? `${k(Math.max(0, d.deal_value_to_clear - a.deal_value))} more than today, or an expansion` : "Already under the limit"} />
      </div>
      <div className="flex flex-col xl:flex-row gap-4">
        <div className="card p-5 flex-1">
          <div className="text-lg font-semibold mb-3">Expenses on this account</div>
          <table className="w-full text-sm">
            <thead><tr className="text-left label border-b border-line"><th className="py-2 pl-2 font-semibold">DATE</th><th className="py-2 font-semibold">EXPENSE</th><th className="py-2 font-semibold">REP</th><th className="py-2 font-semibold text-right pr-2">AMOUNT</th></tr></thead>
            <tbody>
              {d.expenses.map((e, i) => (
                <tr key={e.id} className={`border-b border-line-soft last:border-0 ${i === 0 && over ? "bg-orange-soft" : ""}`}>
                  <td className="py-3 pl-2 text-mute">{when(e.occurred_at)}</td>
                  <td className="font-medium">{e.memo || e.merchant}{e.status === "pending" && <span className="chip chip-ok ml-2 h-5 text-[10px]">pending</span>}</td>
                  <td className="text-mute">{e.rep_name}</td>
                  <td className="text-right pr-2 font-semibold">{money(e.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="w-full xl:w-[380px] flex flex-col gap-4">
          <div className="card p-5 flex flex-col gap-3">
            <div className="font-semibold">What the agent sees</div>
            <Sig l="SPEND TREND" v={`${k(d.signals.last30)} in the last 30 days, ${d.signals.prior30 ? `${d.signals.last30 >= d.signals.prior30 ? "up" : "down"} from ${k(d.signals.prior30)} the 30 days before` : "nothing the 30 days before"}`} />
            <Sig l="DEAL MOVEMENT" v={`Stage unchanged for ${d.signals.stage_days} days.${d.signals.close_date_pushes ? ` Close date pushed ${d.signals.close_date_pushes === 1 ? "once" : "twice"}.` : ""}`} />
            <Sig l="SIGNAL" v={over ? "High spend with a stalled deal is the pattern most often tied to a loss. Worth a conversation, not a block." : "Spend is in proportion to the deal. Nothing to do."} />
          </div>
          <div id="draft" className="rounded-2xl border border-teal-line bg-teal-tint p-5 flex flex-col gap-2.5">
            <div className="font-semibold text-teal-deep">Draft message to {owner}</div>
            <textarea value={msg} onChange={(e) => setMsg(e.target.value)} rows={5} className="w-full text-sm bg-white/70 rounded-lg p-3 border border-teal-line outline-none" />
            <div className="flex gap-2.5">
              <button className="btn-ghost h-10" onClick={() => setMsg(d.draft_message)}>Reset</button>
              <button className="btn h-10 flex-1" disabled={sent} onClick={async () => { await send(`/accounts/${id}/flag`, { action: "ask", message: msg }); setSent(true); load(); }}>{sent ? `Sent to ${owner} by text` : "Send by text"}</button>
            </div>
            <div className="text-xs text-mute">The agent drafted this. You send it. It never messages a rep about spend on its own.</div>
          </div>
          <div className="card p-5">
            <div className="font-semibold mb-2">Activity</div>
            {d.activity.map((x, i) => <div key={i} className="text-[13px] text-mute py-0.5">{when(x.at)} · {x.text}</div>)}
          </div>
        </div>
      </div>
    </Shell>
  );
}

function Sig({ l, v }: { l: string; v: string }) {
  return <div><div className="label">{l}</div><div className="text-sm mt-0.5">{v}</div></div>;
}
