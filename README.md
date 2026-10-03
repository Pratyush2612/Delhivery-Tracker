# SwiftLogic Courier Tracker

Full-stack Python demo. FastAPI dashboard, pandas status normalisation,
requests pollers for Shiprocket / Delhivery, Slack and WhatsApp delay / RTO alerts.

Demo mode is on by default. No courier keys required.

## Windows CMD

```bat
cd path\to\swiftlogic_courier
py -m venv .venv
.venv\Scripts\activate.bat
py -m pip install -r requirements.txt
py run.py
```

Do not copy `.env` unless you want live API keys. The app reads defaults if `.env` is missing.

The server prints a URL such as http://127.0.0.1:8765. It binds only to localhost and skips ports Windows has reserved (the usual cause of WinError 10013 on 8080).

Stop with Ctrl+C.

## macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

## Live keys (optional)

Copy `.env.example` to `.env` only if the file does not already exist:

```bat
if not exist .env copy .env.example .env
```

Set `DEMO_MODE=false` plus Shiprocket / Delhivery / Slack / WhatsApp values.
