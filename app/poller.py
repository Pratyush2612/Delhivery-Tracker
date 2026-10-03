"""Courier pollers using requests. Demo mode reads the in-memory fleet."""

from __future__ import annotations

from typing import Any

import requests

from .config import settings
from .normalise import map_raw
from .store import get_shipments

SR_TRACK = "https://apiv2.shiprocket.in/v1/external/courier/track/awb/{awb}"
SR_LOGIN = "https://apiv2.shiprocket.in/v1/external/auth/login"
DL_TRACK = "https://track.delhivery.com/api/v1/packages/json"


def _sr_token() -> str:
    if settings.shiprocket_token:
        return settings.shiprocket_token
    if not (settings.shiprocket_email and settings.shiprocket_password):
        return ""
    res = requests.post(
        SR_LOGIN,
        json={"email": settings.shiprocket_email, "password": settings.shiprocket_password},
        timeout=20,
    )
    res.raise_for_status()
    return str(res.json().get("token") or "")


def poll_shiprocket(awb: str) -> dict[str, Any]:
    if settings.demo_mode or not (settings.shiprocket_token or settings.shiprocket_email):
        return _demo_payload(awb, "shiprocket")
    token = _sr_token()
    res = requests.get(
        SR_TRACK.format(awb=awb),
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    if res.status_code != 200:
        return {"ok": False, "carrier": "shiprocket", "awb": awb, "error": res.text[:300]}
    body = res.json()
    tracking = (body.get("tracking_data") or body).get("shipment_track") or []
    raw = tracking[0].get("current_status") if tracking else body.get("shipment_status")
    return {
        "ok": True,
        "carrier": "shiprocket",
        "awb": awb,
        "shipment_status": raw,
        "payload": body,
    }


def poll_delhivery(awb: str) -> dict[str, Any]:
    if settings.demo_mode or not settings.delhivery_token:
        return _demo_payload(awb, "delhivery")
    res = requests.get(
        DL_TRACK,
        params={"waybill": awb, "token": settings.delhivery_token},
        timeout=20,
    )
    if res.status_code != 200:
        return {"ok": False, "carrier": "delhivery", "awb": awb, "error": res.text[:300]}
    body = res.json()
    shipment = (body.get("ShipmentData") or [{}])[0].get("Shipment") or {}
    status = (shipment.get("Status") or {}).get("Status")
    return {
        "ok": True,
        "carrier": "delhivery",
        "awb": awb,
        "Status": shipment.get("Status") or {"Status": status},
        "payload": body,
    }


def _demo_payload(awb: str, carrier: str) -> dict[str, Any]:
    df = get_shipments()
    hit = df[df["awb"] == awb]
    if hit.empty:
        return {"ok": False, "carrier": carrier, "awb": awb, "error": "not_found"}
    row = hit.iloc[0]
    if carrier == "shiprocket":
        return {
            "ok": True,
            "carrier": "shiprocket",
            "awb": awb,
            "shipment_status": row["raw_status"],
            "etd": row["sla_hours"],
            "destination": row["city"],
        }
    return {
        "ok": True,
        "carrier": "delhivery",
        "awb": awb,
        "Status": {"Status": row["raw_status"], "StatusDateTime": row["shipped_at"]},
        "Destination": row["city"],
    }


def poll_one(awb: str, carrier: str) -> dict[str, Any]:
    raw = poll_shiprocket(awb) if carrier == "shiprocket" else poll_delhivery(awb)
    if not raw.get("ok"):
        return raw
    raw_status = (
        raw.get("shipment_status")
        if carrier == "shiprocket"
        else (raw.get("Status") or {}).get("Status")
    )
    return {
        "ok": True,
        "awb": awb,
        "carrier": carrier,
        "raw_status": raw_status,
        "status": map_raw(carrier, str(raw_status)),
        "payload": raw,
    }
