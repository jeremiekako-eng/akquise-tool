"""Zentrale Konfiguration — lädt .env und stellt alle Parameter bereit."""
import os
from pathlib import Path
from dotenv import load_dotenv

# .env laden (aus dem Projektordner)
load_dotenv(Path(__file__).parent / ".env")


class Config:
    # ── API Keys ──────────────────────────────────────────
    _tm_raw: str = os.getenv("TICKETMASTER_API_KEY", "")
    TICKETMASTER_API_KEY: str = _tm_raw if _tm_raw and "your_" not in _tm_raw else ""

    _sg_id_raw: str = os.getenv("SEATGEEK_CLIENT_ID", "")
    SEATGEEK_CLIENT_ID: str = _sg_id_raw if _sg_id_raw and "your_" not in _sg_id_raw else ""

    _sg_sec_raw: str = os.getenv("SEATGEEK_CLIENT_SECRET", "")
    SEATGEEK_CLIENT_SECRET: str = _sg_sec_raw if _sg_sec_raw and "your_" not in _sg_sec_raw else ""

    # ── Scan-Targets ──────────────────────────────────────
    TARGET_COUNTRIES: list[str] = [
        c.strip() for c in os.getenv("TARGET_COUNTRIES", "DE,AT,CH").split(",")
    ]
    TARGET_CITIES: list[str] = [
        c.strip()
        for c in os.getenv(
            "TARGET_CITIES", "Berlin,Hamburg,München,Frankfurt,Köln,Wien,Zürich"
        ).split(",")
    ]
    TARGET_CATEGORIES: list[str] = [
        c.strip()
        for c in os.getenv("TARGET_CATEGORIES", "Music,Sports").split(",")
    ]

    # ── Profit-Kalkulation ────────────────────────────────
    MIN_ROI_BUY: float = float(os.getenv("MIN_ROI_BUY", "30"))
    MIN_ROI_MAYBE: float = float(os.getenv("MIN_ROI_MAYBE", "15"))

    STUBHUB_FEE_PERCENT: float = float(os.getenv("STUBHUB_FEE_PERCENT", "15"))
    VIAGOGO_FEE_PERCENT: float = float(os.getenv("VIAGOGO_FEE_PERCENT", "15"))
    TICKETMASTER_RESALE_FEE_PERCENT: float = float(
        os.getenv("TICKETMASTER_RESALE_FEE_PERCENT", "10")
    )
    COST_BUFFER: float = float(os.getenv("COST_BUFFER", "5.0"))

    # ── Alerts ───────────────────────────────────────────
    ALERT_EMAIL_ENABLED: bool = os.getenv("ALERT_EMAIL_ENABLED", "false").lower() == "true"
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    ALERT_RECIPIENT: str = os.getenv("ALERT_RECIPIENT", "")
    ALERT_MIN_PROFIT: float = float(os.getenv("ALERT_MIN_PROFIT", "20.0"))

    # ── Scan-Intervall ────────────────────────────────────
    SCAN_INTERVAL_MINUTES: int = int(os.getenv("SCAN_INTERVAL_MINUTES", "30"))

    # ── Datenbank ─────────────────────────────────────────
    DB_PATH: str = str(Path(__file__).parent / "ticket_scanner.db")


cfg = Config()
