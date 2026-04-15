"""Ticketmaster Discovery API Scanner.

Kostenloser API-Key: https://developer.ticketmaster.com/
Rate Limit: 5 requests/sec, 5000/day (kostenloser Plan)
"""
import time
from datetime import datetime
import requests
from scanners.base import BaseScanner, RawEvent
from config import cfg


TM_BASE = "https://app.ticketmaster.com/discovery/v2"


class TicketmasterScanner(BaseScanner):
    name = "ticketmaster"

    def __init__(self):
        super().__init__()
        self.api_key = cfg.TICKETMASTER_API_KEY
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "TicketScanner/1.0"})

    # ── Öffentliche Methoden ────────────────────────────────

    def fetch_events(self, **kwargs) -> list[RawEvent]:
        """Alle Events für konfigurierte Länder/Kategorien holen."""
        if not self.api_key:
            self.log_error("Kein TICKETMASTER_API_KEY gesetzt!")
            return []

        all_events: list[RawEvent] = []
        for country in cfg.TARGET_COUNTRIES:
            for category in cfg.TARGET_CATEGORIES:
                events = self._fetch_page(country=country, category=category)
                all_events.extend(events)
                time.sleep(0.2)  # Rate-Limit einhalten

        # Duplikate entfernen
        seen = set()
        unique: list[RawEvent] = []
        for e in all_events:
            if e.external_id not in seen:
                seen.add(e.external_id)
                unique.append(e)
        return unique

    def fetch_resale_prices(self, event_id: str) -> dict:
        """Resale-Preise für ein konkretes Event abrufen (TM Resale API)."""
        url = f"{TM_BASE}/events/{event_id}/offers.json"
        params = {"apikey": self.api_key}
        try:
            r = self.session.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            return self._parse_resale(data)
        except Exception as e:
            self.log_error(f"Resale fetch failed for {event_id}: {e}")
            return {}

    def search_artist(self, artist_name: str, country: str = "DE") -> list[RawEvent]:
        """Gezielt nach einem Künstler suchen."""
        return self._fetch_page(keyword=artist_name, country=country, size=50)

    # ── Interne Hilfsmethoden ───────────────────────────────

    def _fetch_page(
        self,
        country: str = "DE",
        category: str = "Music",
        keyword: str = "",
        size: int = 100,
        page: int = 0,
    ) -> list[RawEvent]:
        url = f"{TM_BASE}/events.json"
        params = {
            "apikey": self.api_key,
            "countryCode": country,
            "classificationName": category,
            "size": size,
            "page": page,
            "sort": "date,asc",
        }
        if keyword:
            params["keyword"] = keyword

        try:
            r = self.session.get(url, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
        except requests.exceptions.HTTPError as e:
            self.log_error(f"HTTP {e.response.status_code} für {country}/{category}")
            return []
        except Exception as e:
            self.log_error(f"Request-Fehler: {e}")
            return []

        embedded = data.get("_embedded", {})
        raw_events = embedded.get("events", [])
        return [self._parse_event(e, country) for e in raw_events]

    def _parse_event(self, raw: dict, country: str) -> RawEvent:
        # Datum
        dates = raw.get("dates", {})
        start = dates.get("start", {})
        event_dt = self._parse_dt(start.get("dateTime") or start.get("localDate"))

        # Venue
        venues = raw.get("_embedded", {}).get("venues", [{}])
        venue = venues[0] if venues else {}
        venue_name = venue.get("name", "")
        city = venue.get("city", {}).get("name", "")
        venue_country = venue.get("country", {}).get("countryCode", country)

        # Kategorie
        classifications = raw.get("classifications", [{}])
        cls = classifications[0] if classifications else {}
        segment = cls.get("segment", {}).get("name", "")
        genre = cls.get("genre", {}).get("name", "")

        # Preise
        price_ranges = raw.get("priceRanges", [])
        price_min = price_max = 0.0
        currency = "EUR"
        if price_ranges:
            pr = price_ranges[0]
            price_min = float(pr.get("min", 0))
            price_max = float(pr.get("max", 0))
            currency = pr.get("currency", "EUR")

        # Personalisierung erkennen
        ticket_limit = raw.get("ticketLimit", {})
        is_personalized = "personali" in str(raw).lower()

        # Kapazität (falls vorhanden)
        info = raw.get("info", "")
        capacity = self._extract_capacity(info)

        # Artist-Name
        attractions = raw.get("_embedded", {}).get("attractions", [{}])
        artist = attractions[0].get("name", "") if attractions else ""

        return RawEvent(
            external_id=f"tm_{raw.get('id', '')}",
            source="ticketmaster",
            name=raw.get("name", "Unknown"),
            artist=artist,
            category=segment,
            subcategory=genre,
            venue=venue_name,
            city=city,
            country=venue_country,
            event_date=event_dt,
            on_sale_date=self._parse_dt(
                dates.get("access", {}).get("startDateTime")
            ),
            primary_price_min=price_min,
            primary_price_max=price_max,
            primary_currency=currency,
            primary_url=raw.get("url", ""),
            tickets_available=not dates.get("status", {}).get("code") == "onsalewithsellout",
            capacity=capacity,
            is_personalized=is_personalized,
            extra={"tm_id": raw.get("id"), "tm_status": dates.get("status", {}).get("code")},
        )

    def _parse_resale(self, data: dict) -> dict:
        """Resale-Offer-Daten normalisieren."""
        offers = data.get("_embedded", {}).get("offers", [])
        if not offers:
            return {}
        prices = [float(o.get("attributes", {}).get("price", 0)) for o in offers if o.get("attributes", {}).get("price")]
        if not prices:
            return {}
        return {
            "resale_price_min": min(prices),
            "resale_price_avg": sum(prices) / len(prices),
            "resale_price_max": max(prices),
            "resale_listings_count": len(prices),
        }

    @staticmethod
    def _parse_dt(dt_str: str | None) -> datetime | None:
        if not dt_str:
            return None
        for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(dt_str[:19], fmt[:len(dt_str[:19])])
            except ValueError:
                continue
        return None

    @staticmethod
    def _extract_capacity(info: str) -> int:
        """Versucht Kapazitätszahl aus Infotext zu extrahieren."""
        import re
        match = re.search(r"(\d[\d,]+)\s*(?:seats?|capacity|Kapazität)", info, re.IGNORECASE)
        if match:
            return int(match.group(1).replace(",", ""))
        return 0
