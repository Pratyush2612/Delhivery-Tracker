from __future__ import annotations

import pandas as pd
import requests

from .config import settings
from .store import add_alert


def post_slack(text: str) -> bool:
    if not settings.slack_webhook_url:
        return False
    try:
        res = requests.post(settings.slack_webhook_url, json={"text": text}, timeout=15)
        return res.status_code < 300
    except requests.RequestException:
        return False


def post_whatsapp(text: str) -> bool:
    if not settings.whatsapp_webhook_url:
        return False
    headers = {}
    if settings.whatsapp_token:
        headers["Authorization"] = f"Bearer {settings.whatsapp_token}"
    try:
        res = requests.post(
            settings.whatsapp_webhook_url,
            json={"text": text},
            headers=headers,
            timeout=15,
        )
        return res.status_code < 300
    except requests.RequestException:
        return False


def dispatch(channel: str, text: str) -> bool:
    if channel == "whatsapp":
        return post_whatsapp(text)
    return post_slack(text)


def fire_delay_and_rto(
    df: pd.DataFrame,
    delay_channel: str = "slack",
    rto_channel: str = "whatsapp",
    limit: int = 8,
) -> list[dict]:
    posted: list[dict] = []
    delayed = df[df["is_delayed"]].head(limit)
    rto = df[df["is_rto_risk"]].head(limit)
    for _, row in delayed.iterrows():
        msg = (
            f"Delay {row['delay_hours']:.0f}h | {row['awb']} {row['city']} "
            f"{row['carrier']} {row['status']}"
        )
        ok = dispatch(delay_channel, msg)
        posted.append(add_alert("delay", delay_channel, row["awb"], msg, delivered=ok))
    for _, row in rto.iterrows():
        msg = (
            f"RTO/NDR | {row['awb']} {row['city']} COD={row['cod']} "
            f"₹{row['value_inr']} {row['status']}"
        )
        ok = dispatch(rto_channel, msg)
        posted.append(add_alert("rto", rto_channel, row["awb"], msg, delivered=ok))
    return posted
