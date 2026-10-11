#!/usr/bin/env python3
"""
Duck Picture Store
A small Flask shop that sells duck pictures with Stripe card payments.

Security model, in short:
- Prices and totals are always computed on the server. The browser never sends an amount.
- An order is created only from a Stripe PaymentIntent this server created, after Stripe
  reports it succeeded, and only once per PaymentIntent.
- A customer can only view the orders placed from their own session.
- Every POST form carries a CSRF token. The admin area needs ADMIN_PASSWORD.
"""

import hmac
import json
import os
import secrets
import uuid
from datetime import datetime, timezone

import stripe
from flask import (Flask, Response, abort, flash, jsonify, redirect, render_template,
                   request, send_from_directory, session, url_for)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # optional in production
    pass

ON_VERCEL = bool(os.getenv("VERCEL") or os.getenv("VERCEL_ENV"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or secrets.token_hex(32)
def database_url(env=os.environ, on_vercel=ON_VERCEL):
    """Database URL for this environment.

    A relative SQLite URL makes Flask-SQLAlchemy create an instance/ folder next to the
    app. Vercel's app directory is read-only, so that crashes the function at import;
    there, a relative SQLite file is moved to /tmp (writable, but reset between cold
    starts: set DATABASE_URL to Postgres for orders that must persist).
    """
    url = env.get("DATABASE_URL") or "sqlite:///duck_store.db"
    # Hosted Postgres (Vercel Storage, Neon, Supabase) hands out postgres:// or postgresql://
    # URLs. Pin them to the psycopg 3 driver that requirements.txt installs.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+psycopg://" + url[len(prefix):]
    if on_vercel and url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
        name = url[len("sqlite:///"):].strip("/").replace("/", "_") or "duck_store.db"
        url = "sqlite:////tmp/" + name
    return url


app.config["SQLALCHEMY_DATABASE_URI"] = database_url()
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_FOLDER") or ("/tmp/uploads" if ON_VERCEL else os.path.join(BASE_DIR, "uploads"))
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = ON_VERCEL

db = SQLAlchemy(app)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY") or None
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
CURRENCY = "usd"

MAX_QTY_PER_ITEM = 10
MAX_CART_LINES = 20
ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp"}

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


def _utcnow():
    return datetime.now(timezone.utc)


def stripe_configured():
    return bool(stripe.api_key and STRIPE_PUBLISHABLE_KEY)


# --------------------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=_utcnow)
    orders = db.relationship("Order", backref="user", lazy=True)


class DuckPicture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    filename = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50))
    tags = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=_utcnow)
    order_items = db.relationship("OrderItem", backref="duck_picture", lazy=True)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Guest checkout: there is no account system yet, so user_id stays empty.
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    customer_email = db.Column(db.String(254))
    stripe_payment_intent_id = db.Column(db.String(255), unique=True)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=_utcnow)
    items = db.relationship("OrderItem", backref="order", lazy=True)


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    duck_picture_id = db.Column(db.Integer, db.ForeignKey("duck_picture.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Float, nullable=False)


# --------------------------------------------------------------------------------------
# Security helpers
# --------------------------------------------------------------------------------------

def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token
app.jinja_env.globals["stripe_configured"] = stripe_configured


@app.before_request
def _protect():
    # Admin area: HTTP Basic auth against ADMIN_PASSWORD; disabled when unset.
    if request.path.startswith("/admin"):
        expected = os.getenv("ADMIN_PASSWORD", "")
        if not expected:
            return Response("Admin is disabled. Set ADMIN_PASSWORD to enable it.", 403)
        auth = request.authorization
        if not (auth and auth.password and hmac.compare_digest(auth.password.encode(), expected.encode())):
            return Response("Admin login required", 401, {"WWW-Authenticate": 'Basic realm="admin"'})
    # CSRF: every state-changing request must echo the session token.
    if request.method == "POST":
        sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
        if not sent or not hmac.compare_digest(sent, session.get("_csrf", "")):
            abort(400, description="Invalid or missing CSRF token. Reload the page and try again.")
    return None


def _is_admin_request():
    expected = os.getenv("ADMIN_PASSWORD", "")
    auth = request.authorization
    return bool(expected and auth and auth.password and hmac.compare_digest(auth.password.encode(), expected.encode()))


# --------------------------------------------------------------------------------------
# Cart helpers (all money math happens here, on the server)
# --------------------------------------------------------------------------------------

def _cents(dollars):
    return int(round(float(dollars) * 100))


def _cart():
    raw = session.get("cart", {})
    return raw if isinstance(raw, dict) else {}


def _cart_lines():
    """Validated cart lines with current server-side prices, plus the total in cents."""
    lines, total_cents = [], 0
    for pid, qty in _cart().items():
        try:
            pid, qty = int(pid), int(qty)
        except (TypeError, ValueError):
            continue
        if qty < 1:
            continue
        picture = db.session.get(DuckPicture, pid)
        if not picture or not picture.is_active:
            continue
        qty = min(qty, MAX_QTY_PER_ITEM)
        subtotal_cents = _cents(picture.price) * qty
        total_cents += subtotal_cents
        lines.append({
            "id": picture.id, "title": picture.title, "filename": picture.filename,
            "price": picture.price, "quantity": qty, "subtotal": subtotal_cents / 100,
        })
    return lines, total_cents


def _remember_order(order_id):
    ids = list(session.get("orders", []))
    if order_id not in ids:
        ids.append(order_id)
    session["orders"] = ids[-50:]


# --------------------------------------------------------------------------------------
# Routes: storefront
# --------------------------------------------------------------------------------------

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], secure_filename(filename))


@app.route("/health")
def health():
    return jsonify({"status": "ok", "payments": "configured" if stripe_configured() else "disabled"})


@app.route("/")
def index():
    featured = DuckPicture.query.filter_by(is_active=True).limit(6).all()
    categories = [c[0] for c in db.session.query(DuckPicture.category).distinct().all() if c[0]]
    return render_template("index.html", pictures=featured, categories=categories)


@app.route("/gallery")
def gallery():
    page = request.args.get("page", 1, type=int)
    category = request.args.get("category", "")
    search = request.args.get("search", "")
    query = DuckPicture.query.filter_by(is_active=True)
    if category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(DuckPicture.title.contains(search)
                             | DuckPicture.description.contains(search)
                             | DuckPicture.tags.contains(search))
    pictures = query.paginate(page=page, per_page=12, error_out=False)
    categories = [c[0] for c in db.session.query(DuckPicture.category).distinct().all() if c[0]]
    return render_template("gallery.html", pictures=pictures, categories=categories,
                           current_category=category, search=search)


@app.route("/picture/<int:picture_id>")
def picture_detail(picture_id):
    picture = db.session.get(DuckPicture, picture_id)
    if not picture or not picture.is_active:
        abort(404)
    related = DuckPicture.query.filter(DuckPicture.category == picture.category,
                                       DuckPicture.id != picture.id,
                                       DuckPicture.is_active.is_(True)).limit(4).all()
    return render_template("picture_detail.html", picture=picture, related_pictures=related)


@app.route("/cart")
def cart():
    lines, total_cents = _cart_lines()
    return render_template("cart.html", cart_items=lines, total=total_cents / 100)


@app.route("/add_to_cart/<int:picture_id>", methods=["POST"])
def add_to_cart(picture_id):
    picture = db.session.get(DuckPicture, picture_id)
    if not picture or not picture.is_active:
        abort(404)
    try:
        qty = int(request.form.get("quantity", 1))
    except ValueError:
        qty = 1
    qty = max(1, min(qty, MAX_QTY_PER_ITEM))
    cart = _cart()
    key = str(picture_id)
    if key not in cart and len(cart) >= MAX_CART_LINES:
        flash(f"Your cart is limited to {MAX_CART_LINES} different pictures.", "error")
        return redirect(url_for("cart"))
    cart[key] = min(int(cart.get(key, 0)) + qty, MAX_QTY_PER_ITEM)
    session["cart"] = cart
    flash("Picture added to cart!", "success")
    return redirect(url_for("picture_detail", picture_id=picture_id))


@app.route("/remove_from_cart/<int:picture_id>", methods=["POST"])
def remove_from_cart(picture_id):
    cart = _cart()
    if cart.pop(str(picture_id), None) is not None:
        session["cart"] = cart
        flash("Picture removed from cart!", "success")
    return redirect(url_for("cart"))


@app.route("/checkout")
def checkout():
    lines, total_cents = _cart_lines()
    if not lines:
        flash("Your cart is empty!", "error")
        return redirect(url_for("cart"))
    return render_template("checkout.html", cart_items=lines, total=total_cents / 100,
                           stripe_key=STRIPE_PUBLISHABLE_KEY)


@app.route("/create_payment_intent", methods=["POST"])
def create_payment_intent():
    """Create a PaymentIntent for the current cart. The amount is computed here, never sent by the browser."""
    if not stripe_configured():
        return jsonify({"error": "Payments are not configured on this store yet."}), 503
    lines, total_cents = _cart_lines()
    if not lines:
        return jsonify({"error": "Your cart is empty."}), 400
    if total_cents < 50:  # Stripe's minimum charge in USD
        return jsonify({"error": "The order total is below the minimum card charge."}), 400
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", ""))[:254]
    items = json.dumps([[l["id"], l["quantity"], _cents(l["price"])] for l in lines], separators=(",", ":"))
    try:
        intent = stripe.PaymentIntent.create(
            amount=total_cents,
            currency=CURRENCY,
            receipt_email=email or None,
            metadata={"items": items, "store": "duck-store"},
        )
    except stripe.StripeError:
        app.logger.exception("Stripe error creating PaymentIntent")
        return jsonify({"error": "The payment provider could not start the payment. Please try again."}), 502
    return jsonify({"clientSecret": intent.client_secret})


@app.route("/payment_success")
def payment_success():
    """Turn a succeeded PaymentIntent into exactly one order, built from the intent itself."""
    intent_id = request.args.get("payment_intent", "")
    if not intent_id.startswith("pi_") or not stripe_configured():
        flash("Payment verification failed!", "error")
        return redirect(url_for("index"))

    existing = Order.query.filter_by(stripe_payment_intent_id=intent_id).first()
    if existing:
        # Reloading the success page must not create a second order.
        if existing.id in session.get("orders", []):
            return redirect(url_for("order_confirmation", order_id=existing.id))
        flash("This payment has already been recorded.", "info")
        return redirect(url_for("index"))

    try:
        intent = stripe.PaymentIntent.retrieve(intent_id)
    except stripe.StripeError:
        app.logger.exception("Stripe error retrieving PaymentIntent")
        flash("We could not verify the payment. If you were charged, contact us with your receipt.", "error")
        return redirect(url_for("checkout"))

    meta = dict(getattr(intent, "metadata", None) or {})
    if (getattr(intent, "status", None) != "succeeded" or getattr(intent, "currency", None) != CURRENCY
            or meta.get("store") != "duck-store"):
        flash("Payment failed! Please try again.", "error")
        return redirect(url_for("checkout"))

    try:
        items = json.loads(meta.get("items", "[]"))
    except ValueError:
        items = []
    expected_cents = sum(int(q) * int(c) for _, q, c in items)
    if not items or expected_cents != int(getattr(intent, "amount_received", 0) or getattr(intent, "amount", 0)):
        app.logger.error("PaymentIntent %s amount does not match its items", intent_id)
        flash("Payment could not be matched to an order. Please contact us with your receipt.", "error")
        return redirect(url_for("index"))

    order = Order(stripe_payment_intent_id=intent_id, total_amount=expected_cents / 100,
                  status="completed", customer_email=getattr(intent, "receipt_email", None))
    db.session.add(order)
    db.session.flush()
    for pid, qty, unit_cents in items:
        if db.session.get(DuckPicture, int(pid)):
            db.session.add(OrderItem(order_id=order.id, duck_picture_id=int(pid),
                                     quantity=int(qty), price=int(unit_cents) / 100))
    db.session.commit()

    session.pop("cart", None)
    _remember_order(order.id)
    flash("Payment successful! Your duck pictures are ready for download.", "success")
    return redirect(url_for("order_confirmation", order_id=order.id))


@app.route("/order_confirmation/<int:order_id>")
def order_confirmation(order_id):
    if order_id not in session.get("orders", []) and not _is_admin_request():
        abort(404)
    order = db.session.get(Order, order_id) or abort(404)
    return render_template("order_confirmation.html", order=order)


@app.route("/download/<int:order_id>/<int:picture_id>")
def download(order_id, picture_id):
    """Paid pictures can be downloaded from the session that bought them."""
    if order_id not in session.get("orders", []):
        abort(404)
    order = db.session.get(Order, order_id) or abort(404)
    item = next((i for i in order.items if i.duck_picture_id == picture_id), None)
    if not item or order.status != "completed":
        abort(404)
    if item.duck_picture.filename.startswith("https://"):
        return redirect(item.duck_picture.filename)
    return send_from_directory(app.config["UPLOAD_FOLDER"], item.duck_picture.filename, as_attachment=True)


# --------------------------------------------------------------------------------------
# Routes: admin (protected in _protect)
# --------------------------------------------------------------------------------------

def _parse_price(raw):
    try:
        price = round(float(raw), 2)
    except (TypeError, ValueError):
        return None
    return price if 0.5 <= price <= 10000 else None


IMAGE_CONTENT_TYPES = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                       "gif": "image/gif", "webp": "image/webp"}
BLOB_API_URL = "https://vercel.com/api/blob"
BLOB_API_VERSION = "12"   # matches @vercel/blob 2.8.1, the reference for this request format


def blob_put(pathname, data, content_type):
    """Upload bytes to Vercel Blob (public) and return the file's permanent URL.

    Vercel has no official Python SDK; this is the same request @vercel/blob's put()
    sends. The token (set when a Blob store is connected to the project) looks like
    vercel_blob_rw_<storeId>_<secret>.
    """
    import urllib.parse
    import urllib.request

    token = os.environ["BLOB_READ_WRITE_TOKEN"]
    parts = token.split("_")
    store_id = parts[3] if len(parts) > 3 else ""
    req = urllib.request.Request(
        f"{BLOB_API_URL}/?{urllib.parse.urlencode({'pathname': pathname})}",
        data=data,
        method="PUT",
        headers={
            "authorization": f"Bearer {token}",
            "x-api-version": BLOB_API_VERSION,
            "x-vercel-blob-store-id": store_id,
            "x-vercel-blob-access": "public",
            "x-content-type": content_type,
            "x-add-random-suffix": "1",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        url = json.loads(resp.read().decode("utf-8"))["url"]
    if not url.startswith("https://"):
        raise ValueError("unexpected Blob response")
    return url


def picture_src(filename):
    """Where the browser loads a picture from: a Blob URL as-is, a local file via /uploads."""
    if str(filename).startswith("https://"):
        return filename
    return url_for("uploaded_file", filename=filename)


app.jinja_env.globals["picture_src"] = picture_src


def _save_image(file):
    """Store an uploaded image under a random name. Returns the filename, or None if it is not a real image."""
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_IMAGE_EXT:
        return None
    data = file.read()
    try:
        from io import BytesIO
        from PIL import Image
        Image.open(BytesIO(data)).verify()
    except Exception:
        return None
    name = f"{uuid.uuid4().hex}.{ext}"
    if os.getenv("BLOB_READ_WRITE_TOKEN"):
        return blob_put(f"pictures/{name}", data, IMAGE_CONTENT_TYPES[ext])
    with open(os.path.join(app.config["UPLOAD_FOLDER"], name), "wb") as fh:
        fh.write(data)
    return name


@app.route("/admin")
def admin():
    total_revenue = db.session.query(db.func.sum(Order.total_amount)).filter_by(status="completed").scalar() or 0
    return render_template("admin.html",
                           total_pictures=DuckPicture.query.count(),
                           total_orders=Order.query.count(),
                           total_revenue=total_revenue,
                           recent_orders=Order.query.order_by(Order.created_at.desc()).limit(5).all())


@app.route("/admin/pictures")
def admin_pictures():
    pictures = DuckPicture.query.order_by(DuckPicture.created_at.desc()).all()
    return render_template("admin_pictures.html", pictures=pictures)


@app.route("/admin/add_picture", methods=["GET", "POST"])
def admin_add_picture():
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        price = _parse_price(request.form.get("price"))
        file = request.files.get("picture")
        if not title or price is None:
            flash("Title and a price between $0.50 and $10,000 are required.", "error")
            return render_template("admin_add_picture.html", form=request.form), 400
        if not file or not file.filename:
            flash("No picture file selected!", "error")
            return render_template("admin_add_picture.html", form=request.form), 400
        try:
            filename = _save_image(file)
        except Exception:
            app.logger.exception("Picture upload to storage failed")
            flash("The picture could not be uploaded to storage. Please try again.", "error")
            return render_template("admin_add_picture.html", form=request.form), 502
        if not filename:
            flash("That file is not a supported image (png, jpg, gif, webp).", "error")
            return render_template("admin_add_picture.html", form=request.form), 400
        db.session.add(DuckPicture(title=title[:100], description=request.form.get("description", ""),
                                   filename=filename, price=price,
                                   category=(request.form.get("category") or "")[:50] or None,
                                   tags=(request.form.get("tags") or "")[:200]))
        db.session.commit()
        flash("Picture added successfully!", "success")
        return redirect(url_for("admin_pictures"))
    return render_template("admin_add_picture.html", form={})


@app.route("/admin/edit_picture/<int:picture_id>", methods=["GET", "POST"])
def admin_edit_picture(picture_id):
    picture = db.session.get(DuckPicture, picture_id) or abort(404)
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        price = _parse_price(request.form.get("price"))
        if not title or price is None:
            flash("Title and a price between $0.50 and $10,000 are required.", "error")
            return render_template("admin_edit_picture.html", picture=picture), 400
        picture.title = title[:100]
        picture.description = request.form.get("description", "")
        picture.price = price
        picture.category = (request.form.get("category") or "")[:50] or None
        picture.tags = (request.form.get("tags") or "")[:200]
        picture.is_active = "is_active" in request.form
        db.session.commit()
        flash("Picture updated successfully!", "success")
        return redirect(url_for("admin_pictures"))
    return render_template("admin_edit_picture.html", picture=picture)


@app.route("/admin/orders")
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("admin_orders.html", orders=orders)


# --------------------------------------------------------------------------------------
# Errors and setup
# --------------------------------------------------------------------------------------

@app.errorhandler(404)
def not_found_error(error):
    return render_template("404.html"), 404


@app.errorhandler(400)
def bad_request_error(error):
    return render_template("404.html", message=getattr(error, "description", "Bad request")), 400


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template("500.html"), 500


SAMPLE_PICTURES = [
    {"title": "Majestic Mallard", "description": "A beautiful male mallard duck in full breeding plumage",
     "filename": "sample_mallard.jpg", "price": 9.99, "category": "Wild Ducks", "tags": "mallard, wild, breeding, colorful"},
    {"title": "Cute Duckling", "description": "Adorable baby duck with fluffy yellow feathers",
     "filename": "sample_duckling.jpg", "price": 7.99, "category": "Baby Ducks", "tags": "duckling, baby, cute, fluffy"},
    {"title": "Wood Duck Beauty", "description": "Stunning wood duck with iridescent feathers",
     "filename": "sample_wood_duck.jpg", "price": 12.99, "category": "Wild Ducks", "tags": "wood duck, iridescent, colorful, rare"},
]


def init_db():
    """Create tables and seed sample pictures on an empty database."""
    with app.app_context():
        db.create_all()
        if DuckPicture.query.count() == 0:
            for pic in SAMPLE_PICTURES:
                db.session.add(DuckPicture(**pic))
            db.session.commit()
        # Sample images ship in ./uploads; copy them when uploads live elsewhere (e.g. /tmp on Vercel).
        src = os.path.join(BASE_DIR, "uploads")
        dst = app.config["UPLOAD_FOLDER"]
        if os.path.abspath(src) != os.path.abspath(dst) and os.path.isdir(src):
            import shutil
            for name in os.listdir(src):
                if not os.path.exists(os.path.join(dst, name)):
                    shutil.copy2(os.path.join(src, name), dst)


init_db()

if __name__ == "__main__":
    print("Duck Store running at http://localhost:%s" % os.getenv("PORT", "5000"))
    app.run(debug=os.getenv("FLASK_DEBUG") == "1", host=os.getenv("HOST", "127.0.0.1"),
            port=int(os.getenv("PORT", "5000")))
