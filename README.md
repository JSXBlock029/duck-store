# Duck Store

A small Flask storefront that sells duck pictures with Stripe card payments: a gallery with search and categories, a session cart, Stripe checkout, instant downloads after payment, and a password-protected admin area for pictures and orders.

![CI](https://github.com/lowriskbtc/duck-store/actions/workflows/ci.yml/badge.svg)

## Features

- **Gallery** with search, category filters and pagination
- **Cart** stored in the session, with quantity limits
- **Stripe card checkout** (Stripe.js card element); the order is built from the PaymentIntent, not from the browser
- **Downloads** of purchased pictures from the buyer's session
- **Admin area** (`/admin`): dashboard, add and edit pictures, order list

## Run it locally

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # fill in the values
python duck_store.py                                  # http://127.0.0.1:5000
```

Without Stripe keys the shop runs normally and the checkout page says payments are not enabled yet.

## Configuration

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Signs sessions. Required in production. |
| `ADMIN_PASSWORD` | Enables `/admin` (HTTP Basic auth, any username). Unset means admin is disabled. |
| `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY` | Enable card payments. Use `sk_test_` / `pk_test_` keys first. |
| `DATABASE_URL` | Defaults to SQLite. Use Postgres in production so orders persist. |
| `UPLOAD_FOLDER` | Where pictures are stored. Defaults to `./uploads` (or `/tmp/uploads` on Vercel). |
| `BLOB_READ_WRITE_TOKEN` | Set automatically when a Vercel Blob store is connected. Admin uploads then go to Blob and survive restarts. |

## Security

- Prices and totals are computed on the server; the browser never sends an amount.
- An order is created only from a PaymentIntent this server created, after Stripe reports it succeeded, with the charged amount matching the items, and only once per PaymentIntent.
- Orders and downloads are visible only to the session that bought them (and to the admin).
- Every POST carries a CSRF token. Uploads must be real images (png, jpg, gif, webp) and are stored under random names.
- Debug mode is off unless `FLASK_DEBUG=1`, and the dev server binds to localhost.

## Deploying on Vercel

`vercel.json` routes everything to `api/index.py`, which serves the same app. Set the environment variables above in the Vercel project. Vercel's filesystem is temporary, so connect a Postgres database (`DATABASE_URL`) for orders and a Blob store (`BLOB_READ_WRITE_TOKEN`) for uploaded pictures.

## Tests

```bash
pip install -r requirements.txt pytest
pytest
```

Tests cover the storefront, cart limits, CSRF, the admin guard and upload validation, and the payment flow end to end with a fake Stripe (server-side amounts, replays, swapped carts, underpayments, foreign PaymentIntents). The network is blocked during tests.
