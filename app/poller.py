"""Live Shiprocket and Delhivery pollers. No mock data."""

from __future__ import annotations

from typing import Any

import requests

from .config import settings
from .normalise import map_raw

SR_LOGIN = "https://apiv2.shiprocket.in/v1/external/auth/login"
SR_TRACK = "https://apiv2.shiprocket.in/v1/external/courier/track/awb/{awb}"
DL_TRACK = "https://track.delhivery.com/api/v1/packages/json/"


class CourierError(Exception):
    pass


def _sr_token() -> str:
    if settings.shiprocket_token:
        return settings.shiprocket_token
    if not (settings.shiprocket_email and settings.shiprocket_password):
        raise CourierError("Shiprocket credentials missing. Set SHIPROCKET_TOKEN or email/password.")
    res = requests.post(
        SR_LOGIN,
        json={"email": settings.shiprocket_email, "password": settings.shiprocket_password},
        timeout=25,
    )
    if res.status_code >= 300:
        raise CourierError(f"Shiprocket login failed: {res.status_code} {res.text[:180]}")
    token = str(res.json().get("token") or "")
    if not token:
        raise CourierError("Shiprocket login returned no token")
    return token


def poll_shiprocket(awb: str) -> dict[str, Any]:
    token = _sr_token()
    res = requests.get(
        SR_TRACK.format(awb=awb),
        headers={"Authorization": f"Bearer {token}"},
        timeout=25,
    )
    if res.status_code >= 300:
        raise CourierError(f"Shiprocket track failed: {res.status_code} {res.text[:180]}")
    body = res.json()
    tracking = (body.get("tracking_data") or {}).get("shipment_track") or []
    raw = ""
    city = ""
    shipped_at = ""
    if tracking:
        raw = str(tracking[0].get("current_status") or "")
        city = str(tracking[0].get("destination") or "")
        shipped_at = str(tracking[0].get("pickup_date") or "")
    return {
        "ok": True,
        "carrier": "shiprocket",
        "awb": awb,
        "raw_status": raw,
        "status": map_raw("shiprocket", raw),
        "city": city,
        "shipped_at": shipped_at,
        "payload": body,
    }


def poll_delhivery(awb: str) -> dict[str, Any]:
    if not settings.delhivery_token:
        raise CourierError("Delhivery token missing. Set DELHIVERY_TOKEN.")
    res = requests.get(
        DL_TRACK,
        params={"waybill": awb, "verbose": 2},
        headers={"Authorization": f"Token {settings.delhivery_token}"},
        timeout=25,
    )
    if res.status_code >= 300:
        raise CourierError(f"Delhivery track failed: {res.status_code} {res.text[:180]}")
    body = res.json()
    shipment = ((body.get("ShipmentData") or [{}])[0].get("Shipment") or {})
    status = shipment.get("Status") or {}
    raw = str(status.get("Status") or "")
    return {
        "ok": True,
        "carrier": "delhivery",
        "awb": awb,
        "raw_status": raw,
        "status": map_raw("delhivery", raw),
        "city": str(shipment.get("Destination") or ""),
        "shipped_at": str(shipment.get("PickUpDate") or status.get("StatusDateTime") or ""),
        "payload": body,
    }


def poll_one(awb: str, carrier: str) -> dict[str, Any]:
    if carrier == "shiprocket":
        return poll_shiprocket(awb)
    if carrier == "delhivery":
        return poll_delhivery(awb)
    raise CourierError(f"Unknown carrier: {carrier}")
