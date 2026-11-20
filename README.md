# SwiftLogic Courier Tracker

Production Shiprocket / Delhivery tracker. No mock shipment book.

- FastAPI dashboard with login
- SQLite watchlist of real AWBs
- Live `requests` polling of Shiprocket and Delhivery
- pandas status summary
- APScheduler refresh + Slack / WhatsApp delay and RTO alerts

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill `.env`:

- `LOGIN_EMAIL` / `LOGIN_PASSWORD` for the ops login
- `SHIPROCKET_TOKEN` or `SHIPROCKET_EMAIL` + `SHIPROCKET_PASSWORD`
- `DELHIVERY_TOKEN`
- `SLACK_WEBHOOK_URL` and `WHATSAPP_WEBHOOK_URL` for alerts

Then:

```bash
python run.py
```

Open the URL printed in the console. Add AWBs from the dashboard. The scheduler polls every `POLL_INTERVAL_MINUTES`.

## Windows CMD

```bat
py -m venv .venv
.venv\Scripts\activate.bat
py -m pip install -r requirements.txt
copy .env.example .env
py run.py
```

## Deploy

Render / Railway / Fly:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set the same environment variables. SQLite is fine for a single instance. For multi-instance hosting, point `DATABASE_URL` at Postgres and swap the store.
