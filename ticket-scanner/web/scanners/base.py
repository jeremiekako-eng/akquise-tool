"""Basis-Klasse für alle Event-Scanner."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawEvent:
    """Normalisiertes Event-Objekt — unabhängig von der Quelle."""
    external_id: str
    source: str
    name: str

    # Optionale Felder
    artist: str = ""
    category: str = ""
    subcategory: str = ""
    venue: str = ""
    city: str = ""
    country: str = ""
    event_date: datetime | None = None
    on_sale_date: datetime | None = None

    # Preise
    primary_price_min: float = 0.0
    primary_price_max: float = 0.0
    primary_currency: str = "EUR"
    primary_url: str = ""
    tickets_available: bool = True
    capacity: int = 0

    # Resale (falls direkt aus API verfügbar)
    resale_price_min: float = 0.0
    resale_price_avg: float = 0.0
    resale_price_max: float = 0.0
    resale_listings_count: int = 0

    is_personalized: bool = False
    extra: dict = field(default_factory=dict)


class BaseScanner(ABC):
    """Abstrakte Basis für alle Scanner."""

    name: str = "base"

    def __init__(self):
        self.errors: list[str] = []

    @abstractmethod
    def fetch_events(self, **kwargs) -> list[RawEvent]:
        """Hauptmethode: Events von der Quelle holen."""
        ...

    def log_error(self, msg: str) -> None:
        self.errors.append(msg)
        print(f"[{self.name}] ERROR: {msg}")
