from __future__ import annotations

import hashlib
import hmac
from typing import Any

import pandas as pd
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .config import CANONICAL, STATIC, TEMPLATES, settings
from .db import add_shipment, delete_shipment, init_db, list_alerts, list_shipments
from .jobs import fanout_alerts, refresh_all, refresh_one
from .normalise import zone_for
from .scheduler import start_scheduler

COOKIE = "sl_session"

app = FastAPI(
    title="SwiftLogic Courier Tracker",
    description="Live Shiprocket / Delhivery tracker. SQLite watchlist, scheduled polling, Slack and WhatsApp alerts.",
    version="2.0.0",
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
    digest = hmac.new(settings.session_secret.encode(), email.encode(), hashlib.sha256).hexdigest()
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


class ShipmentIn(BaseModel):
    awb: str
    carrier: str = Field(pattern="^(shiprocket|delhivery)$")
    order_id: str = ""
    city: str = ""
    sku: str = ""
    cod: bool = False
    value_inr: int = 0
    age_hours: float = 0
    delay_hours: float = 0
    raw_status: str = ""
    status: str = ""


class DeleteIn(BaseModel):
    awb: str
    carrier: str = Field(pattern="^(shiprocket|delhivery)$")


@app.on_event("startup")
def startup() -> None:
    init_db()
    start_scheduler()


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = "") -> HTMLResponse:
    if logged_in(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request=request, name="login.html", context={"error": error})


@app.post("/login")
def login_submit(email: str = Form(...), password: str = Form(...)) -> RedirectResponse:
    ok = hmac.compare_digest(email.strip().lower(), settings.login_email.lower()) and hmac.compare_digest(
        password, settings.login_password
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
    return templates.TemplateResponse(request=request, name="courier-index.html", context={})


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "courier-tracker",
        "mode": "live",
        "shiprocket_configured": bool(settings.shiprocket_token or settings.shiprocket_email),
        "delhivery_configured": bool(settings.delhivery_token),
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "total": 0,
            "in_flight": 0,
            "delayed": 0,
            "rto": 0,
            "at_risk_value": 0,
            "by_status": {s: 0 for s in CANONICAL},
            "by_city": [],
        }
    df = pd.DataFrame(rows)
    return {
        "total": int(len(df)),
        "in_flight": int(df["status"].isin(["picked", "in_transit", "out_for_delivery"]).sum()),
        "delayed": int(df["is_delayed"].sum()),
        "rto": int(df["is_rto_risk"].sum()),
        "at_risk_value": int(df.loc[df["is_rto_risk"] == 1, "value_inr"].sum()),
        "by_status": {s: int((df["status"] == s).sum()) for s in CANONICAL},
        "by_city": (
            df.groupby("city")
            .agg(n=("awb", "count"), delayed=("is_delayed", "sum"), rto=("is_rto_risk", "sum"))
            .reset_index()
            .sort_values("delayed", ascending=False)
            .to_dict(orient="records")
        ),
    }


@app.get("/api/shipments")
def api_shipments(request: Request) -> dict[str, Any]:
    require_login(request)
    rows = list_shipments()
    return {"summary": _summary(rows), "shipments": rows}


@app.post("/api/shipments")
def api_add(body: ShipmentIn, request: Request) -> dict[str, Any]:
    require_login(request)
    zone = zone_for(body.city)
    row = add_shipment(
        body.awb,
        body.carrier,
        body.order_id,
        body.city,
        body.sku,
        body.cod,
        body.value_inr,
        zone,
        body.raw_status,
        body.status,
        body.age_hours,
        body.delay_hours,
    )
    result = refresh_one(body.awb, body.carrier)
    return {"ok": True, "shipment": row, "poll": result}


@app.post("/api/shipments/delete")
def api_delete(body: DeleteIn, request: Request) -> dict[str, Any]:
    require_login(request)
    delete_shipment(body.awb, body.carrier)
    return {"ok": True}


@app.post("/api/refresh")
def api_refresh(request: Request) -> dict[str, Any]:
    require_login(request)
    return refresh_all()


@app.post("/api/alerts/fanout")
def api_fanout(request: Request) -> dict[str, Any]:
    require_login(request)
    return fanout_alerts()


@app.get("/api/alerts")
def api_alerts(request: Request) -> list[dict[str, Any]]:
    require_login(request)
    return list_alerts()
