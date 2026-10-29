"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { get, send, k, pct } from "@/lib/api";
import { Shell, Stat, PageTitle, Bar, Pill } from "@/components/ui";

type Acc = { id: string; name: string; deal_type: string; deal_value: number; te: number; ratio: number; limit: number; over_limit: boolean; expense_count: number; flag: { status: string } | null };
type Data = { accounts: Acc[]; totals: { deal_value: number; te: number; ratio: number; over_limit_count: number; over_limit_names: string[]; auto_tag_rate: number }; default_limit: number };

export default function Overview() {
  const [d, setD] = useState<Data | null>(null);
  const load = () => get<Data>("/accounts").then(setD);
  useEffect(() => { load(); const t = setInterval(load, 5000); return () => clearInterval(t); }, []);
  if (!d) return <Shell><div /></Shell>;
  const flagged = d.accounts.find((a) => a.over_limit && a.flag?.status === "open");
  return (
    <Shell>
      <PageTitle title="Spend vs deal value" sub="Sales T&E tagged to accounts and events, Q4 to date. Sample data."
        right={<div className="flex gap-2"><Pill on>Accounts</Pill><Link href="/finance/events"><Pill>Events</Pill></Link><Link href="/rep"><Pill>Reps</Pill></Link></div>} />
      <div className="flex flex-wrap gap-4 mb-6">
        <Stat label="Open deal value tracked" value={k(d.totals.deal_value)} sub={`${d.accounts.length} accounts`} />
        <Stat label="T&E on those accounts" value={k(d.totals.te)} sub={`${pct(d.totals.ratio)} of deal value`} />
        <Stat label={`Over the ${pct(d.default_limit, 0)} limit`} value={`${d.totals.over_limit_count} account${d.totals.over_limit_count === 1 ? "" : "s"}`} sub={d.totals.over_limit_names.join(", ") || "None"} warn={d.totals.over_limit_count > 0} />
        <Stat label="Receipts auto-tagged" value={pct(d.totals.auto_tag_rate, 0)} sub="Rest asked one question" />
      </div>
      {flagged && (
        <div className="rounded-2xl border border-orange-line bg-orange-tint p-5 flex flex-wrap items-center justify-between gap-4 mb-6">
          <div className="flex-1 min-w-[320px]">
            <div className="font-bold text-orange-deep">{flagged.name} is at {pct(flagged.ratio, 0)} of deal value</div>
            <div className="text-sm mt-1">{k(flagged.te)} of T&amp;E against a {k(flagged.deal_value)} opportunity that is still open. The deal can still change, so this is the point to ask the rep what the plan is.</div>
          </div>
          <div className="flex gap-2.5">
            <button className="btn-ghost" onClick={async () => { await send(`/accounts/${flagged.id}/flag`, { action: "expected", note: "Expansion expected" }); load(); }}>Mark as expected</button>
            <Link href={`/finance/accounts/${flagged.id}`} className="btn">Ask the rep</Link>
          </div>
        </div>
      )}
      <div className="card p-5">
        <div className="text-lg font-semibold mb-3">Accounts</div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[680px] text-[15px]">
            <thead><tr className="text-left label border-b border-line"><th className="py-2 pl-2 font-semibold">ACCOUNT</th><th className="py-2 font-semibold">DEAL VALUE</th><th className="py-2 font-semibold">T&amp;E TO DATE</th><th className="py-2 font-semibold w-[40%]">T&amp;E AS % OF DEAL VALUE</th></tr></thead>
            <tbody>
              {d.accounts.map((a) => (
                <tr key={a.id} className={`border-b border-line-soft last:border-0 ${a.over_limit ? "bg-orange-soft" : ""}`}>
                  <td className="py-3.5 pl-2"><Link href={`/finance/accounts/${a.id}`} className="font-semibold hover:underline">{a.name}</Link>
                    <div className={`text-[13px] ${a.over_limit ? "text-orange-text font-semibold" : "text-mute"}`}>{a.over_limit ? `Over the ${pct(a.limit, 0)} limit` : a.deal_type}</div></td>
                  <td>{k(a.deal_value)}</td><td>{k(a.te)}</td>
                  <td className="pr-2"><div className="flex items-center gap-3"><Bar ratio={a.ratio} limit={a.limit} warn={a.over_limit} /><span className={`w-12 font-semibold ${a.over_limit ? "text-orange-text" : ""}`}>{pct(a.ratio)}</span></div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="text-[13px] text-mute mt-3">The black marker is each account&apos;s limit (default {pct(d.default_limit, 0)}, strategic accounts higher; set in Settings). The bar scale ends at 30%.</div>
      </div>
    </Shell>
  );
}

