from __future__ import annotations

import requests

from .config import settings
from .db import add_alert


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


def alert(kind: str, channel: str, awb: str, message: str) -> dict:
    delivered = dispatch(channel, message)
    return add_alert(kind, channel, awb, message, delivered)
