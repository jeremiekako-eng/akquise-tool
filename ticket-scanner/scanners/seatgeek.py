"""SeatGeek API Scanner — liefert Resale-Preise und Demand-Scores.

Kostenloser API-Key: https://platform.seatgeek.com/
SeatGeek hat einen eingebauten "score" (Popularitätswert 0–1).
"""
import time
import requests
from datetime import datetime
from scanners.base import BaseScanner, RawEvent
from config import cfg


SG_BASE = "https://api.seatgeek.com/2"


class SeatGeekScanner(BaseScanner):
    name = "seatgeek"

    def __init__(self):
        super().__init__()
        self.client_id = cfg.SEATGEEK_CLIENT_ID
        self.client_secret = cfg.SEATGEEK_CLIENT_SECRET
        self.session = requests.Session()

    # ── Öffentliche Methoden ────────────────────────────────

    def fetch_events(self, **kwargs) -> list[RawEvent]:
        """Events für alle konfigurierten Städte holen."""
        if not self.client_id:
            self.log_error("Kein SEATGEEK_CLIENT_ID gesetzt!")
            return []

        all_events: list[RawEvent] = []
        for city in cfg.TARGET_CITIES:
            events = self._fetch_city(city)
            all_events.extend(events)
            time.sleep(0.3)

        seen = set()
        unique = []
        for e in all_events:
            if e.external_id not in seen:
                seen.add(e.external_id)
                unique.append(e)
        return unique

    def get_resale_for_event(self, seatgeek_id: int) -> dict:
        """Aktueller Resale-Preise für ein bestimmtes Event."""
        url = f"{SG_BASE}/listings"
        params = {
            "client_id": self.client_id,
            "event_id": seatgeek_id,
            "per_page": 200,
        }
        if self.client_secret:
            params["client_secret"] = self.client_secret

        try:
            r = self.session.get(url, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            return self._parse_listings(data)
        except Exception as e:
            self.log_error(f"Listings fetch failed for event {seatgeek_id}: {e}")
            return {}

    def search_by_artist(self, artist: str) -> list[RawEvent]:
        """Alle Events eines Künstlers suchen."""
        return self._fetch_page(q=artist, per_page=50)

    # ── Interne Hilfsmethoden ───────────────────────────────

    def _fetch_city(self, city: str, per_page: int = 100) -> list[RawEvent]:
        return self._fetch_page(
            city=city,
            per_page=per_page,
            taxonomies="concert,sports",
        )

    def _fetch_page(self, **params) -> list[RawEvent]:
        base_params = {
            "client_id": self.client_id,
            "sort": "datetime_utc.asc",
        }
        if self.client_secret:
            base_params["client_secret"] = self.client_secret
        base_params.update(params)

        try:
            r = self.session.get(f"{SG_BASE}/events", params=base_params, timeout=15)
            r.raise_for_status()
            data = r.json()
        except requests.exceptions.HTTPError as e:
            self.log_error(f"HTTP {e.response.status_code}: {e}")
            return []
        except Exception as e:
            self.log_error(f"Request-Fehler: {e}")
            return []

        return [self._parse_event(e) for e in data.get("events", [])]

    def _parse_event(self, raw: dict) -> RawEvent:
        # Venue
        venue = raw.get("venue", {})
        city = venue.get("city", "")
        country = venue.get("country", "")
        venue_name = venue.get("name", "")

        # Kategorie
        taxonomies = raw.get("taxonomies", [{}])
        category = taxonomies[0].get("name", "") if taxonomies else ""

        # Performers / Künstler
        performers = raw.get("performers", [{}])
        artist = performers[0].get("name", "") if performers else ""

        # Stats (SeatGeek hat eingebaute Statistiken)
        stats = raw.get("stats", {})
        avg_price = float(stats.get("average_price", 0) or 0)
        min_price = float(stats.get("lowest_price", 0) or 0)
        max_price = float(stats.get("highest_price", 0) or 0)
        listing_count = int(stats.get("listing_count", 0) or 0)

        # Popularity score (0–1 bei SeatGeek, wir skalieren auf 0–100)
        score = float(raw.get("score", 0) or 0) * 100

        # Datum
        dt_str = raw.get("datetime_utc", "")
        event_dt = self._parse_dt(dt_str)

        return RawEvent(
            external_id=f"sg_{raw.get('id', '')}",
            source="seatgeek",
            name=raw.get("title", "Unknown"),
            artist=artist,
            category=category,
            venue=venue_name,
            city=city,
            country=country,
            event_date=event_dt,
            primary_price_min=min_price,
            primary_price_max=max_price,
            primary_currency="EUR",
            primary_url=raw.get("url", ""),
            resale_price_min=min_price,
            resale_price_avg=avg_price,
            resale_price_max=max_price,
            resale_listings_count=listing_count,
            extra={
                "sg_id": raw.get("id"),
                "sg_score": score,
                "sg_stats": stats,
            },
        )

    def _parse_listings(self, data: dict) -> dict:
        listings = data.get("listings", [])
        if not listings:
            return {}
        prices = [float(l.get("price", {}).get("amount", 0)) for l in listings
                  if l.get("price", {}).get("amount")]
        if not prices:
            return {}
        return {
            "resale_price_min": min(prices),
            "resale_price_avg": round(sum(prices) / len(prices), 2),
            "resale_price_max": max(prices),
            "resale_listings_count": len(prices),
        }

    @staticmethod
    def _parse_dt(dt_str: str) -> datetime | None:
        if not dt_str:
            return None
        try:
            return datetime.strptime(dt_str[:19], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return None
