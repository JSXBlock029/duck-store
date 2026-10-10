import base64
import io

import pytest

import duck_store
from conftest import csrf


def basic(pw):
    return {"Authorization": "Basic " + base64.b64encode(f"admin:{pw}".encode()).decode()}


def add(client, pid, qty=1, token=None):
    token = token or csrf(client)
    return client.post(f"/add_to_cart/{pid}", data={"quantity": qty, "csrf_token": token})


# ---------------- storefront ----------------

@pytest.mark.parametrize("path", ["/", "/gallery", "/gallery?category=Wild+Ducks", "/gallery?search=mallard",
                                  "/picture/1", "/cart", "/health", "/uploads/sample_mallard.jpg"])
def test_public_pages_render(client, path):
    assert client.get(path).status_code == 200


def test_unknown_picture_is_404_page(client):
    r = client.get("/picture/9999")
    assert r.status_code == 404 and b"flew away" in r.data


def test_hidden_picture_not_viewable(client, app):
    with app.app_context():
        duck_store.db.session.get(duck_store.DuckPicture, 1).is_active = False
        duck_store.db.session.commit()
    assert client.get("/picture/1").status_code == 404


# ---------------- cart ----------------

def test_post_without_csrf_rejected(client):
    assert client.post("/add_to_cart/1", data={"quantity": 1}).status_code == 400


def test_add_and_remove(client):
    t = csrf(client)
    assert add(client, 1, 2, t).status_code == 302
    r = client.get("/cart")
    assert b"Majestic Mallard" in r.data and b"19.98" in r.data
    client.post("/remove_from_cart/1", data={"csrf_token": t})
    assert b"Majestic Mallard" not in client.get("/cart").data


@pytest.mark.parametrize("qty,expected", [(-5, 1), (0, 1), (3, 3), (500, 10), ("abc", 1)])
def test_quantity_is_clamped(client, qty, expected):
    add(client, 1, qty)
    with client.session_transaction() as s:
        assert s["cart"]["1"] == expected


def test_cannot_add_missing_picture(client):
    assert add(client, 424242).status_code == 404


def test_forged_session_cart_ignored(client):
    with client.session_transaction() as s:
        s["cart"] = {"1": -3, "2": "x", "999": 1, "3": 2}
    r = client.get("/cart")
    assert b"25.98" in r.data  # only the valid line (2 x 12.99) counts


# ---------------- checkout and payments ----------------

def test_checkout_without_stripe_degrades(client):
    add(client, 1)
    r = client.get("/checkout")
    assert r.status_code == 200 and b"not enabled" in r.data
    r = client.post("/create_payment_intent", json={}, headers={"X-CSRF-Token": csrf(client)})
    assert r.status_code == 503


def test_amount_is_computed_server_side(client, fake_stripe):
    t = csrf(client)
    add(client, 3, 2, t)  # 2 x 12.99
    r = client.post("/create_payment_intent", json={"amount": 0.01, "email": "a@example.com"}, headers={"X-CSRF-Token": t})
    assert r.status_code == 200
    intent = next(iter(fake_stripe.intents.values()))
    assert intent.amount == 2598  # the browser's "amount: 0.01" is ignored


def test_paid_order_created_once_and_viewable_only_by_buyer(client, fake_stripe, app):
    t = csrf(client)
    add(client, 1, 1, t)
    client.post("/create_payment_intent", json={}, headers={"X-CSRF-Token": t})
    pid = next(iter(fake_stripe.intents))
    fake_stripe.pay(pid)

    r = client.get(f"/payment_success?payment_intent={pid}")
    assert r.status_code == 302 and "/order_confirmation/" in r.headers["Location"]
    order_path = r.headers["Location"]
    assert b"Thank you" in client.get(order_path).data

    # Reload of the success URL must not create a second order.
    client.get(f"/payment_success?payment_intent={pid}")
    with app.app_context():
        assert duck_store.Order.query.count() == 1
        order = duck_store.Order.query.one()
        assert order.total_amount == 9.99 and len(order.items) == 1

    # Download works for the buyer, not for anyone else.
    dl = f"/download/{order.id}/1"
    assert client.get(dl).status_code == 200
    stranger = app.test_client()
    assert stranger.get(order_path).status_code == 404
    assert stranger.get(dl).status_code == 404


def test_unpaid_intent_creates_no_order(client, fake_stripe, app):
    t = csrf(client)
    add(client, 1, 1, t)
    client.post("/create_payment_intent", json={}, headers={"X-CSRF-Token": t})
    pid = next(iter(fake_stripe.intents))
    client.get(f"/payment_success?payment_intent={pid}")
    with app.app_context():
        assert duck_store.Order.query.count() == 0


def test_cheap_payment_cannot_buy_expensive_cart(client, fake_stripe, app):
    """Pay for a $7.99 cart, then swap in an expensive cart before visiting the success URL."""
    t = csrf(client)
    add(client, 2, 1, t)  # 7.99
    client.post("/create_payment_intent", json={}, headers={"X-CSRF-Token": t})
    pid = next(iter(fake_stripe.intents))
    fake_stripe.pay(pid)
    with client.session_transaction() as s:
        s["cart"] = {"3": 10}  # 129.90 worth of pictures
    client.get(f"/payment_success?payment_intent={pid}")
    with app.app_context():
        order = duck_store.Order.query.one()
        assert order.total_amount == 7.99
        assert [(i.duck_picture_id, i.quantity) for i in order.items] == [(2, 1)]


def test_tampered_intent_amount_rejected(client, fake_stripe, app):
    t = csrf(client)
    add(client, 3, 1, t)
    client.post("/create_payment_intent", json={}, headers={"X-CSRF-Token": t})
    pid = next(iter(fake_stripe.intents))
    fake_stripe.pay(pid).amount_received = 50  # charged less than the items are worth
    client.get(f"/payment_success?payment_intent={pid}")
    with app.app_context():
        assert duck_store.Order.query.count() == 0


def test_unknown_or_foreign_intent_rejected(client, fake_stripe, app):
    assert client.get("/payment_success?payment_intent=pi_nope").status_code == 302
    assert client.get("/payment_success?payment_intent=not-an-intent").status_code == 302
    foreign = fake_stripe.create(amount=999, currency="usd", metadata={"items": "[[1,1,999]]"})  # no store tag
    fake_stripe.pay(foreign.id)
    client.get(f"/payment_success?payment_intent={foreign.id}")
    with app.app_context():
        assert duck_store.Order.query.count() == 0


# ---------------- admin ----------------

def test_admin_disabled_without_password(client):
    assert client.get("/admin").status_code == 403


@pytest.mark.parametrize("path", ["/admin", "/admin/pictures", "/admin/add_picture", "/admin/edit_picture/1", "/admin/orders"])
def test_admin_requires_password(client, monkeypatch, path):
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    assert client.get(path).status_code == 401
    assert client.get(path, headers=basic("wrong")).status_code == 401
    assert client.get(path, headers=basic("pw")).status_code == 200


def _png():
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), (255, 200, 0)).save(buf, format="PNG")
    buf.seek(0)
    return buf


def test_admin_upload_accepts_real_image(client, monkeypatch, app):
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    t = csrf(client)
    r = client.post("/admin/add_picture", headers=basic("pw"), content_type="multipart/form-data",
                    data={"csrf_token": t, "title": "Test Duck", "price": "4.50", "picture": (_png(), "duck.png")})
    assert r.status_code == 302
    with app.app_context():
        pic = duck_store.DuckPicture.query.filter_by(title="Test Duck").one()
        assert pic.filename.endswith(".png") and pic.filename != "duck.png"  # stored under a random name


@pytest.mark.parametrize("name,payload", [
    ("evil.html", b"<script>alert(1)</script>"),
    ("evil.svg", b"<svg onload=alert(1)></svg>"),
    ("fake.png", b"<script>not an image</script>"),
])
def test_admin_upload_rejects_non_images(client, monkeypatch, app, name, payload):
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    t = csrf(client)
    r = client.post("/admin/add_picture", headers=basic("pw"), content_type="multipart/form-data",
                    data={"csrf_token": t, "title": "Bad", "price": "4.50", "picture": (io.BytesIO(payload), name)})
    assert r.status_code == 400
    with app.app_context():
        assert duck_store.DuckPicture.query.filter_by(title="Bad").count() == 0


@pytest.mark.parametrize("name", ["duck.html", "duck.svg", "duck.php", "duck"])
def test_admin_upload_rejects_real_image_with_dangerous_extension(client, monkeypatch, app, name):
    """A valid image under a non-image extension would be served with a dangerous content type."""
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    t = csrf(client)
    r = client.post("/admin/add_picture", headers=basic("pw"), content_type="multipart/form-data",
                    data={"csrf_token": t, "title": "Sneaky", "price": "4.50", "picture": (_png(), name)})
    assert r.status_code == 400
    with app.app_context():
        assert duck_store.DuckPicture.query.filter_by(title="Sneaky").count() == 0


@pytest.mark.parametrize("price", ["-1", "0", "abc", "999999"])
def test_admin_rejects_bad_prices(client, monkeypatch, price):
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    t = csrf(client)
    r = client.post("/admin/edit_picture/1", headers=basic("pw"), data={"csrf_token": t, "title": "X", "price": price})
    assert r.status_code == 400


def test_admin_can_view_any_order(client, fake_stripe, monkeypatch, app):
    t = csrf(client)
    add(client, 1, 1, t)
    client.post("/create_payment_intent", json={}, headers={"X-CSRF-Token": t})
    pid = next(iter(fake_stripe.intents))
    fake_stripe.pay(pid)
    client.get(f"/payment_success?payment_intent={pid}")
    monkeypatch.setenv("ADMIN_PASSWORD", "pw")
    admin = app.test_client()
    assert admin.get("/order_confirmation/1", headers=basic("pw")).status_code == 200
    assert b"#1" in admin.get("/admin/orders", headers=basic("pw")).data


# ---------------- config ----------------

def test_debug_off_by_default():
    assert duck_store.app.debug is False


def test_vercel_entry_serves_same_app():
    import vercel_app
    assert vercel_app.app is duck_store.app
