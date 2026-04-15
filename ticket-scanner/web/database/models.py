"""SQLAlchemy-Datenbankmodelle für alle Entitäten."""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, Float, String, DateTime, Boolean, Text, ForeignKey, Enum
)
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()


class DecisionType(str, enum.Enum):
    BUY = "BUY"
    MAYBE = "MAYBE"
    NO = "NO"


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Event(Base):
    """Gescanntes Event mit allen Rohdaten."""
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(200), unique=True, nullable=False)
    source = Column(String(50), nullable=False)          # ticketmaster, seatgeek, manual

    # Event-Info
    name = Column(String(500), nullable=False)
    artist = Column(String(300))
    category = Column(String(100))
    subcategory = Column(String(100))
    venue = Column(String(300))
    city = Column(String(100))
    country = Column(String(10))
    event_date = Column(DateTime)
    on_sale_date = Column(DateTime)

    # Primärmarkt-Preise
    primary_price_min = Column(Float)
    primary_price_max = Column(Float)
    primary_currency = Column(String(10), default="EUR")
    primary_url = Column(String(1000))
    tickets_available = Column(Boolean, default=True)
    capacity = Column(Integer)

    # Resale-Preise (aggregiert)
    resale_price_min = Column(Float)
    resale_price_avg = Column(Float)
    resale_price_max = Column(Float)
    resale_listings_count = Column(Integer, default=0)

    # Analyse-Ergebnisse
    demand_score = Column(Float, default=0.0)       # 0–100
    risk_score = Column(Float, default=0.0)          # 0–100
    competition_score = Column(Float, default=0.0)   # 0–100
    expected_profit = Column(Float, default=0.0)
    expected_roi = Column(Float, default=0.0)
    decision = Column(String(10))                    # BUY, MAYBE, NO
    decision_reason = Column(Text)

    # Metadaten
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_personalized = Column(Boolean, default=False)  # Risikofaktor
    sellout_probability = Column(Float, default=0.0)  # 0–1

    # Relationen
    price_history = relationship("PriceHistory", back_populates="event", cascade="all, delete")
    alerts = relationship("Alert", back_populates="event", cascade="all, delete")
    portfolio_entries = relationship("PortfolioEntry", back_populates="event")

    def __repr__(self):
        return f"<Event {self.name} @ {self.city} [{self.decision}]>"


class PriceHistory(Base):
    """Zeitreihe der Preisänderungen pro Event."""
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    primary_price_min = Column(Float)
    primary_price_max = Column(Float)
    resale_price_min = Column(Float)
    resale_price_avg = Column(Float)
    resale_price_max = Column(Float)
    resale_listings_count = Column(Integer)
    demand_score = Column(Float)

    event = relationship("Event", back_populates="price_history")


class PortfolioEntry(Base):
    """Ticket das der User gekauft hat."""
    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)

    # Kauf
    bought_at = Column(DateTime, default=datetime.utcnow)
    buy_price = Column(Float, nullable=False)
    quantity = Column(Integer, default=1)
    seat_category = Column(String(200))
    platform_bought = Column(String(100))   # ticketmaster, fanticket, ...

    # Verkauf
    sold_at = Column(DateTime)
    sell_price = Column(Float)
    platform_sold = Column(String(100))
    platform_fee = Column(Float, default=0.0)
    actual_profit = Column(Float)

    # Status
    status = Column(String(50), default="holding")  # holding, listed, sold, cancelled
    notes = Column(Text)

    event = relationship("Event", back_populates="portfolio_entries")

    @property
    def total_invested(self) -> float:
        return self.buy_price * self.quantity

    @property
    def net_profit(self) -> float | None:
        if self.sell_price is None:
            return None
        revenue = self.sell_price * self.quantity
        return revenue - self.total_invested - (self.platform_fee or 0)


class Alert(Base):
    """Generierte Alerts für profitable Deals."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    alert_type = Column(String(50))   # new_deal, price_drop, sellout_warning, sell_now
    message = Column(Text)
    expected_profit = Column(Float)
    expected_roi = Column(Float)
    decision = Column(String(10))
    is_sent = Column(Boolean, default=False)
    is_read = Column(Boolean, default=False)

    event = relationship("Event", back_populates="alerts")
