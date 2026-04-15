"""Nachfrage-Analyse: Berechnet einen Demand-Score (0–100) und Sellout-Wahrscheinlichkeit."""
from datetime import datetime, timedelta
from database.models import Event


# Künstler-Tier: bekannte Mega-Acts = höhere Basisnachfrage
TIER1_KEYWORDS = {
    "taylor swift", "beyoncé", "beyonce", "coldplay", "harry styles",
    "ed sheeran", "rammstein", "metallica", "u2", "adele", "drake",
    "bad bunny", "kendrick lamar", "post malone",
}
TIER2_KEYWORDS = {
    "the weeknd", "dua lipa", "billie eilish", "arctic monkeys",
    "imagine dragons", "martin garrix", "david guetta", "tiësto",
}

# Venue-Kapazitäts-Schwellen
SMALL_VENUE = 2_000
MEDIUM_VENUE = 10_000
LARGE_VENUE = 50_000


class DemandAnalyzer:
    """Berechnet Demand-Score basierend auf mehreren Faktoren."""

    def analyze(self, event: Event) -> tuple[float, float]:
        """Gibt (demand_score 0–100, sellout_probability 0–1) zurück."""
        score = 0.0

        # 1. Künstler-Popularität (0–35 Punkte)
        score += self._artist_score(event.artist or event.name)

        # 2. Venue-Größe & Verfügbarkeit (0–20 Punkte)
        score += self._venue_score(event.capacity, event.tickets_available)

        # 3. Resale-Aktivität (0–25 Punkte)
        score += self._resale_activity_score(
            event.resale_listings_count or 0,
            event.resale_price_min or 0,
            event.primary_price_min or 0,
        )

        # 4. Zeitdruck (0–15 Punkte) — je näher das Event, desto höher
        score += self._time_pressure_score(event.event_date)

        # 5. Preisaufschlag auf Resale-Markt (0–5 Punkte)
        score += self._price_premium_score(
            event.resale_price_avg or 0,
            event.primary_price_min or 0,
        )

        score = min(score, 100.0)

        # Sellout-Wahrscheinlichkeit aus Demand-Score ableiten
        sellout_prob = self._estimate_sellout(score, event)

        return round(score, 1), round(sellout_prob, 3)

    # ── Teilscores ─────────────────────────────────────────

    def _artist_score(self, name: str) -> float:
        name_lower = name.lower()
        if any(kw in name_lower for kw in TIER1_KEYWORDS):
            return 35.0
        if any(kw in name_lower for kw in TIER2_KEYWORDS):
            return 22.0
        return 10.0   # Unbekannter Künstler

    def _venue_score(self, capacity: int, tickets_available: bool) -> float:
        base = 0.0
        if capacity > 0:
            if capacity < SMALL_VENUE:
                base = 20.0   # Kleine Venue -> knappe Tickets -> hohe Nachfrage
            elif capacity < MEDIUM_VENUE:
                base = 15.0
            elif capacity < LARGE_VENUE:
                base = 10.0
            else:
                base = 5.0
        else:
            base = 8.0   # Unbekannte Kapazität -> mittlere Einschätzung
        if not tickets_available:
            base = min(base + 5, 20)   # Ausverkauft -> Nachfrage noch höher
        return base

    def _resale_activity_score(
        self, listings: int, resale_min: float, primary_min: float
    ) -> float:
        """Viele Listings + hoher Aufschlag = hohe Nachfrage."""
        listing_score = min(listings / 20, 1.0) * 12    # max 12 Punkte
        premium_score = 0.0
        if primary_min > 0 and resale_min > 0:
            ratio = resale_min / primary_min
            premium_score = min((ratio - 1.0) * 10, 13)  # max 13 Punkte
        return listing_score + premium_score

    def _time_pressure_score(self, event_date: datetime | None) -> float:
        if event_date is None:
            return 5.0
        now = datetime.utcnow()
        days_left = (event_date - now).days
        if days_left < 0:
            return 0.0
        if days_left <= 7:
            return 15.0    # Sehr nah
        if days_left <= 30:
            return 10.0
        if days_left <= 90:
            return 7.0
        if days_left <= 180:
            return 4.0
        return 2.0

    def _price_premium_score(self, resale_avg: float, primary_min: float) -> float:
        if primary_min <= 0 or resale_avg <= 0:
            return 0.0
        ratio = resale_avg / primary_min
        if ratio >= 3.0:
            return 5.0
        if ratio >= 2.0:
            return 3.0
        if ratio >= 1.5:
            return 2.0
        return 0.0

    def _estimate_sellout(self, demand_score: float, event: Event) -> float:
        """Einfaches Modell: Hoher Score + nahe Datum = hohe Sellout-Wahrscheinlichkeit."""
        base_prob = demand_score / 100

        # Zeitbonus
        if event.event_date:
            days = (event.event_date - datetime.utcnow()).days
            if days <= 14:
                base_prob = min(base_prob * 1.3, 1.0)
            elif days <= 60:
                base_prob = min(base_prob * 1.1, 1.0)

        # Bereits kein Ticket mehr verfügbar
        if not event.tickets_available:
            base_prob = min(base_prob + 0.3, 1.0)

        return base_prob
