"use client";
import { useEffect, useState } from "react";
import { get, send, k, pct } from "@/lib/api";
import { Shell, PageTitle } from "@/components/ui";

type Rules = { default_limit: number; small_deal_threshold: number; small_deal_cap: number; auto_approve_under: number; copy_finance_on_over_limit: boolean; ask_rep_before_flagging: boolean; agent_can_tag_without_asking: boolean; agent_writes_memo: boolean; agent_drafts_messages: boolean; strategic_accounts: { id: string; name: string; limit: number }[]; integrations: { name: string; detail: string; connected: boolean }[] };

export default function Settings() {
  const [r, setR] = useState<Rules | null>(null);
  const [saved, setSaved] = useState(false);
  useEffect(() => { get<Rules>("/settings").then(setR); }, []);
  if (!r) return <Shell><div /></Shell>;
  const set = (patch: Partial<Rules>) => { setR({ ...r, ...patch }); setSaved(false); };
  const save = async () => {
    const { default_limit, small_deal_threshold, small_deal_cap, auto_approve_under, copy_finance_on_over_limit, ask_rep_before_flagging, agent_can_tag_without_asking, agent_writes_memo, agent_drafts_messages } = r;
    await send("/settings", { default_limit, small_deal_threshold, small_deal_cap, auto_approve_under, copy_finance_on_over_limit, ask_rep_before_flagging, agent_can_tag_without_asking, agent_writes_memo, agent_drafts_messages }, "PUT");
    setSaved(true);
  };
  return (
    <Shell>
      <PageTitle title="Settings" sub="Limits, integrations, and approval routing. Changes apply to new expenses and recompute every flag." />
      <div className="flex flex-col xl:flex-row gap-4">
        <div className="flex-1 flex flex-col gap-4">
          <div className="card p-5 flex flex-col gap-4">
            <div className="text-lg font-semibold">T&amp;E limit</div>
            <div className="text-sm text-mute">When T&amp;E on an account crosses this share of its open deal value, the account is flagged on the overview and the account owner is asked. Nothing is blocked.</div>
            <div className="flex flex-wrap gap-4">
              <Field label="Default limit" suffix="% of deal value" value={Math.round(r.default_limit * 100)} onChange={(v) => set({ default_limit: v / 100 })} />
              <Field label="Deals under" prefix="$" value={r.small_deal_threshold} onChange={(v) => set({ small_deal_threshold: v })} />
              <Field label="use a flat cap of" prefix="$" value={r.small_deal_cap} onChange={(v) => set({ small_deal_cap: v })} />
              <div className="flex-1 min-w-[220px]"><div className="text-[13px] font-semibold mb-1.5">Strategic accounts</div><div className="h-11 rounded-xl border border-field bg-bg px-3.5 flex items-center text-[15px] text-mute">{r.strategic_accounts.map((a) => `${a.name.split(" ")[0]} ${pct(a.limit, 0)}`).join(", ")}</div></div>
            </div>
          </div>
          <div className="card p-5">
            <div className="text-lg font-semibold mb-1">Approval routing</div>
            <Field label="Auto-approve expenses under" prefix="$" value={r.auto_approve_under} onChange={(v) => set({ auto_approve_under: v })} inline />
            <Row t="Auto-approve routine expenses" s={`Under ${k(r.auto_approve_under)} and under the account limit. Receipt and memo still required.`} on={r.auto_approve_under > 0} onChange={(on) => set({ auto_approve_under: on ? 100 : 0 })} />
            <Row t="Send over-limit expenses to finance too" s="Manager approves, finance is copied. Default is manager only." on={r.copy_finance_on_over_limit} onChange={(v) => set({ copy_finance_on_over_limit: v })} />
            <Row t="Ask the rep before flagging" s="The agent texts the rep for context first, then flags if there is no reply in 2 days." on={r.ask_rep_before_flagging} onChange={(v) => set({ ask_rep_before_flagging: v })} last />
          </div>
          <div className="card p-5">
            <div className="text-lg font-semibold mb-1">What the agent is allowed to do</div>
            <Row t="Tag an expense to an account without asking" s="Only when a calendar event and a CRM opportunity both match. Otherwise it asks." on={r.agent_can_tag_without_asking} onChange={(v) => set({ agent_can_tag_without_asking: v })} />
            <Row t="Write the memo" s="Drafted from the receipt, the event title, and attendees. The rep can edit by text." on={r.agent_writes_memo} onChange={(v) => set({ agent_writes_memo: v })} />
            <Row t="Draft messages to reps" s="Finance always sends them. The agent never messages a rep about spend on its own." on={r.agent_drafts_messages} onChange={(v) => set({ agent_drafts_messages: v })} last />
          </div>
        </div>
        <div className="w-full xl:w-[400px] flex flex-col gap-4">
          <div className="card p-5">
            <div className="text-lg font-semibold mb-1">Integrations</div>
            {r.integrations.map((i, idx) => (
              <div key={i.name} className={`flex items-center justify-between gap-3 py-3 ${idx < r.integrations.length - 1 ? "border-b border-line-soft" : ""}`}>
                <div><div className="font-semibold text-[15px]">{i.name}</div><div className="text-[13px] text-mute">{i.detail}</div></div>
                <span className={`chip ${i.connected ? "chip-ok" : "bg-bg border border-field"}`}>{i.connected ? "Connected" : "Connect"}</span>
              </div>
            ))}
          </div>
          <div className="card p-5">
            <div className="text-lg font-semibold mb-1">Data and privacy</div>
            <div className="text-sm text-mute">Calendar and CRM data are read at match time and not stored beyond the event title, attendees, and opportunity name on the expense. Reps can see every field the agent used. Finance cannot see calendar events the agent did not match.</div>
          </div>
        </div>
      </div>
      <div className="flex justify-end gap-2.5 mt-6">
        <button className="btn-ghost" onClick={() => get<Rules>("/settings").then(setR)}>Discard</button>
        <button className="btn" onClick={save}>{saved ? "Saved" : "Save changes"}</button>
      </div>
    </Shell>
  );
}

function Field({ label, value, onChange, prefix, suffix, inline }: { label: string; value: number; onChange: (v: number) => void; prefix?: string; suffix?: string; inline?: boolean }) {
  return (
    <div className={inline ? "flex items-center gap-3 py-3 border-b border-line-soft" : "min-w-[200px]"}>
      <div className={`text-[13px] font-semibold ${inline ? "" : "mb-1.5"}`}>{label}</div>
      <div className="h-11 rounded-xl border border-field bg-white px-3.5 flex items-center text-[15px] gap-1 w-fit">
        {prefix}<input type="number" value={value} onChange={(e) => onChange(Number(e.target.value))} className="w-24 outline-none" />{suffix && <span className="text-mute text-sm">{suffix}</span>}
      </div>
    </div>
  );
}

function Row({ t, s, on, onChange, last }: { t: string; s: string; on: boolean; onChange: (v: boolean) => void; last?: boolean }) {
  return (
    <div className={`flex items-center justify-between gap-4 py-3.5 ${last ? "" : "border-b border-line-soft"}`}>
      <div><div className="font-semibold text-[15px]">{t}</div><div className="text-[13px] text-mute">{s}</div></div>
      <button role="switch" aria-checked={on} onClick={() => onChange(!on)} className={`w-11 h-[26px] rounded-full p-[3px] flex ${on ? "bg-teal justify-end" : "bg-field justify-start"}`}><span className="w-5 h-5 rounded-full bg-white block" /></button>
    </div>
  );
}
