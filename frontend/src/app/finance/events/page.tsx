"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { get, k, pct } from "@/lib/api";
import { Shell, Stat, PageTitle, Bar, Pill } from "@/components/ui";

type Ev = { id: string; name: string; start: string; end: string; city: string; reps: string[]; spend: number; pipeline_sourced: number; ratio: number; return_per_dollar: number; reached: [string, string][] };
type Data = { events: Ev[]; totals: { spend: number; pipeline_sourced: number; ratio: number; tag_rate: number } };

export default function Events() {
  const [d, setD] = useState<Data | null>(null);
  useEffect(() => { get<Data>("/events").then(setD); }, []);
  if (!d) return <Shell><div /></Shell>;
  const best = [...d.events].sort((a, b) => b.return_per_dollar - a.return_per_dollar);
  const first = d.events.find((e) => e.reached.length) ?? d.events[0];
  return (
    <Shell>
      <PageTitle title="Events" sub="Conference and event spend against the pipeline it sourced. Sample data."
        right={<div className="flex gap-2"><Link href="/finance"><Pill>Accounts</Pill></Link><Pill on>Events</Pill><Link href="/rep"><Pill>Reps</Pill></Link></div>} />
      <div className="flex flex-wrap gap-4 mb-6">
        <Stat label="Event spend, Q4" value={k(d.totals.spend)} sub={`${d.events.length} events`} />
        <Stat label="Pipeline sourced" value={k(d.totals.pipeline_sourced)} sub="Created within 30 days of an event" />
        <Stat label="Spend as % of pipeline" value={pct(d.totals.ratio, 0)} sub="Across all events" />
        <Stat label="Receipts tagged to an event" value={pct(d.totals.tag_rate, 0)} sub="Matched by date and city" />
      </div>
      <div className="card p-5 mb-4">
        <div className="text-lg font-semibold mb-3">Events</div>
        <table className="w-full text-[15px]">
          <thead><tr className="text-left label border-b border-line"><th className="py-2 pl-2 font-semibold">EVENT</th><th className="py-2 font-semibold">PIPELINE SOURCED</th><th className="py-2 font-semibold">SPEND</th><th className="py-2 font-semibold w-[40%]">SPEND AS % OF PIPELINE</th></tr></thead>
          <tbody>
            {d.events.map((e) => { const warn = e.ratio > 0.2; return (
              <tr key={e.id} className={`border-b border-line-soft last:border-0 ${warn ? "bg-orange-soft" : ""}`}>
                <td className="py-3.5 pl-2"><div className="font-semibold">{e.name}</div><div className="text-[13px] text-mute">{fmtRange(e.start, e.end)} · {e.reps.length} reps attended</div></td>
                <td>{k(e.pipeline_sourced)}</td><td>{k(e.spend)}</td>
                <td className="pr-2"><div className="flex items-center gap-3"><Bar ratio={e.ratio} warn={warn} /><span className={`w-12 font-semibold ${warn ? "text-orange-text" : ""}`}>{pct(e.ratio, 0)}</span></div></td>
              </tr>); })}
          </tbody>
        </table>
        <div className="text-[13px] text-mute mt-3">Bar scale ends at 30%. Pipeline sourced is counted when an opportunity is created within 30 days of the event with an attendee as a contact.</div>
      </div>
      <div className="flex flex-col xl:flex-row gap-4">
        <div className="card p-5 flex-1">
          <div className="font-semibold mb-2">{first.name}: who it reached</div>
          {first.reached.map(([a, b]) => <div key={a} className="flex justify-between gap-4 py-1 text-sm"><span className="font-semibold">{a}</span><span className="text-mute text-right">{b}</span></div>)}
        </div>
        <div className="card p-5 w-full xl:w-[420px]">
          <div className="font-semibold mb-2">Suggested for next year</div>
          <div className="text-sm">{best.map((e, i) => `${e.name} returned $${e.return_per_dollar.toFixed(2)} of pipeline per $1 spent${i === best.length - 1 ? " and is the one to rethink." : "."}`).join(" ")}</div>
        </div>
      </div>
    </Shell>
  );
}

function fmtRange(s: string, e: string) {
  const a = new Date(s + "T12:00:00"), b = new Date(e + "T12:00:00");
  const m = a.toLocaleString("en-US", { month: "short" });
  return s === e ? `${m} ${a.getDate()}` : `${m} ${a.getDate()} to ${b.getDate()}`;
}
