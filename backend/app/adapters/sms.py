"""Outbound SMS. With Twilio credentials it sends; without, it records the message and the simulator shows it."""

import logging

import httpx

from ..config import settings

log = logging.getLogger("allot.sms")


def send_sms(to: str, body: str) -> dict:
    if not (settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_from_number):
        log.info("SMS (not sent, no Twilio config) to %s: %s", to, body)
        return {"sent": False, "to": to, "body": body}
    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
    r = httpx.post(url, data={"To": to, "From": settings.twilio_from_number, "Body": body},
                   auth=(settings.twilio_account_sid, settings.twilio_auth_token), timeout=15)
    r.raise_for_status()
    return {"sent": True, "sid": r.json().get("sid")}
