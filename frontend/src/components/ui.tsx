"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

export function Phone({ children, title, sub, clock = "9:41" }: { children: React.ReactNode; title?: string; sub?: string; clock?: string }) {
  return (
    <div className="w-[390px] h-[844px] bg-bg rounded-[40px] border-[10px] border-ink overflow-hidden flex flex-col shadow-2xl shrink-0">
      <div className="h-[54px] px-6 pt-4 flex justify-between font-semibold text-[15px]"><span>{clock}</span><span className="text-[13px]">●●● 100%</span></div>
      {title && (
        <div className="bg-white border-b border-line px-5 pt-2.5 pb-3.5 flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-teal text-white font-bold flex items-center justify-center">T</div>
          <div><div className="font-semibold">{title}</div><div className="text-[13px] text-mute">{sub}</div></div>
        </div>
      )}
      <div className="flex-1 min-h-0 flex flex-col">{children}</div>
      <div className="h-7 flex items-center justify-center"><div className="w-[134px] h-[5px] rounded bg-ink" /></div>
    </div>
  );
}

export function Header({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div className="bg-white border-b border-line px-5 pt-2.5 pb-3.5">
      <div className="text-[13px] text-mute">{eyebrow}</div>
      <div className="text-xl font-bold">{title}</div>
    </div>
  );
}

export function Bar({ ratio, limit, warn, scale = 0.3 }: { ratio: number; limit?: number; warn?: boolean; scale?: number }) {
  const w = Math.min(100, (ratio / scale) * 100);
  return (
    <div className="relative h-2.5 rounded-full bg-track flex-1">
      <div className={`h-2.5 rounded-full ${warn ? "bg-orange" : "bg-teal"}`} style={{ width: `${Math.max(w, 1.5)}%` }} />
      {limit !== undefined && <div className="absolute -top-[3px] w-0.5 h-4 bg-ink" style={{ left: `${(limit / scale) * 100}%` }} />}
    </div>
  );
}

const NAV = [
  ["Overview", "/finance"],
  ["Accounts", "/finance/accounts"],
  ["Events", "/finance/events"],
  ["Approvals", "/approvals"],
  ["Reps", "/rep"],
  ["Settings", "/settings"],
];

export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  return (
    <div className="min-h-screen flex">
      <aside className="w-60 bg-white border-r border-line p-4 flex flex-col gap-1 shrink-0">
        <Link href="/" className="flex items-center gap-2.5 px-2 pb-5">
          <div className="w-8 h-8 rounded-full bg-teal text-white text-sm font-bold flex items-center justify-center">T</div>
          <span className="font-semibold">Tabbed</span>
        </Link>
        {NAV.map(([n, href]) => {
          const active = href === "/finance" ? path === "/finance" : path.startsWith(href);
          return (
            <Link key={n} href={href} className={`px-3 py-2.5 rounded-lg text-sm ${active ? "bg-teal-tint text-teal-deep font-semibold" : "font-medium"}`}>
              {n}
            </Link>
          );
        })}
        <div className="mt-auto px-2 pt-3">
          <div className="text-[13px] font-semibold">Dana Whitfield</div>
          <div className="text-xs text-mute">Finance · Acme Software</div>
        </div>
      </aside>
      <main className="flex-1 px-10 py-8 min-w-0">{children}</main>
    </div>
  );
}

export function Stat({ label, value, sub, warn }: { label: string; value: string; sub: string; warn?: boolean }) {
  return (
    <div className="card p-[18px] flex-1 min-w-[200px]">
      <div className="text-[13px] text-mute">{label}</div>
      <div className={`text-3xl font-bold leading-tight my-1 ${warn ? "text-orange-text" : ""}`}>{value}</div>
      <div className="text-[13px] text-mute">{sub}</div>
    </div>
  );
}

export function PageTitle({ title, sub, right }: { title: string; sub?: string; right?: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3 mb-6">
      <div>
        <div className="text-sm font-semibold text-teal-deep">Tabbed</div>
        <h1 className="text-3xl font-bold leading-tight">{title}</h1>
        {sub && <div className="text-sm text-mute mt-1">{sub}</div>}
      </div>
      {right}
    </div>
  );
}

export function Pill({ children, on }: { children: React.ReactNode; on?: boolean }) {
  return <span className={`inline-flex items-center h-9 px-3.5 rounded-full text-sm font-semibold ${on ? "bg-ink text-white" : "bg-white border border-field"}`}>{children}</span>;
}
