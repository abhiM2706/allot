"""Twilio webhook: signature validation, WhatsApp prefix, and guest numbers get their own thread."""

import base64
import hashlib
import hmac
import os

os.environ["PROVIDER"] = "mock"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
URL = "http://testserver/sms/twilio"


@pytest.fixture(autouse=True)
def _setup():
    # settings is a module singleton shared with other test files, so set it here rather than via env vars
    settings.twilio_auth_token, settings.twilio_validate_signature, settings.demo_fallback_rep = "test-token", True, "rep_maya"
    client.post("/admin/reset")
    yield


def sign(form: dict) -> str:
    payload = URL + "".join(k + form[k] for k in sorted(form))
    return base64.b64encode(hmac.new(b"test-token", payload.encode(), hashlib.sha1).digest()).decode()


def post(form, signed=True):
    headers = {"X-Twilio-Signature": sign(form)} if signed else {}
    return client.post("/sms/twilio", data=form, headers=headers)


def test_rejects_unsigned_requests():
    r = post({"From": "+15105550101", "Body": "hi", "NumMedia": "0"}, signed=False)
    assert r.status_code == 403


def test_known_rep_gets_twiml_reply():
    r = post({"From": "+15105550101", "Body": "hello", "NumMedia": "0"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/xml")
    assert "<Message>" in r.text and "photo of a receipt" in r.text


def test_whatsapp_prefix_and_guest_numbers_get_own_thread():
    r = post({"From": "whatsapp:+14155550999", "Body": "hello", "NumMedia": "0"})
    assert r.status_code == 200 and "photo of a receipt" in r.text
    # the guest has a thread keyed by their number, not Maya's
    rows = client.get("/thread/guest:+14155550999").json()
    assert [m["direction"] for m in rows] == ["in", "out"]
    assert client.get("/thread/rep_maya").json() == []


def test_get_on_webhook_explains_itself():
    assert client.get("/sms/twilio").json()["ok"] is True
