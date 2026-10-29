"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { get, send, money, k, pct } from "@/lib/api";
import { Phone, Header, Bar } from "@/components/ui";

type Exp = { id: string; rep_name: string; merchant: string; city: string | null; amount: number; occurred_at: string; memo: string; attendees: string | null; status: string; match_confidence: number; match_evidence: string; account: { name: string; deal_type: string; deal_value: number } | null; standing: { te_to_date: number; ratio: number; limit: number; over_limit: boolean } | null };

export default function ApprovalDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [e, setE] = useState<Exp | null>(null);
  const [q, setQ] = useState(false);
  useEffect(() => { get<Exp>(`/expenses/${id}`).then(setE); }, [id]);
  if (!e) return null;
  const st = e.standing;
  return (
    <div className="min-h-screen flex items-center justify-center p-10">
      <Phone clock="8:03">
        <Header eyebrow="‹ Approvals" title={e.merchant} />
        <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-4">
          <div className="card p-4 flex flex-col gap-3">
            <div className="flex justify-between"><div><div className="font-semibold">{e.merchant}{e.city ? `, ${e.city}` : ""}</div><div className="text-[13px] text-mute">{e.rep_name}, {new Date(e.occurred_at).toLocaleString("en-US", { weekday: "short", hour: "numeric", minute: "2-digit" })}</div></div><div className="text-[22px] font-bold">{money(e.amount)}</div></div>
            <Sec l="MEMO" v={e.memo || "—"} />
            <Sec l="TAGGED TO" v={e.account ? `${e.account.name}, ${e.account.deal_type.toLowerCase()}, ${k(e.account.deal_value)}` : "No account"} s={`${e.match_evidence} · confidence ${Math.round((e.match_confidence ?? 0) * 100)}%`} />
            {e.attendees && <Sec l="ATTENDEES" v={e.attendees} />}
          </div>
          {st && e.account && (
            <div className={`rounded-2xl border p-4 flex flex-col gap-2.5 ${st.over_limit ? "bg-orange-tint border-orange-line" : "bg-teal-tint border-teal-line"}`}>
              <div className={`text-[13px] font-semibold ${st.over_limit ? "text-orange-deep" : "text-teal-deep"}`}>Account context</div>
              <div className="flex justify-between text-sm"><span>T&amp;E on this account, including this</span><span className="font-semibold">{k(st.te_to_date)}</span></div>
              <div className="flex"><Bar ratio={st.ratio} limit={st.limit} warn={st.over_limit} /></div>
              <div className="text-[13px]">{pct(st.ratio)} of the {k(e.account.deal_value)} deal value. {st.over_limit ? `Over the ${pct(st.limit, 0)} limit.` : `Within the ${pct(st.limit, 0)} limit.`}</div>
            </div>
          )}
          {q && (
            <div className="card p-4 text-sm">Sent to {e.rep_name.split(" ")[0]} by text: “Quick one on your {e.merchant} expense: what was this for?”</div>
          )}
        </div>
        <div className="bg-white border-t border-line px-5 pt-3 pb-5 flex gap-2.5">
          <button onClick={async () => { await send(`/expenses/${id}/question`, {}); setQ(true); }} className="btn-ghost flex-1 h-12">Ask a question</button>
          {e.status === "pending" ? (
            <button onClick={async () => { await send(`/expenses/${id}/approve`); router.push("/approvals"); }} className="btn flex-1 h-12">Approve</button>
          ) : (
            <Link href="/approvals" className="btn flex-1 h-12 opacity-70">Approved</Link>
          )}
        </div>
      </Phone>
    </div>
  );
}

function Sec({ l, v, s }: { l: string; v: string; s?: string }) {
  return <div><div className="label">{l}</div><div className="text-[15px] mt-1">{v}</div>{s && <div className="text-[13px] text-mute">{s}</div>}</div>;
}
