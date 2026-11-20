from __future__ import annotations

from .alerts import alert
from .db import iso, list_shipments, now_ist, update_shipment
from .normalise import compute_age_delay, flags, map_raw, sla_for, zone_for
from .poller import CourierError, poll_one


def refresh_one(awb: str, carrier: str) -> dict:
    try:
        result = poll_one(awb, carrier)
    except CourierError as exc:
        update_shipment(awb, carrier, {"last_error": str(exc), "last_polled_at": iso()})
        return {"ok": False, "awb": awb, "carrier": carrier, "error": str(exc)}

    city = result.get("city") or ""
    status = result.get("status") or map_raw(carrier, result.get("raw_status") or "")
    zone = zone_for(city)
    sla = sla_for(zone)
    age, delay = compute_age_delay(result.get("shipped_at"), sla, status)
    delayed, rto = flags(status, delay)
    fields = {
        "raw_status": result.get("raw_status") or "",
        "status": status,
        "age_hours": age,
        "sla_hours": sla,
        "delay_hours": delay,
        "is_delayed": int(delayed),
        "is_rto_risk": int(rto),
        "last_error": "",
        "last_polled_at": iso(),
    }
    if city:
        fields["city"] = city
        fields["zone"] = zone
    update_shipment(awb, carrier, fields)
    return {"ok": True, "awb": awb, "carrier": carrier, "status": status, "delay_hours": delay}


def refresh_all() -> dict:
    rows = list_shipments()
    ok = 0
    failed = 0
    for row in rows:
        result = refresh_one(row["awb"], row["carrier"])
        if result.get("ok"):
            ok += 1
        else:
            failed += 1
    return {"ok": True, "polled": len(rows), "succeeded": ok, "failed": failed, "at": iso()}


def fanout_alerts() -> dict:
    posted = []
    for row in list_shipments():
        if row["is_delayed"]:
            msg = (
                f"Delay {row['delay_hours']:.0f}h | {row['awb']} {row['city']} "
                f"{row['carrier']} {row['status']}"
            )
            posted.append(alert("delay", "slack", row["awb"], msg))
        if row["is_rto_risk"]:
            msg = (
                f"RTO/NDR | {row['awb']} {row['city']} COD={bool(row['cod'])} "
                f"₹{row['value_inr']} {row['status']}"
            )
            posted.append(alert("rto", "whatsapp", row["awb"], msg))
    return {"ok": True, "posted": len(posted), "at": now_ist().isoformat(timespec="seconds")}
