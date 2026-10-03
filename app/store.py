from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd

from .config import CITIES, DELHIVERY_MAP, SHIPROCKET_MAP, SKUS, SLA_HOURS

IST = timezone(timedelta(hours=5, minutes=30))

ALERTS: list[dict[str, Any]] = []
SHIPMENTS: pd.DataFrame | None = None


def now_ist() -> datetime:
    return datetime.now(tz=IST)


def invert_raw(carrier: str, status: str, rng: np.random.Generator) -> str:
    mapping = SHIPROCKET_MAP if carrier == "shiprocket" else DELHIVERY_MAP
    candidates = [k for k, v in mapping.items() if v == status]
    return str(rng.choice(candidates)) if candidates else status.upper()


def generate_shipments(n: int = 180, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    today = now_ist()
    cities = list(CITIES.keys())
    rows = []
    for i in range(n):
        city = str(rng.choice(cities))
        zone = CITIES[city]
        carrier = str(rng.choice(["shiprocket", "delhivery"]))
        age_h = float(rng.integers(4, 220))
        shipped_at = today - timedelta(hours=age_h)
        sla = SLA_HOURS[zone]
        if age_h < 18:
            status = rng.choice(["created", "picked", "in_transit"], p=[0.25, 0.35, 0.40])
        elif age_h < sla * 0.8:
            status = rng.choice(
                ["in_transit", "out_for_delivery", "delivered"], p=[0.45, 0.25, 0.30]
            )
        elif age_h < sla * 1.4:
            status = rng.choice(
                ["in_transit", "out_for_delivery", "delivered", "ndr"],
                p=[0.20, 0.15, 0.45, 0.20],
            )
        else:
            status = rng.choice(
                ["ndr", "rto_initiated", "rto_in_transit", "rto_delivered", "delivered", "lost"],
                p=[0.22, 0.20, 0.18, 0.15, 0.20, 0.05],
            )
        raw = invert_raw(carrier, str(status), rng)
        open_status = status not in ("delivered", "cancelled", "rto_delivered")
        delay_h = max(0.0, age_h - sla) if open_status else 0.0
        rows.append(
            {
                "awb": f"{'SR' if carrier == 'shiprocket' else 'DL'}{100000 + i}",
                "order_id": f"PN-{24000 + i}",
                "sku": str(rng.choice(SKUS)),
                "city": city,
                "zone": zone,
                "carrier": carrier,
                "raw_status": raw,
                "status": str(status),
                "shipped_at": shipped_at.isoformat(timespec="seconds"),
                "age_hours": round(age_h, 1),
                "sla_hours": sla,
                "delay_hours": round(delay_h, 1),
                "is_delayed": delay_h > 6 and open_status,
                "is_rto_risk": str(status).startswith("rto") or status == "ndr",
                "cod": bool(rng.random() < 0.62),
                "value_inr": int(rng.choice([349, 499, 699, 899, 1299, 1899])),
            }
        )
    return pd.DataFrame(rows)


def get_shipments() -> pd.DataFrame:
    global SHIPMENTS
    if SHIPMENTS is None:
        SHIPMENTS = generate_shipments()
    return SHIPMENTS


def reset_shipments(n: int = 180, seed: int = 7) -> pd.DataFrame:
    global SHIPMENTS
    SHIPMENTS = generate_shipments(n, seed)
    return SHIPMENTS


def add_alert(kind: str, channel: str, awb: str, message: str, delivered: bool = True) -> dict[str, Any]:
    item = {
        "id": len(ALERTS) + 1,
        "kind": kind,
        "channel": channel,
        "awb": awb,
        "message": message,
        "delivered": delivered,
        "sent_at": now_ist().isoformat(timespec="seconds"),
    }
    ALERTS.insert(0, item)
    return item
