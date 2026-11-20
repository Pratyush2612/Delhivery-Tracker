from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    login_email: str = "ops@swiftlogic.ai"
    login_password: str = "change-me"
    session_secret: str = "swiftlogic-change-me"

    shiprocket_email: str = ""
    shiprocket_password: str = ""
    shiprocket_token: str = ""
    delhivery_token: str = ""

    slack_webhook_url: str = ""
    whatsapp_webhook_url: str = ""
    whatsapp_token: str = ""

    poll_interval_minutes: int = 15
    database_url: str = "sqlite:///data/tracker.db"
    cors_origins: str = "*"


settings = Settings()

SLA_HOURS = {"metro": 48, "tier1": 72, "tier2": 96, "remote": 144}

CITY_ZONE = {
    "pune": "metro",
    "mumbai": "metro",
    "bengaluru": "metro",
    "bangalore": "metro",
    "delhi": "metro",
    "new delhi": "metro",
    "hyderabad": "metro",
    "chennai": "metro",
    "ahmedabad": "tier1",
    "jaipur": "tier1",
    "surat": "tier1",
    "lucknow": "tier1",
    "indore": "tier2",
    "nagpur": "tier2",
    "coimbatore": "tier2",
    "bhubaneswar": "tier2",
    "guwahati": "remote",
    "ranchi": "remote",
}

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
    "unknown",
]
