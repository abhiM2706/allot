# Allot product brief

Oct 29, 2026 · Abhinav Malviya · BBS × Ramp Hackathon, Round 2 (technical build)

## Summary

Allot is a text-message agent that ties every sales T&E expense to the customer it was for, and shows finance that spend next to the deal's value. A rep texts a photo of a receipt. The agent reads it, matches it to a calendar event and a CRM opportunity, tags the account, writes the memo, and routes it for approval. Finance gets a per-account view of T&E as a share of deal value, with accounts over a set limit flagged while the deal is still open.

It builds on what Ramp already does well, receipt matching and memo automation, and adds the one piece that still lives in a spreadsheet: which customer the spend was for, and whether it was worth it. All names and numbers are sample data.

## The problem

Finance can see what a sales team spent, but not what it bought. Client dinners, travel, and event spend land on company cards and show up as one T&E line. The question that matters to a CFO, "are we spending $9.8K to win a $35K deal?", is answered in a spreadsheet at quarter end, if at all.

Three things keep it that way:

1. **Customer tagging is manual.** Ramp and most spend tools let admins add a customer field, but the rep has to pick the right one from a dropdown weeks after the dinner. In practice the field is blank or wrong, so finance cannot trust it.
2. **Spend and revenue live in different systems.** T&E is in Ramp. Deal value, stage, and close date are in Salesforce or HubSpot. Nothing joins them per account without someone exporting both and matching in Excel.
3. **Reviews happen after the fact.** By the time finance notices an account is over-served, the quarter has closed and the deal has been won or lost.

The cost is not only wasted spend. It is also the opposite: finance cannot tell a rep investing wisely in a $240K renewal from one burning budget on a stalled $35K deal, so both get the same blunt policy.

## Who it is for

| Person | What they do today | What Allot changes |
| --- | --- | --- |
| Sales rep (Maya, Tom) | Digs up receipts when finance pings, types "client dinner" in the memo, picks a customer from a dropdown or skips it | Texts a photo from the table. Answers one question at most. Never opens an expense app. |
| Sales manager (Priya) | Approves expenses with no context on which account or why | Sees the account, the deal value, and T&E to date beside every expense. Routine ones are approved for her. |
| Finance (Dana) | Reconciles T&E to accounts in a spreadsheet at quarter end | Sees T&E as a share of deal value per account and per event, live, with over-limit accounts flagged |
| Admin | Sets one blanket T&E policy | Sets a limit as a share of deal value, with exceptions for strategic accounts, and decides what the agent may do on its own |

The first customer is a B2B software company with 20 to 200 reps that already runs on Ramp and Salesforce.

## How it works in practice

**1. The rep texts a receipt.** Maya pays for dinner at Harbor Table and texts a photo of the receipt. Within seconds the agent replies: it read $412.00, found her 7 PM calendar event "Dinner with Northwind", found an open $240K renewal on Northwind Logistics, and is tagging the expense there. It asks one question, who joined you, because attendees are the one thing neither source reliably has. She answers in a line. The agent writes the memo and sends it to Priya.

When the agent is not sure, it asks instead of guessing. An $18.40 coffee with no attendees on the calendar gets a three-option text. Maya replies "1". The agent tags it and remembers that 1 PM coffees at Blue Door are usually that account.

**2. The manager approves.** Priya's queue shows each expense with the account and its share of deal value. Expenses under $100 and under the account limit are approved automatically. For the rest, the detail shows the memo, how the account was matched, the attendees, and the account context: $3.1K on a $240K deal is 1.3%, well under the 15% limit.

**3. Finance sees spend vs deal value.** The overview lists every account with its deal value, T&E to date, and T&E as a share of deal value, with the limit drawn as a marker on each bar. Pinecrest Health is at 28%, flagged. The account page shows the nine expenses behind the $9.8K, what the agent noticed (spend up, stage unchanged since August, close date pushed twice), and a drafted message to Tom that Dana edits and sends. The agent never messages a rep about spend on its own. Events work the same way: the Chicago summit cost $48K and sourced $410K of pipeline.

**4. The admin sets the rules.** Default limit (15% of deal value), a flat cap for small deals, higher limits for named strategic accounts, and what the agent may do without asking. Nothing is ever blocked at the card.

## What the agent does, and does not do

The agent tags an expense without asking only when a calendar event within three hours of the receipt and a CRM account on that event's attendees both point to the same customer. Anything less, and it asks the rep to pick from at most three options. Every answer is remembered for that merchant, time of day, and rep.

**It does:** read receipts, match them to calendar events and CRM opportunities, ask one clarifying question by text, draft the memo, apply the auto-approval rule, compute T&E against deal value, flag accounts over the limit, and draft a message from finance to the rep.

**It does not:** decline a card transaction, message a rep about spend on its own, change anything in the CRM, read calendar events it did not match, or store calendar and CRM data beyond the event title, attendees, and opportunity name on the expense.

## Implementation

See the README for the running architecture. In short: a FastAPI service over SQLite; adapters for CRM, calendar and SMS; an agent package with a vision receipt reader, a two-layer matcher (deterministic scorer plus Claude adjudication), and a memo drafter; and a rules module that owns every money decision with no model involved. The Next.js frontend renders the ten screens from the Figma design against the live API.

| Component | Model class | Why this and not rules |
| --- | --- | --- |
| Receipt reading | Vision-language model (Claude) | Handles itemized splits, handwritten tips, and foreign receipts that templates miss |
| Account matching | Deterministic scorer + LLM adjudication | Signals are soft; the scorer keeps it auditable, the model handles the ambiguous middle |
| Memo drafting | LLM | Short, needs the event and attendee context in natural language |
| Spend-vs-deal flag | Plain arithmetic and a threshold | Deterministic, auditable, explainable to a CFO |
| Message to the rep | LLM draft, human send | Tone matters, and finance should own the relationship |

## Key decisions

| Decision | What we chose | What we rejected, and why |
| --- | --- | --- |
| Channel for reps | SMS | A new app: reps will not install one, and Ramp already trained them to text receipts. Slack: field reps are on their phones at dinner. |
| How the customer gets identified | Calendar event plus CRM attendees, with one question when unsure | A dropdown at submission time: the status quo, stays blank. Asking every time: too much friction. |
| What to measure | T&E as a share of open deal value, per account | Spend per rep: Ramp already shows it and it says nothing about worth. Spend vs closed revenue: too late to act. |
| What the limit does | Flags and asks; never blocks the card | A rep at a client dinner cannot have the card fail. |
| Who messages the rep | Finance, from a drafted text | A bot questioning a rep's spend would be resented and ignored. |
| Scope of calendar access | The rep's own calendar, read at match time, title and attendees only | Full calendar sync: more than needed; reps would object. |
| Where it runs | A service on Ramp's API, written back into Ramp fields | A separate expense system duplicates Ramp and splits the ledger. |

## Roadmap

- **Pilot (weeks 1 to 8, one team of 10):** SMS capture, calendar match, Salesforce read-only, finance overview. Gate: 85% tagged without a question; reps still texting after week 4.
- **V1 (months 3 to 6, whole sales org):** auto-approve routine spend, events and pipeline sourced, per-tier limits, HubSpot and Outlook. Gate: finance acts on a flag in under a week.
- **V2 (months 6 to 12):** event budgets from last year's ratio, win-rate vs T&E by segment, pre-trip budgets suggested by deal, pipeline-weighted limits.

## Risks

| Risk | What we do about it |
| --- | --- |
| Match accuracy is lower than the demo suggests | Auto-tag only when calendar and CRM agree; store the evidence; raise the threshold if reps correct more than 1 in 20 |
| Reps feel surveilled | Own calendar only, at match time; reps see every field used; finance never sees unmatched events; the limit asks, never blocks |
| The ratio misleads on long cycles | Per-account overrides, a flat cap for small deals, "mark as expected" with a recorded reason |
| Deal value in the CRM is stale | Show sync time and stage beside the number; weight by stage in V2 |
| Ramp builds this | That is the pitch: a connector plus a report on top of what Ramp has |

## Success measures (pilot targets)

Receipts tagged without a question: 85%. Rep corrections of an automatic tag: under 5%. Receipt to approved expense: under 24 hours. Reps still texting in week 8: 90%. Flags acted on within a week: 80%. Finance hours on T&E-to-account reconciliation at quarter end: zero.
