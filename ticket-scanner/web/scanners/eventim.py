"""Eventim Scraper — nutzt die interne Eventim-API über tls-client.

Kein offizieller API-Key nötig. Verwendet denselben Endpunkt wie der Browser.
Rate Limit: 1 Request/Sekunde (höfliches Scraping).
"""
import time
import re
from datetime import datetime
from scanners.base import BaseScanner, RawEvent
from config import cfg

try:
    import tls_client
    TLS_AVAILABLE = True
except ImportError:
    TLS_AVAILABLE = False

# Eventim interne API (aus dem Browser-Source extrahiert)
EVENTIM_API = "https://public-api.eventim.com/websearch/search/api/exploration"
EVENTIM_WEB_ID = "web__eventim-de"
EVENTIM_BASE = "https://www.eventim.de"

# Standard-Städte-IDs (Eventim intern)
CITY_IDS = {
    "Berlin":    "1",
    "Hamburg":   "2",
    "München":   "3",
    "Frankfurt": "5",
    "Köln":      "6",
    "Stuttgart": "7",
    "Leipzig":   "8",
    "Düsseldorf": "9",
    "Wien":      "103",
    "Zürich":    "200",
}


class EventimScanner(BaseScanner):
    name = "eventim"

    def __init__(self):
        super().__init__()
        if not TLS_AVAILABLE:
            self.log_error("tls-client nicht installiert: pip install tls-client")
            self._session = None
            return
        self._session = self._create_session()
        self._init_cookies()

    # ── Öffentliche Methoden ────────────────────────────────

    def fetch_events(self, **kwargs) -> list[RawEvent]:
        """Events für alle konfigurierten Städte holen."""
        if not self._session:
            return []

        all_events: list[RawEvent] = []
        for city in cfg.TARGET_CITIES:
            if not city:
                continue
            events = self._fetch_city_events(city)
            all_events.extend(events)
            time.sleep(1.0)   # Höfliches Rate-Limiting

        # Duplikate entfernen
        seen = set()
        return [e for e in all_events if not (e.external_id in seen or seen.add(e.external_id))]

    def search_artist(self, artist_name: str) -> list[RawEvent]:
        """Events für einen bestimmten Künstler suchen."""
        if not self._session:
            return []
        return self._fetch_product_groups(search_term=artist_name, rows=50)

    def fetch_top_events(self, rows: int = 50) -> list[RawEvent]:
        """Meistgesuchte Events holen (ohne Suchbegriff)."""
        if not self._session:
            return []
        return self._fetch_product_groups(search_term="", rows=rows, sort="Recommendation")

    # ── Interne Hilfsmethoden ───────────────────────────────

    def _create_session(self):
        session = tls_client.Session(
            client_identifier="chrome_120",
            random_tls_extension_order=True,
        )
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": EVENTIM_BASE,
            "Referer": f"{EVENTIM_BASE}/",
            "x-api-client-id": EVENTIM_WEB_ID,
        })
        return session

    def _init_cookies(self) -> None:
        """Cookies durch Startseiten-Aufruf initialisieren (wie echter Browser)."""
        try:
            self._session.get(f"{EVENTIM_BASE}/", timeout_seconds=12)
        except Exception as e:
            self.log_error(f"Cookie-Init fehlgeschlagen: {e}")

    def _fetch_city_events(self, city: str, rows: int = 50) -> list[RawEvent]:
        """Events für eine Stadt — Konzerte & Sport."""
        # Eventim gibt keine saubere Kategorie-Filterung per API,
        # daher holen wir mehr Events und filtern client-seitig.
        all_events = self._fetch_product_groups(city=city, rows=rows, sort="DateAsc")

        # Nur relevante Kategorien behalten
        RELEVANT = {"konzert", "rock", "pop", "festival", "sport", "musical",
                    "comedy", "live", "show", "hiphop", "electronic", "classical"}
        filtered = []
        for e in all_events:
            cat = (e.category + " " + e.subcategory).lower()
            if any(kw in cat for kw in RELEVANT) or e.primary_price_min > 0:
                filtered.append(e)
        return filtered

    def _fetch_product_groups(
        self,
        search_term: str = "",
        rows: int = 30,
        start: int = 0,
        sort: str = "DateAsc",
        **extra_params,
    ) -> list[RawEvent]:
        """Kern-API: productGroups (= Event-Serien / Konzerte)."""
        url = f"{EVENTIM_API}/v2/productGroups"
        params = {
            "webId": EVENTIM_WEB_ID,
            "language": "de",
            "rows": rows,
            "start": start,
            "sort": sort,
        }
        if search_term:
            params["search_term"] = search_term
        params.update(extra_params)

        try:
            r = self._session.get(url, params=params, timeout_seconds=15)
            if r.status_code != 200:
                self.log_error(f"API {r.status_code} für {search_term or 'top'}: {r.text[:100]}")
                return []
            data = r.json()
        except Exception as e:
            self.log_error(f"Request-Fehler: {e}")
            return []

        groups = data.get("productGroups", [])
        events: list[RawEvent] = []
        for g in groups:
            events.extend(self._parse_product_group(g))
        return events

    def _parse_product_group(self, raw: dict) -> list[RawEvent]:
        """Ein productGroup in einzelne RawEvents (pro Konzerttermin) umwandeln."""
        group_id = raw.get("productGroupId", "")
        if not group_id:
            return []

        group_name = raw.get("name", "")
        currency = raw.get("currency", "EUR")
        image_url = raw.get("imageUrl", "")
        is_personalized = "PERSONALIZED" in raw.get("tags", [])
        group_link = raw.get("link", "")

        # Kategorie
        categories = raw.get("categories", [])
        category_name = categories[0].get("name", "Konzerte") if categories else "Konzerte"
        subcategory = categories[1].get("name", "") if len(categories) > 1 else ""

        # Bewertung
        rating = raw.get("rating") or {}
        rating_avg = float(rating.get("average", 0) or 0)
        rating_count = int(rating.get("count", 0) or 0)

        # Produktliste (einzelne Termine) durchgehen
        products = raw.get("products", [])
        if not products:
            # Fallback: nur Gruppen-Eintrag ohne Einzeltermine
            return [self._make_raw_event(
                external_id=f"eim_{group_id}",
                name=group_name,
                artist=group_name,
                category=category_name,
                subcategory=subcategory,
                venue="", city="", country="DE",
                event_dt=self._parse_dt(raw.get("startDate")),
                min_price=0.0, max_price=0.0,
                currency=currency,
                link=group_link,
                tickets_available=raw.get("status", "") != "SoldOut",
                is_personalized=is_personalized,
                image_url=image_url,
                rating_avg=rating_avg, rating_count=rating_count,
            )]

        results = []
        for product in products:
            product_id = product.get("productId", "")
            product_link = product.get("link", group_link)
            product_status = product.get("status", "Available")
            tickets_available = product_status not in ("SoldOut", "Unavailable")

            # Location aus typeAttributes
            live = (product.get("typeAttributes") or {}).get("liveEntertainment") or {}
            location = live.get("location") or {}
            venue = location.get("name", "")
            city = location.get("city", "")
            country = location.get("countryCode", "DE")

            # Datum
            event_dt = self._parse_dt(live.get("startDate") or raw.get("startDate"))

            # Preise — manchmal in priceRanges oder ticketTypes
            price_ranges = product.get("priceRanges") or []
            if price_ranges:
                min_price = float(min(p.get("min", 0) for p in price_ranges))
                max_price = float(max(p.get("max", 0) for p in price_ranges))
            else:
                min_price = float(product.get("minPrice") or raw.get("minPrice") or 0)
                max_price = float(product.get("maxPrice") or raw.get("maxPrice") or 0)

            ext_id = f"eim_{product_id}" if product_id else f"eim_{group_id}"

            results.append(self._make_raw_event(
                external_id=ext_id,
                name=group_name,
                artist=group_name,
                category=category_name,
                subcategory=subcategory,
                venue=venue,
                city=city,
                country=country,
                event_dt=event_dt,
                min_price=min_price,
                max_price=max_price,
                currency=currency,
                link=product_link,
                tickets_available=tickets_available,
                is_personalized=is_personalized,
                image_url=image_url,
                rating_avg=rating_avg,
                rating_count=rating_count,
                extra_id=group_id,
            ))

        return results

    @staticmethod
    def _make_raw_event(
        external_id, name, artist, category, subcategory,
        venue, city, country, event_dt, min_price, max_price,
        currency, link, tickets_available, is_personalized,
        image_url, rating_avg, rating_count, extra_id=None,
    ) -> RawEvent:
        return RawEvent(
            external_id=external_id,
            source="eventim",
            name=name,
            artist=artist,
            category=category,
            subcategory=subcategory,
            venue=venue,
            city=city,
            country=country or "DE",
            event_date=event_dt,
            primary_price_min=min_price,
            primary_price_max=max_price,
            primary_currency=currency,
            primary_url=link,
            tickets_available=tickets_available,
            is_personalized=is_personalized,
            extra={
                "eim_group_id": extra_id,
                "image_url": image_url,
                "rating_avg": rating_avg,
                "rating_count": rating_count,
            },
        )

    @staticmethod
    def _parse_dt(dt_str: str | None) -> datetime | None:
        if not dt_str:
            return None
        # Format: 2026-04-17T20:30:00+02:00
        clean = dt_str[:19]
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(clean, fmt)
            except ValueError:
                continue
        return None
