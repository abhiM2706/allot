# Live texting with Twilio

Goal for Nov 19: a judge texts a photo of a receipt from their own phone, the agent replies in a few seconds, and the expense appears on the finance dashboard on screen. Start this the week of Nov 2; toll-free verification takes days, not hours.

## What you are setting up

Two channels, both hit the same webhook (`POST /sms/twilio`):

| Channel | Works when | Photos | Who can text it |
| --- | --- | --- | --- |
| **SMS/MMS on a toll-free number** | After toll-free verification is approved (free, usually a few business days) and the account is upgraded | Yes (MMS) | Anyone, once upgraded. On a trial, only up to 5 numbers you verified. |
| **WhatsApp Sandbox** | Immediately | Yes | Anyone who first sends the sandbox's join code |

Set up both. WhatsApp is the fallback if verification is still pending on demo day.

## Step 1: Twilio account (10 minutes)

1. Sign up at https://www.twilio.com/try-twilio with your phone number. Trial gives 100 messages and expires in 30 days, so do this no earlier than ~Nov 1.
2. **Upgrade** (Console → Billing → Upgrade). Load the minimum balance (about $20). This removes the "verified recipients only" restriction so judges can text without you pre-registering their numbers, and lets the agent send free-form replies. Twilio keeps your number and settings when you upgrade.
3. Copy **Account SID** and **Auth Token** from the Console home page.

## Step 2: Toll-free number + verification (10 minutes, then wait)

1. Console → Phone Numbers → Buy a number → filter **Toll-free**, capabilities **SMS** and **MMS**. Buy one (about $2/month).
2. Immediately submit **Toll-Free Verification** (Console → Messaging → Regulatory compliance → Toll-free verification). Suggested answers:
   - Business name: your name (sole proprietor) or "Allot (hackathon demo)"
   - Website: the GitHub repo URL
   - Use case: *Transactional / account notifications*
   - Use case description: *Employees text a photo of a receipt to log a business expense. The service replies with the expense details and a confirmation. One or two messages per receipt, user-initiated.*
   - Opt-in: *Users initiate by texting the number first. No marketing.*
   - Sample messages: paste two agent replies from the demo (the "Got it: $412.00 at Harbor Table..." and "Done. Logged and sent to Priya for approval." lines).
   - Monthly volume: lowest tier.
3. Status is visible on the same page. Until it is approved, SMS to US numbers is limited; the WhatsApp sandbox covers you meanwhile.

## Step 3: WhatsApp Sandbox (3 minutes)

Console → Messaging → Try it out → Send a WhatsApp message. It shows a sandbox number and a join code like `join <two-words>`. Anyone who sends that code to the sandbox number from WhatsApp can then text receipts. Set the sandbox's **"When a message comes in"** URL to your webhook (Step 5). Print the join code on a slide.

## Step 4: Configure the backend

In `backend/.env`:

```
TWILIO_ACCOUNT_SID=ACxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxx
TWILIO_FROM_NUMBER=+18885550123        # your toll-free number
TWILIO_VALIDATE_SIGNATURE=true
DEMO_FALLBACK_REP=rep_maya             # unknown numbers (judges) use Maya's calendar and accounts, each in their own thread
```

Judges' numbers are not in `fixtures/people.json`, so they are treated as "guests": they get Maya's persona (her calendar and accounts) but their own conversation thread. Those threads show up on the rep screen under **Live texts** as they arrive.

## Step 5: Expose the webhook

Twilio needs a public HTTPS URL. Two options:

**A. ngrok on the demo laptop (simplest, 2 minutes)**
```
ngrok http 8000
```
Copy the `https://....ngrok-free.app` URL. In the Console, open your number → Messaging configuration → "A message comes in" → **Webhook**, `https://....ngrok-free.app/sms/twilio`, method **POST**. Do the same for the WhatsApp sandbox. The free ngrok URL changes each restart; paste it again if you restart.

**B. Deploy the backend (always on, survives laptop sleep)**
Railway or Render, one service from the `backend/` folder, start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, env vars from Step 4 plus `ANTHROPIC_API_KEY`. Point the frontend at it with `NEXT_PUBLIC_API_URL`. Use the deployed URL as the webhook. This also means judges can keep texting it after your slot.

Check: open `https://<your-host>/sms/twilio` in a browser. It should return `{"ok": true, ...}`.

## Step 6: Test from your own phone

1. Text a receipt photo to the toll-free number (or the WhatsApp sandbox after joining).
2. Within ~5 seconds you get the agent's reply. Reply to its question.
3. On the rep screen, click the new chip under **Live texts** to see the thread. Open Approvals: the expense is there.

If nothing comes back: check the backend log for the POST; if there is a 403, the signature check failed because the public URL Twilio signed differs from what the server reconstructs (common behind some tunnels). Set `TWILIO_VALIDATE_SIGNATURE=false` for the demo and turn it back on after.

## On demo day

- Put the number and the WhatsApp join code on the first slide: "Text a receipt to +1 (888) ...".
- Keep a receipt photo in your own phone's camera roll to send if no judge volunteers.
- Keep the browser simulator open as the fallback; it is the same code path.
- A receipt a judge sends has no calendar event behind it, so the agent will ask "which account?" rather than auto-tag. That is the correct behavior and a good moment to explain the confidence rule. If you want an auto-tag live, send the Harbor Table photo yourself: its printed date matches Maya's calendar fixture.
