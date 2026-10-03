from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .alerts import fire_delay_and_rto
from .config import CANONICAL, STATIC, TEMPLATES, settings
from .normalise import normalise_frame
from .poller import poll_one
from .store import ALERTS, add_alert, get_shipments, reset_shipments

DEMO_EMAIL = os.getenv("LOGIN_EMAIL", "ops@swiftlogic.ai")
DEMO_PASSWORD = os.getenv("LOGIN_PASSWORD", "demo1234")
COOKIE = "sl_session"
SECRET = os.getenv("SESSION_SECRET", "swiftlogic-demo-secret")

app = FastAPI(
    title="SwiftLogic Courier Tracker",
    description="Shiprocket / Delhivery poller, pandas status normaliser, Slack & WhatsApp alerts.",
    version="1.2.0",
)
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES))


def _token(email: str) -> str:
    digest = hmac.new(SECRET.encode(), email.encode(), hashlib.sha256).hexdigest()
    return f"{email}:{digest}"


def logged_in(request: Request) -> bool:
    raw = request.cookies.get(COOKIE, "")
    email, _, digest = raw.partition(":")
    if not email or not digest:
        return False
    expected = _token(email).split(":", 1)[1]
    return hmac.compare_digest(digest, expected)


def require_login(request: Request) -> None:
    if not logged_in(request):
        raise HTTPException(status_code=401, detail="login required")


class AlertIn(BaseModel):
    awb: str = ""
    text: str = "alert"


class TrackIn(BaseModel):
    awb: str
    carrier: str = Field(pattern="^(shiprocket|delhivery)$")


class PollIn(BaseModel):
    n: int = 180
    seed: int = 7


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = "") -> HTMLResponse:
    if logged_in(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(
        request=request, name="login.html", context={"error": error}
    )


@app.post("/login")
def login_submit(email: str = Form(...), password: str = Form(...)) -> RedirectResponse:
    ok = hmac.compare_digest(email.strip().lower(), DEMO_EMAIL.lower()) and hmac.compare_digest(
        password, DEMO_PASSWORD
    )
    if not ok:
        return RedirectResponse("/login?error=Invalid+email+or+password", status_code=303)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(COOKIE, _token(email.strip().lower()), httponly=True, samesite="lax")
    return response


@app.get("/logout")
def logout() -> RedirectResponse:
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie(COOKIE)
    return response


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    if not logged_in(request):
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(request=request, name="index.html", context={})


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "courier-tracker", "demo_mode": settings.demo_mode}


@app.get("/api/shipments")
def api_shipments(request: Request) -> dict[str, Any]:
    require_login(request)
    df = normalise_frame(get_shipments())
    records = df.to_dict(orient="records")
    summary = {
        "total": int(len(df)),
        "in_flight": int(df["status"].isin(["picked", "in_transit", "out_for_delivery"]).sum()),
        "delayed": int(df["is_delayed"].sum()),
        "rto": int(df["is_rto_risk"].sum()),
        "at_risk_value": int(df.loc[df["is_rto_risk"], "value_inr"].sum()),
        "by_status": {s: int((df["status"] == s).sum()) for s in CANONICAL},
        "by_city": (
            df.groupby("city")
            .agg(n=("awb", "count"), delayed=("is_delayed", "sum"), rto=("is_rto_risk", "sum"))
            .reset_index()
            .sort_values("delayed", ascending=False)
            .to_dict(orient="records")
        ),
    }
    return {"summary": summary, "shipments": records}


@app.post("/api/poll")
def api_poll(body: PollIn, request: Request) -> dict[str, Any]:
    require_login(request)
    reset_shipments(body.n, body.seed)
    return {"ok": True, "n": body.n, "seed": body.seed}


@app.post("/api/track")
def api_track(body: TrackIn, request: Request) -> dict[str, Any]:
    require_login(request)
    return poll_one(body.awb, body.carrier)


@app.post("/api/alerts/slack")
def api_slack(body: AlertIn, request: Request) -> dict[str, Any]:
    require_login(request)
    return add_alert("ops", "slack", body.awb, body.text)


@app.post("/api/alerts/whatsapp")
def api_whatsapp(body: AlertIn, request: Request) -> dict[str, Any]:
    require_login(request)
    return add_alert("customer", "whatsapp", body.awb, body.text)


@app.post("/api/alerts/fanout")
def api_fanout(
    request: Request,
    delay_channel: str = Query("slack"),
    rto_channel: str = Query("whatsapp"),
) -> dict[str, Any]:
    require_login(request)
    df = normalise_frame(get_shipments())
    posted = fire_delay_and_rto(df, delay_channel, rto_channel)
    return {"ok": True, "posted": len(posted), "alerts": posted}


@app.get("/api/alerts")
def api_alerts(request: Request) -> list[dict[str, Any]]:
    require_login(request)
    return ALERTS[:80]
