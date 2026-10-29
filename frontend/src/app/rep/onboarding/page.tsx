import Link from "next/link";
import { Phone } from "@/components/ui";

const STEPS = [
  { n: "✓", t: "Ramp card", s: "Maya Okafor, Sales. Connected by your admin.", done: true },
  { n: "✓", t: "Google Calendar", s: "We read event titles and attendees to match a receipt to a meeting. Your calendar only, at match time.", done: true },
  { n: "3", t: "Salesforce", s: "Read-only. We look up open opportunities on your accounts.", cta: true },
  { n: "4", t: "Verify your number", s: "Receipts come from +1 (510) 555-0142", dim: true },
];

export default function Onboarding() {
  return (
    <div className="min-h-screen flex items-center justify-center p-10 gap-10">
      <Phone>
        <div className="flex-1 p-5 pt-7 flex flex-col gap-4">
          <div className="w-[52px] h-[52px] rounded-full bg-teal text-white text-2xl font-bold flex items-center justify-center">A</div>
          <div><div className="text-[26px] font-bold leading-tight">Set up Allot</div><div className="text-[15px] text-mute mt-1.5">Three connections, then you only ever text us a photo.</div></div>
          {STEPS.map((s) => (
            <div key={s.t} className={`card p-4 flex gap-3.5 ${s.dim ? "opacity-60" : ""}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shrink-0 ${s.done ? "bg-teal text-white" : "bg-teal-tint text-teal-deep"}`}>{s.n}</div>
              <div className="flex-1"><div className="font-semibold">{s.t}</div><div className="text-[13px] text-mute">{s.s}</div>
                {s.cta && <button className="btn h-10 text-sm mt-3 w-full">Connect Salesforce</button>}</div>
            </div>
          ))}
        </div>
        <div className="bg-white border-t border-line px-5 pt-3 pb-5 flex gap-2.5">
          <Link href="/rep" className="btn-ghost flex-1 h-12">Skip for now</Link>
          <Link href="/rep" className="btn flex-1 h-12">Continue</Link>
        </div>
      </Phone>
      <div className="max-w-sm text-sm text-mute">
        <p>In the demo the integrations are fixtures: <code>fixtures/calendar.json</code> and <code>fixtures/accounts.json</code>. The adapter interfaces in <code>backend/app/adapters/</code> are what a live Google Calendar and Salesforce connection would implement.</p>
      </div>
    </div>
  );
}
