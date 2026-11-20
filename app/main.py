from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .config import CANONICAL, STATIC, TEMPLATES, settings
from .db import add_shipment, delete_shipment, init_db, list_alerts, list_shipments
from .jobs import fanout_alerts, refresh_all, refresh_one
from .normalise import zone_for
from .scheduler import start_scheduler

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
    try:
        init_db()
        start_scheduler()
    except Exception as exc:
        print(f"Startup warning: {exc}")


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    try:
        return templates.TemplateResponse(request=request, name="courier-index.html", context={})
    except TypeError:
        return templates.TemplateResponse("courier-index.html", {"request": request})


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
def api_shipments() -> dict[str, Any]:
    rows = list_shipments()
    return {"summary": _summary(rows), "shipments": rows}


@app.post("/api/shipments")
def api_add(body: ShipmentIn) -> dict[str, Any]:
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
def api_delete(body: DeleteIn) -> dict[str, Any]:
    delete_shipment(body.awb, body.carrier)
    return {"ok": True}


@app.post("/api/refresh")
def api_refresh() -> dict[str, Any]:
    return refresh_all()


@app.post("/api/alerts/fanout")
def api_fanout() -> dict[str, Any]:
    return fanout_alerts()


@app.get("/api/alerts")
def api_alerts() -> list[dict[str, Any]]:
    return list_alerts()
