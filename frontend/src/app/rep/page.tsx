"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { API, get, send, k, pct } from "@/lib/api";
import { Phone, Header, Bar } from "@/components/ui";

type Msg = { id: number; direction: "in" | "out" | "finance" | "manager"; body: string; media_url?: string | null; payload?: { kind?: string; options?: { n: number; label: string }[]; account?: string; memo?: string; confidence?: number; evidence?: string; status?: string } | null };
type Fixture = { file: string; url: string; merchant: string; total: number; label: string; rep_id: string };
type Summary = { rep: { name: string }; recent: { id: string; merchant: string; amount: number; account_name: string | null; status: string; created_at: string }[]; accounts: { id: string; name: string; deal_value: number; te: number; ratio: number; limit: number; over_limit: boolean }[]; finance_question: { body: string } | null };

const REPS = [{ id: "rep_maya", name: "Maya Okafor" }, { id: "rep_tom", name: "Tom Reyes" }];

export default function RepPage() {
  const [rep, setRep] = useState("rep_maya");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState<"thread" | "expenses">("thread");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [health, setHealth] = useState<{ provider: string } | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const [clock, setClock] = useState("9:41");
  useEffect(() => { setClock(new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }).replace(/ [AP]M/, "")); }, []);

  const refresh = useCallback(async () => {
    const [m, s] = await Promise.all([get<Msg[]>(`/thread/${rep}`), get<Summary>(`/rep/${rep}/summary`)]);
    setMsgs(m); setSummary(s);
  }, [rep]);

  useEffect(() => { get<Fixture[]>("/fixtures").then(setFixtures); get<{ provider: string }>("/health").then(setHealth); }, []);
  useEffect(() => { refresh(); const t = setInterval(refresh, 4000); return () => clearInterval(t); }, [refresh]);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs.length]);

  async function sendText() {
    if (!text.trim()) return;
    setBusy(true);
    await send("/sms/simulate", { rep_id: rep, text });
    setText(""); await refresh(); setBusy(false);
  }
  async function sendReceipt(file: string) {
    setBusy(true);
    await send("/sms/simulate", { rep_id: rep, receipt: file });
    await refresh(); setBusy(false);
  }
  async function upload(f: File) {
    setBusy(true);
    const fd = new FormData(); fd.append("rep_id", rep); fd.append("file", f);
    await fetch(`${API}/sms/upload`, { method: "POST", body: fd });
    await refresh(); setBusy(false);
  }
  async function reset() { await send(`/thread/${rep}/reset`); await refresh(); }

  return (
    <div className="min-h-screen flex flex-col lg:flex-row gap-10 items-start justify-center px-6 py-10">
      <div className="flex flex-col items-center gap-3">
        <div className="flex gap-2">
          {REPS.map((r) => (
            <button key={r.id} onClick={() => setRep(r.id)} className={`chip ${rep === r.id ? "bg-ink text-white" : "bg-white border border-field"}`}>{r.name}</button>
          ))}
          <button onClick={() => setTab(tab === "thread" ? "expenses" : "thread")} className="chip bg-white border border-field">{tab === "thread" ? "My expenses" : "Messages"}</button>
        </div>
        {tab === "thread" ? (
          <Phone title="Tabbed" sub="Text a receipt to log it" clock={clock}>
            <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-2.5">
              {msgs.length === 0 && <div className="text-center text-xs text-mute mt-10">Send a receipt below to start.</div>}
              {msgs.map((m) => <Bubble key={m.id} m={m} />)}
              <div ref={bottom} />
            </div>
            <div className="bg-white border-t border-line px-5 pt-3 pb-4 flex gap-2.5 items-center">
              <input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && sendText()} placeholder="Text message"
                className="flex-1 h-11 rounded-full border border-field px-4 text-[15px] outline-none" />
              <button onClick={sendText} disabled={busy} aria-label="Send" className="w-11 h-11 rounded-full bg-teal text-white font-bold disabled:opacity-50">↑</button>
            </div>
          </Phone>
        ) : (
          <Phone clock="7:49">
            <Header eyebrow="My expenses" title="This week" />
            <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-3">
              {summary?.recent[0] && (
                <div className="card p-4">
                  <div className="flex justify-between items-center"><span className="font-semibold">{summary.recent[0].merchant}, {k(summary.recent[0].amount)}</span>
                    <span className={`chip ${summary.recent[0].status === "approved" ? "chip-ok" : "chip-ok"}`}>{summary.recent[0].status === "approved" ? "Approved" : "Pending approval"}</span></div>
                  <div className="text-[13px] text-mute mt-1">Tagged to {summary.recent[0].account_name ?? "no account"}. No form, no dropdown.</div>
                </div>
              )}
              <div className="label">YOUR ACCOUNTS</div>
              {summary?.accounts.map((a) => (
                <div key={a.id} className={`p-4 rounded-2xl border flex justify-between items-center ${a.over_limit ? "bg-orange-soft border-orange-line" : "bg-white border-line"}`}>
                  <div><div className="font-semibold">{a.name}</div><div className="text-[13px] text-mute">{k(a.te)} of {k(a.deal_value)}, {pct(a.ratio)}</div></div>
                  <span className={`chip ${a.over_limit ? "chip-warn" : "chip-ok"}`}>{a.over_limit ? `Over ${pct(a.limit, 0)}` : "On track"}</span>
                </div>
              ))}
              {summary?.finance_question && (
                <div className="p-4 rounded-2xl bg-orange-tint border border-orange-line flex flex-col gap-2">
                  <div className="font-semibold text-orange-deep">Finance asked</div>
                  <div className="text-[13px]">“{summary.finance_question.body}”</div>
                  <button onClick={() => setTab("thread")} className="btn h-10 text-sm">Reply to Dana in Finance</button>
                </div>
              )}
            </div>
          </Phone>
        )}
      </div>

      <aside className="w-full max-w-md flex flex-col gap-4">
        <div className="card p-5">
          <div className="font-semibold text-lg">Phone simulator</div>
          <p className="text-sm text-mute mt-1">
            Same handler as the Twilio webhook. Receipt reading and matching run {health?.provider === "bedrock" ? "on Claude via Amazon Bedrock" : health?.provider === "anthropic" ? "on Claude" : "on the deterministic matcher (no model credentials set)"}.
          </p>
        </div>
        <div className="card p-5 flex flex-col gap-3">
          <div className="font-semibold">Send a sample receipt</div>
          {fixtures.filter((f) => f.rep_id === rep).map((f) => (
            <button key={f.file} onClick={() => sendReceipt(f.file)} disabled={busy} className="flex gap-3 items-start text-left p-3 rounded-xl border border-line hover:border-teal disabled:opacity-50">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={`${API}${f.url}`} alt="" className="w-14 h-20 object-cover object-top rounded border border-line" />
              <div><div className="font-semibold text-sm">{f.merchant}, {k(f.total)}</div><div className="text-xs text-mute mt-1">{f.label}</div></div>
            </button>
          ))}
          <label className="btn-ghost h-10 text-sm cursor-pointer">
            Upload any receipt photo
            <input type="file" accept="image/*" className="hidden" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
          </label>
          <div className="text-xs text-mute">Uploading your own photo needs model credentials on the backend (Bedrock or Anthropic); sample receipts work either way.</div>
        </div>
        <div className="flex gap-2">
          <button onClick={reset} className="btn-ghost h-10 text-sm">Reset thread</button>
          <Link href="/rep/onboarding" className="btn-ghost h-10 text-sm">Onboarding screen</Link>
          <Link href="/approvals" className="btn h-10 text-sm">Go to approvals →</Link>
        </div>
      </aside>
    </div>
  );
}

function Bubble({ m }: { m: Msg }) {
  if (m.direction === "in") {
    return (
      <div className="self-end max-w-[270px] bg-white border border-line rounded-[18px] rounded-br-[4px] p-3 text-[15px]">
        {m.media_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={`${API}${m.media_url}`} alt="receipt" className="w-full rounded-lg border border-dashed border-field mb-1.5" />
        )}
        {m.media_url && !m.body && <div className="text-xs text-mute">Photo of receipt</div>}
        {m.body}
      </div>
    );
  }
  if (m.direction === "finance" || m.direction === "manager") {
    return (
      <div className="self-start max-w-[300px] bg-orange-tint border border-orange-line rounded-[18px] rounded-bl-[4px] px-3.5 py-3 text-[15px]">
        <div className="text-xs font-semibold text-orange-deep mb-1">{m.direction === "finance" ? "Dana, Finance" : "Priya, your manager"}</div>
        {m.body}
      </div>
    );
  }
  const p = m.payload;
  const lines = m.body.split("\n");
  return (
    <div className="self-start max-w-[300px] bg-teal text-white rounded-[18px] rounded-bl-[4px] px-3.5 py-3 text-[15px] leading-snug flex flex-col gap-2">
      <div>{lines[0]}</div>
      {p?.kind === "ask_account" && p.options && (
        <div className="flex flex-col gap-1.5">
          {p.options.map((o) => (
            <div key={o.n} className="flex justify-between bg-white/15 rounded-lg px-3 py-2 text-sm"><span>{o.label}</span><span className="opacity-70">{o.n}</span></div>
          ))}
        </div>
      )}
      {p?.kind === "tagged" && (
        <div className="bg-white/15 rounded-lg px-3 py-2 text-xs">Confidence {Math.round((p.confidence ?? 0) * 100)}% · {p.evidence}</div>
      )}
      {p?.kind === "done" && (
        <div className="bg-white/15 rounded-lg px-3 py-2 text-[13px]"><div className="font-semibold">Account: {p.account}</div><div>Memo: {p.memo}</div></div>
      )}
    </div>
  );
}
