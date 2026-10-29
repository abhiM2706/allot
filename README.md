# Tabbed

**T&E tied to the customer it was for.**

Ramp shows what a company spent. Tabbed adds which customer it was for and whether it was worth it. A sales rep texts a photo of a receipt. An agent reads it, matches it to a calendar event and a CRM opportunity, tags the account, writes the memo, and routes it for approval. Finance sees T&E as a share of each account's deal value, with accounts over a limit flagged while the deal is still open.

Built for the BBS × Ramp Hackathon (Round 2, technical build). All names, accounts, deals and dollar figures are sample data.

> **Try it in 60 seconds:** `make dev` (or the two commands under *Run it*), open http://localhost:3000, click **Rep**, send the Harbor Table receipt, answer "Me, Dana, Chris, and Jordan", then click through **Manager → Finance → Pinecrest Health → Send by text**.

---

## What is real and what is mocked

| Piece | Status |
| --- | --- |
| Receipt reading from a photo | **Real.** Claude Sonnet 4.5 vision, via Amazon Bedrock (default) or the Anthropic API. Without credentials, the three sample receipts carry a JSON sidecar so the rest of the pipeline still runs. |
| Account matching | **Real.** Deterministic scorer (calendar time gap, attendee email domains, event title, rep memory, ownership) plus Claude adjudication when a key is set. The model can lower confidence; it cannot raise it above the evidence. |
| One-question fallback | **Real.** Below the confidence threshold the agent texts up to three options and remembers the answer per merchant, hour and rep. |
| Memo drafting | **Real.** Claude when available, template otherwise. |
| Auto-approval, spend-vs-deal ratio, limit flag | **Real.** Plain arithmetic in `backend/app/rules.py`. No model touches money decisions. |
| Manager queue, finance overview, account detail, events, settings | **Real.** Computed from SQLite on every request. Settings changes recompute every flag. |
| SMS | **Real, optional.** `/sms/twilio` is a Twilio webhook. The browser simulator calls the same handler, so the demo does not depend on a phone number. |
| Salesforce, Google Calendar | **Fixtures.** `backend/fixtures/accounts.json` and `calendar.json`, read through adapter classes in `backend/app/adapters/`. A live integration implements the same two or three methods. |
| Ramp | **Not connected in the demo.** The design writes the account and memo back to a Ramp custom accounting field via the Ramp API; here the expense table stands in for it. |

## Run it

Requirements: Python 3.11+, Node 20+.

```bash
# backend
cd backend
pip install -r requirements.txt
cp .env.example .env            # add your Bedrock key (see below), or set PROVIDER=mock
python fixtures/make_receipts.py # generates the three sample receipt photos
uvicorn app.main:app --reload --port 8000

# frontend (second terminal)
cd frontend
npm install
npm run dev                      # http://localhost:3000
```

Tests (no API key needed):

```bash
cd backend && PROVIDER=mock pytest -q
```

Six scenario tests cover: seed numbers match the design, dinner with calendar + CRM auto-tags, coffee without attendees asks and then remembers, over-limit accounts never auto-approve, "not a customer expense" is left untagged, raising the limit changes arithmetic but not history.

### Environment variables (`backend/.env`)

| Variable | Default | Notes |
| --- | --- | --- |
| `PROVIDER` | `bedrock` | `bedrock`, `anthropic` or `mock`. With no credentials for the chosen provider, the code falls back to mock. |
| `AWS_REGION` | `us-west-2` | Bedrock region. |
| `AWS_BEARER_TOKEN_BEDROCK` | — | A Bedrock API key (bearer token). Simplest option. |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` | — | Alternative to the bearer token. Leave all blank to use `~/.aws/credentials` or an instance role. |
| `BEDROCK_MODEL` | `global.anthropic.claude-sonnet-4-5-20250929-v1:0` | Sonnet 4.5 on Bedrock requires an inference profile prefix (`global.`, `us.`, `eu.`). |
| `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | — | Only if `PROVIDER=anthropic`. |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` | — | Set all three to send real texts. Point your Twilio number's messaging webhook at `POST https://<your-host>/sms/twilio`. Rep phone numbers live in `fixtures/people.json`. |

### Going live with Twilio for the demo

1. Create a Twilio trial number and set the three env vars.
2. Expose the backend (`ngrok http 8000`) and set the number's webhook to `https://<ngrok>/sms/twilio`.
3. Put a judge's phone number on one of the reps in `fixtures/people.json`, restart, and have them text a receipt photo.

## How it works

```
 rep's phone ──SMS/photo──▶ /sms/twilio ─┐
 browser simulator ──────▶ /sms/simulate ─┴─▶ conversation.py (state machine per rep)
                                                 │
                                                 ├─ receipt.py   vision model → merchant, total, time, guests
                                                 ├─ matcher.py   calendar ±3h + CRM domains + memory → candidates
                                                 │               score ≥ 0.80 and clear lead → tag, ask "who joined?"
                                                 │               otherwise → ask "which account?" (≤3 options)
                                                 ├─ memo.py      one-line memo from event + attendees + receipt
                                                 └─ rules.py     auto-approve? ratio = T&E / deal value; over limit → flag
                                                                       │
 manager queue ◀── /approvals ─────────────────────────────────────────┤
 finance overview ◀── /accounts, /accounts/{id}, /events ──────────────┤
 admin ◀── /settings (limits, exceptions, agent permissions) ──────────┘
```

The agent tags an expense without asking only when a calendar event within three hours of the receipt and a CRM account on that event's attendees both point to the same customer. Everything that touches money or people is either arithmetic (`rules.py`) or a human action (approve, send the drafted message).

### Repo layout

```
backend/
  app/
    main.py            FastAPI routes, grouped by who uses them
    rules.py           limit, ratio, auto-approve, flag (no model)
    db.py              SQLite schema + seed from fixtures
    agent/
      conversation.py  SMS state machine
      receipt.py       vision receipt reading (+ sidecar fallback)
      matcher.py       candidate scoring + optional LLM adjudication
      memo.py          memo drafting
      llm.py           Anthropic wrapper
    adapters/          crm.py, calendar.py, sms.py (swap fixtures for live systems here)
  fixtures/            accounts, calendar, people, events, seed expenses, sample receipts
  tests/               six scenario tests
frontend/
  src/app/rep          phone simulator + onboarding + "my expenses"
  src/app/approvals    manager queue and detail
  src/app/finance      overview, account detail, events
  src/app/settings     admin
```

## Decisions

| Decision | Chose | Rejected |
| --- | --- | --- |
| Channel for reps | SMS | A new app (reps will not install one; Ramp already trained them to text receipts). Slack (field reps are on their phones at dinner). |
| Identifying the customer | Calendar event + CRM attendees, one question when unsure | A dropdown at submission (the status quo, stays blank). Asking every time (the point is to ask rarely). |
| What to measure | T&E as a share of open deal value per account | Spend per rep (Ramp shows it, says nothing about worth). Spend vs closed revenue (too late to act). |
| What the limit does | Flags and asks, never blocks | Declining the card at a client dinner. |
| Who messages the rep | Finance, from a drafted text | The agent on its own (would be resented and ignored). |
| Where the model is allowed | Reading, matching, drafting | Approval, flagging and money math stay deterministic and auditable. |
| Heuristic + LLM, not LLM alone | Scorer always runs; the model adjudicates and explains | An LLM-only matcher is hard to audit and fails silently when the key or network is down. |

## Roadmap

- **Pilot (weeks 1–8, one team):** SMS capture, calendar match, Salesforce read-only, finance overview. Gate: 85% tagged without a question, reps still texting in week 4.
- **V1 (months 3–6, whole org):** auto-approve, events and pipeline sourced, per-tier limits, HubSpot and Outlook. Gate: finance acts on a flag within a week.
- **V2 (months 6–12):** event budgets from last year's ratio, pre-trip budgets by deal, pipeline-weighted limits.

## Links

- Figma prototype (Round 1 design, the spec for these screens): https://www.figma.com/design/iBnb9LwxvfHa7Vnkky2Vec
- Product brief: see `docs/brief.md`

Ramp capabilities referenced (SMS receipt submission, memo automation, custom accounting fields, policy agents) are from Ramp's public help center and product pages as of October 2026. The gap this fills, spend tied to deal value per account, is one I could not find in public documentation.
