import Link from "next/link";

const ROLES = [
  { href: "/rep", title: "Rep", sub: "Text a receipt. The agent tags the customer and asks one question at most.", who: "Maya Okafor, Sales" },
  { href: "/approvals", title: "Manager", sub: "Approve with the account and its deal value next to every expense.", who: "Priya Shah, Sales manager" },
  { href: "/finance", title: "Finance", sub: "T&E as a share of deal value, per account and per event, flagged while the deal is open.", who: "Dana Whitfield, Finance" },
  { href: "/settings", title: "Admin", sub: "Set the limit, exceptions, and what the agent may do on its own.", who: "Admin" },
];

export default function Home() {
  return (
    <main className="min-h-screen">
      <section className="bg-teal text-white px-10 py-20">
        <div className="max-w-5xl mx-auto">
          <h1 className="text-6xl font-bold">Tabbed</h1>
          <p className="text-2xl mt-3 text-teal-tint">T&E tied to the customer it was for.</p>
          <p className="mt-8 max-w-2xl text-teal-tint">
            Ramp shows what a company spent. Tabbed adds which customer it was for and whether it was worth it: a rep texts a
            photo of a receipt, the agent matches it to a calendar event and a CRM deal, and finance sees spend against deal
            value while the deal is still open. BBS × Ramp Hackathon, Round 2. All data is sample data.
          </p>
        </div>
      </section>
      <section className="max-w-5xl mx-auto px-10 py-12 grid md:grid-cols-2 gap-4">
        {ROLES.map((r) => (
          <Link key={r.href} href={r.href} className="card p-6 hover:border-teal transition-colors">
            <div className="text-xs font-semibold text-teal-deep uppercase tracking-wider">{r.who}</div>
            <div className="text-2xl font-bold mt-1">{r.title}</div>
            <div className="text-mute mt-2">{r.sub}</div>
          </Link>
        ))}
      </section>
      <p className="max-w-5xl mx-auto px-10 pb-12 text-sm text-mute">
        Suggested walkthrough: Rep → send the Harbor Table receipt → answer who joined → Manager → approve → Finance → open Pinecrest → ask the rep → Rep again to see the question arrive.
      </p>
    </main>
  );
}
