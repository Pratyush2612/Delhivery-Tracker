from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    shiprocket_email: str = ""
    shiprocket_password: str = ""
    shiprocket_token: str = ""
    delhivery_token: str = ""
    slack_webhook_url: str = ""
    whatsapp_webhook_url: str = ""
    whatsapp_token: str = ""
    poll_interval_seconds: int = 300
    demo_mode: bool = True
    cors_origins: str = "*"


settings = Settings()

SLA_HOURS = {"metro": 48, "tier1": 72, "tier2": 96, "remote": 144}

CITIES = {
    "Pune": "metro",
    "Mumbai": "metro",
    "Bengaluru": "metro",
    "Delhi": "metro",
    "Hyderabad": "metro",
    "Chennai": "metro",
    "Ahmedabad": "tier1",
    "Jaipur": "tier1",
    "Surat": "tier1",
    "Lucknow": "tier1",
    "Indore": "tier2",
    "Nagpur": "tier2",
    "Coimbatore": "tier2",
    "Bhubaneswar": "tier2",
    "Guwahati": "remote",
    "Ranchi": "remote",
}

SKUS = [
    "PN-HAIR-OIL-100",
    "PN-FACE-WASH-50",
    "PN-SOAP-NEEM",
    "PN-SCRUB-COFFEE",
    "PN-SERUM-VITC",
    "PN-COMBO-GLOW",
]

SHIPROCKET_MAP = {
    "NEW": "created",
    "AWB ASSIGNED": "created",
    "PICKED UP": "picked",
    "SHIPPED": "in_transit",
    "IN TRANSIT": "in_transit",
    "REACHED DESTINATION HUB": "in_transit",
    "OUT FOR DELIVERY": "out_for_delivery",
    "DELIVERED": "delivered",
    "UNDELIVERED": "ndr",
    "PENDING": "ndr",
    "RTO INITIATED": "rto_initiated",
    "RTO IN TRANSIT": "rto_in_transit",
    "RTO DELIVERED": "rto_delivered",
    "LOST": "lost",
    "CANCELLED": "cancelled",
}

DELHIVERY_MAP = {
    "Manifested": "created",
    "Not Picked": "created",
    "In Transit": "in_transit",
    "Pending": "in_transit",
    "Dispatched": "out_for_delivery",
    "Delivered": "delivered",
    "DTO": "ndr",
    "NDR": "ndr",
    "RTO": "rto_initiated",
    "RTO In Transit": "rto_in_transit",
    "RTO Delivered": "rto_delivered",
    "Lost": "lost",
    "Cancelled": "cancelled",
}

CANONICAL = [
    "created",
    "picked",
    "in_transit",
    "out_for_delivery",
    "delivered",
    "ndr",
    "rto_initiated",
    "rto_in_transit",
    "rto_delivered",
    "lost",
    "cancelled",
]
