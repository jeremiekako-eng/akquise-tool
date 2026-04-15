"""Portfolio-Tracker: Gekaufte Tickets verwalten und P&L berechnen."""
from datetime import datetime
from database.db import get_db
from database.models import PortfolioEntry, Event


class PortfolioTracker:

    def add_ticket(
        self,
        event_id: int,
        buy_price: float,
        quantity: int = 1,
        seat_category: str = "",
        platform_bought: str = "",
        notes: str = "",
    ) -> PortfolioEntry:
        """Neues Ticket ins Portfolio aufnehmen."""
        with get_db() as db:
            entry = PortfolioEntry(
                event_id=event_id,
                buy_price=buy_price,
                quantity=quantity,
                seat_category=seat_category,
                platform_bought=platform_bought,
                notes=notes,
                status="holding",
            )
            db.add(entry)
            db.flush()
            db.refresh(entry)
            return entry

    def mark_sold(
        self,
        entry_id: int,
        sell_price: float,
        platform_sold: str,
        platform_fee: float | None = None,
    ) -> PortfolioEntry | None:
        """Ticket als verkauft markieren und Profit berechnen."""
        with get_db() as db:
            entry = db.get(PortfolioEntry, entry_id)
            if not entry:
                return None

            if platform_fee is None:
                # Geschätzte Gebühr (15%)
                platform_fee = sell_price * entry.quantity * 0.15

            entry.sold_at = datetime.utcnow()
            entry.sell_price = sell_price
            entry.platform_sold = platform_sold
            entry.platform_fee = platform_fee
            entry.status = "sold"
            entry.actual_profit = (
                sell_price * entry.quantity
                - entry.buy_price * entry.quantity
                - platform_fee
            )
            db.flush()
            db.refresh(entry)
            return entry

    def get_portfolio(self, status: str | None = None) -> list[dict]:
        """Portfolio-Übersicht mit Event-Details."""
        with get_db() as db:
            query = db.query(PortfolioEntry).join(Event)
            if status:
                query = query.filter(PortfolioEntry.status == status)
            entries = query.all()

            result = []
            for e in entries:
                event = db.get(Event, e.event_id)
                result.append({
                    "id": e.id,
                    "event": event.name if event else "Unknown",
                    "city": event.city if event else "",
                    "event_date": event.event_date.strftime("%d.%m.%Y") if event and event.event_date else "?",
                    "status": e.status,
                    "quantity": e.quantity,
                    "buy_price": e.buy_price,
                    "total_invested": e.total_invested,
                    "sell_price": e.sell_price,
                    "actual_profit": e.actual_profit,
                    "platform_sold": e.platform_sold,
                    "notes": e.notes,
                    "bought_at": e.bought_at.strftime("%d.%m.%Y") if e.bought_at else "?",
                    "sold_at": e.sold_at.strftime("%d.%m.%Y") if e.sold_at else None,
                    "expected_profit": event.expected_profit if event else 0,
                    "expected_roi": event.expected_roi if event else 0,
                    "current_resale_avg": event.resale_price_avg if event else 0,
                })
            return result

    def get_summary(self) -> dict:
        """Gesamte P&L-Übersicht."""
        portfolio = self.get_portfolio()
        holding = [p for p in portfolio if p["status"] == "holding"]
        sold = [p for p in portfolio if p["status"] == "sold"]

        total_invested = sum(p["total_invested"] for p in holding)
        total_profit = sum(p["actual_profit"] or 0 for p in sold)
        total_revenue = sum(
            (p["sell_price"] or 0) * p["quantity"] for p in sold
        )
        total_cost = sum(p["total_invested"] for p in sold)
        total_roi = (total_profit / total_cost * 100) if total_cost > 0 else 0

        # Unrealisierter Gewinn (aktuelle Resale-Preise)
        unrealized = sum(
            ((p["current_resale_avg"] or 0) - p["buy_price"]) * p["quantity"]
            for p in holding
        )

        return {
            "total_tickets_holding": sum(p["quantity"] for p in holding),
            "total_tickets_sold": sum(p["quantity"] for p in sold),
            "total_invested_holding": round(total_invested, 2),
            "total_realized_profit": round(total_profit, 2),
            "total_realized_roi": round(total_roi, 1),
            "unrealized_profit_estimate": round(unrealized, 2),
            "total_revenue": round(total_revenue, 2),
        }
