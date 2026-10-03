from __future__ import annotations

import pandas as pd

from .config import DELHIVERY_MAP, SHIPROCKET_MAP


def map_raw(carrier: str, raw_status: str) -> str:
    table = SHIPROCKET_MAP if carrier == "shiprocket" else DELHIVERY_MAP
    raw = str(raw_status).strip()
    return table.get(raw, table.get(raw.upper(), "in_transit"))


def normalise_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    status_col = out["status"] if "status" in out.columns else pd.Series([""] * len(out))
    out["status"] = [
        map_raw(c, r) if not s else s
        for c, r, s in zip(out["carrier"], out["raw_status"], status_col)
    ]
    closed = out["status"].isin(["delivered", "cancelled", "rto_delivered"])
    out["is_delayed"] = (out["delay_hours"] > 6) & ~closed
    out["is_rto_risk"] = out["status"].isin(
        ["ndr", "rto_initiated", "rto_in_transit", "rto_delivered"]
    )
    return out
