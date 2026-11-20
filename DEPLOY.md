# Deploy

Set environment variables from `.env.example`.

Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Local:

```bash
python run.py
```

The scheduler starts with the app and polls the watchlist on `POLL_INTERVAL_MINUTES`.
