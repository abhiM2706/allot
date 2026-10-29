# Live demo script (about 4 minutes)

Before you start: `make dev`, open http://localhost:3000 in one tab. Reset the rep thread. Have the finance overview open in a second tab.

**Open (20s).** "I use Ramp for my stipends. It tells you what was spent, not what it was for. For a sales team that means client dinners land in one T&E bucket and nobody knows until the end of the quarter whether they were worth it. Tabbed fixes that with one text message."

**Rep (60s).** Click **Rep**. "Maya just paid for dinner. She texts the receipt." Send *Harbor Table*. Read the reply aloud: it found the 7 PM calendar event, found Northwind's $240K renewal, tagged it, and asked one question. Type "Me, Dana, Chris, and Jordan from SE". Point at the memo card. "Eleven seconds. No app, no dropdown."

Send *Blue Door Coffee*. "No attendees on the calendar, so it does not guess. Three options." Type "1". "And it remembers: next time, no question." (If asked: send Blue Door again and it tags without asking.)

**Manager (40s).** Click **Go to approvals**. "Priya sees the account and its share of deal value next to every expense. The $18 coffee was approved automatically; it was under the routine threshold and the account is under its limit." Open the $412 row. Point at account context: $3.1K on $240K, 1.3%. Approve.

**Finance (70s).** Switch to the finance tab. "Every account, deal value next to T&E, the limit drawn as a marker. Pinecrest is at 28%, over the 15% limit: $9.8K on a $35K deal that is still open." Click **Ask the rep**. Point at the nine expenses, the signals (spend up, stage unchanged 75 days, close date pushed twice), and the drafted message. "The agent drafted it. Dana sends it. It never messages a rep on its own." Click **Send by text**. Switch to Rep, click **Tom Reyes**: the question has arrived.

**Events (20s).** Open **Events**. "Same idea for conferences. Chicago summit returned $8.50 of pipeline per dollar. The SF dinner returned $3.70. Next year's budget has a number behind it."

**Admin (20s).** Open **Settings**. "The limit is a share of deal value, with a flat cap for small deals and higher limits for strategic accounts. Nothing blocks the card. And finance decides what the agent may do without asking." Change the default limit to 30%, save, go back to Overview: the flag record stays, the arithmetic changes.

**Close (15s).** "Ramp already matches receipts and drafts memos. Tabbed adds the customer and the revenue behind each one. The matching is live Claude vision plus a deterministic scorer; the money rules are plain arithmetic a CFO can audit."

## If something goes wrong

- Thread looks stale: click **Reset thread**.
- Numbers off after experiments: `curl -X POST localhost:8000/admin/reset` reseeds everything.
- No model credentials on the demo machine: the sample receipts still work end to end. Only "Upload any receipt photo" needs the model credentials.
