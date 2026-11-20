from __future__ import annotations

from datetime import datetime

from .config import CITY_ZONE, DELHIVERY_MAP, SHIPROCKET_MAP, SLA_HOURS
from .db import now_ist


def map_raw(carrier: str, raw_status: str) -> str:
    table = SHIPROCKET_MAP if carrier == "shiprocket" else DELHIVERY_MAP
    raw = str(raw_status or "").strip()
    if not raw:
        return "unknown"
    if raw in table:
        return table[raw]
    upper = raw.upper()
    for key, value in table.items():
        if key.upper() == upper:
            return value
    # Fuzzy pass for labels like "RTO INITIATED - IN TRANSIT"
    upper_space = raw.upper()
    if "RTO DELIVERED" in upper_space:
        return "rto_delivered"
    if "RTO IN TRANSIT" in upper_space:
        return "rto_in_transit"
    if "RTO" in upper_space:
        return "rto_initiated"
    if "UNDELIVERED" in upper_space or "NDR" in upper_space:
        return "ndr"
    if "OUT FOR DELIVERY" in upper_space or "DISPATCHED" in upper_space:
        return "out_for_delivery"
    if "DELIVERED" in upper_space:
        return "delivered"
    if "PICKED" in upper_space:
        return "picked"
    if "TRANSIT" in upper_space or "SHIPPED" in upper_space:
        return "in_transit"
    if "CANCEL" in upper_space:
        return "cancelled"
    if "LOST" in upper_space:
        return "lost"
    return "in_transit"


def zone_for(city: str, fallback: str = "tier1") -> str:
    return CITY_ZONE.get((city or "").strip().lower(), fallback or "tier1")


def compute_age_delay(shipped_at: str | None, sla_hours: int, status: str) -> tuple[float, float]:
    age = 0.0
    if shipped_at:
        try:
            parsed = datetime.fromisoformat(shipped_at)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=now_ist().tzinfo)
            age = max(0.0, (now_ist() - parsed).total_seconds() / 3600)
        except ValueError:
            age = 0.0
    closed = status in {"delivered", "cancelled", "rto_delivered"}
    delay = max(0.0, age - sla_hours) if (age and not closed) else 0.0
    return round(age, 1), round(delay, 1)


def flags(status: str, delay_hours: float) -> tuple[bool, bool]:
    closed = status in {"delivered", "cancelled", "rto_delivered"}
    delayed = delay_hours > 6 and not closed
    rto = status in {"ndr", "rto_initiated", "rto_in_transit", "rto_delivered"}
    return delayed, rto


def sla_for(zone: str) -> int:
    return SLA_HOURS.get(zone, 72)
