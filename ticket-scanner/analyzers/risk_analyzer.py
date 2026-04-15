"""Risiko-Analyse: Berechnet Risk-Score (0–100) und identifiziert Risikofaktoren."""
from datetime import datetime
from database.models import Event


class RiskFactor:
    def __init__(self, name: str, score: float, description: str):
        self.name = name
        self.score = score          # Beitrag zum Risk-Score
        self.description = description


class RiskAnalyzer:
    """Bewertet das Gesamtrisiko eines Ticket-Kaufs."""

    def analyze(self, event: Event) -> tuple[float, list[RiskFactor]]:
        """Gibt (risk_score 0–100, [Risikofaktoren]) zurück."""
        factors: list[RiskFactor] = []

        # 1. Personalisierte Tickets (größtes Risiko)
        if event.is_personalized:
            factors.append(RiskFactor(
                "Personalisiertes Ticket",
                40.0,
                "Tickets sind auf den Käufer personalisiert — Weiterverkauf sehr schwierig oder verboten.",
            ))

        # 2. Zu niedriger Resale-Aufschlag
        factors.extend(self._check_price_spread(event))

        # 3. Hohe Konkurrenz (viele Listings)
        factors.extend(self._check_competition(event))

        # 4. Zeitrisiko (Event sehr weit in der Zukunft)
        factors.extend(self._check_time_risk(event))

        # 5. Liquiditätsrisiko (wenig Listings -> schwer zu verkaufen)
        factors.extend(self._check_liquidity(event))

        # 6. Kleines Venue (evtl. Event abgesagt)
        factors.extend(self._check_cancellation_risk(event))

        risk_score = min(sum(f.score for f in factors), 100.0)
        return round(risk_score, 1), factors

    def risk_level(self, risk_score: float) -> str:
        if risk_score >= 60:
            return "HIGH"
        if risk_score >= 30:
            return "MEDIUM"
        return "LOW"

    # ── Einzelne Risiko-Checks ─────────────────────────────

    def _check_price_spread(self, event: Event) -> list[RiskFactor]:
        factors = []
        primary = event.primary_price_min or 0
        resale_avg = event.resale_price_avg or 0
        if primary <= 0:
            return []
        if resale_avg <= 0:
            factors.append(RiskFactor(
                "Keine Resale-Daten",
                10.0,
                "Resale-Preise unbekannt — Verkaufspreis unsicher.",
            ))
            return factors

        ratio = resale_avg / primary
        if ratio < 1.1:
            factors.append(RiskFactor(
                "Minimaler Preisaufschlag",
                25.0,
                f"Resale-Durchschnitt nur {ratio:.1f}x des Primärpreises — kaum Gewinnpotenzial nach Gebühren.",
            ))
        elif ratio < 1.2:
            factors.append(RiskFactor(
                "Geringer Preisaufschlag",
                12.0,
                f"Resale-Durchschnitt {ratio:.1f}x Primärpreis — Gebühren können Profit auffressen.",
            ))
        return factors

    def _check_competition(self, event: Event) -> list[RiskFactor]:
        listings = event.resale_listings_count or 0
        if listings > 500:
            return [RiskFactor(
                "Sehr hohe Konkurrenz",
                20.0,
                f"{listings} aktive Listings — starker Preisdruck, schwierig zum Zielpreis zu verkaufen.",
            )]
        if listings > 200:
            return [RiskFactor(
                "Hohe Konkurrenz",
                10.0,
                f"{listings} aktive Listings — Preisdruck möglich.",
            )]
        return []

    def _check_time_risk(self, event: Event) -> list[RiskFactor]:
        if not event.event_date:
            return []
        days = (event.event_date - datetime.utcnow()).days
        if days > 365:
            return [RiskFactor(
                "Weit entferntes Event",
                15.0,
                f"Event ist in {days} Tagen — hohes Risiko für Absage, Verlegung oder Preisverfall.",
            )]
        if days > 180:
            return [RiskFactor(
                "Event in fernerer Zukunft",
                8.0,
                f"Event in {days} Tagen — moderates Risiko für Preisveränderungen.",
            )]
        return []

    def _check_liquidity(self, event: Event) -> list[RiskFactor]:
        listings = event.resale_listings_count or 0
        if 0 < listings < 5:
            return [RiskFactor(
                "Geringe Liquidität",
                15.0,
                "Nur wenige Listings vorhanden — Markt evtl. zu klein für schnellen Verkauf.",
            )]
        if listings == 0 and (event.resale_price_min or 0) == 0:
            return [RiskFactor(
                "Kein Resale-Markt erkennbar",
                20.0,
                "Keine Resale-Aktivität gefunden — Marktgröße unbekannt.",
            )]
        return []

    def _check_cancellation_risk(self, event: Event) -> list[RiskFactor]:
        """Kleine/unbekannte Venues haben höheres Absagerisiko."""
        factors = []
        name_lower = (event.name or "").lower()
        if any(kw in name_lower for kw in ["tba", "to be announced", "venue tbc"]):
            factors.append(RiskFactor(
                "Venue unbekannt",
                10.0,
                "Venue noch nicht bestätigt — Organisationsrisiko.",
            ))
        return factors
