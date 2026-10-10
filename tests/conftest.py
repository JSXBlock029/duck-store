"""Test setup: temp database and uploads, no network, fake Stripe."""
import os
import shutil
import socket
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
_TMP = tempfile.mkdtemp(prefix="duck-tests-")

# Configure before the app module is imported (it reads env at import time).
for k in ("STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "ADMIN_PASSWORD", "VERCEL", "VERCEL_ENV", "DATABASE_URL"):
    os.environ.pop(k, None)
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_TMP) / "test.db").replace("\\", "/")
os.environ["UPLOAD_FOLDER"] = str(Path(_TMP) / "uploads")
os.environ["SECRET_KEY"] = "test-secret"
sys.path.insert(0, str(ROOT))


def _no_network(*args, **kwargs):
    raise RuntimeError("Network access is blocked in tests")


socket.socket.connect = _no_network
socket.create_connection = _no_network

import pytest  # noqa: E402
import stripe  # noqa: E402

import duck_store  # noqa: E402

shutil.copytree(ROOT / "uploads", Path(_TMP) / "uploads", dirs_exist_ok=True)


@pytest.fixture()
def app():
    duck_store.app.config.update(TESTING=True)
    with duck_store.app.app_context():
        duck_store.db.drop_all()
    duck_store.init_db()
    yield duck_store.app


@pytest.fixture()
def client(app):
    return app.test_client()


def csrf(client):
    """Load a page so the session gets a CSRF token, then return it."""
    client.get("/")
    with client.session_transaction() as s:
        if "_csrf" not in s:
            s["_csrf"] = "tok"
        return s["_csrf"]


class FakeStripe:
    """Records PaymentIntents created by the app and lets tests decide their outcome."""

    def __init__(self):
        self.intents = {}

    def create(self, amount, currency, metadata, receipt_email=None):
        pid = f"pi_test_{len(self.intents) + 1}"
        self.intents[pid] = SimpleNamespace(id=pid, amount=amount, amount_received=0, currency=currency,
                                            metadata=dict(metadata), status="requires_payment_method",
                                            receipt_email=receipt_email, client_secret=pid + "_secret")
        return self.intents[pid]

    def retrieve(self, pid):
        if pid not in self.intents:
            raise stripe.InvalidRequestError("No such payment_intent", "id")
        return self.intents[pid]

    def pay(self, pid):
        it = self.intents[pid]
        it.status, it.amount_received = "succeeded", it.amount
        return it


@pytest.fixture()
def fake_stripe(monkeypatch):
    fake = FakeStripe()
    monkeypatch.setattr(stripe, "api_key", "sk_test_fake")
    monkeypatch.setattr(duck_store, "STRIPE_PUBLISHABLE_KEY", "pk_test_fake")
    monkeypatch.setattr(stripe.PaymentIntent, "create", staticmethod(fake.create))
    monkeypatch.setattr(stripe.PaymentIntent, "retrieve", staticmethod(fake.retrieve))
    return fake
