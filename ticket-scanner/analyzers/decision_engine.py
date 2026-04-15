"""Entscheidungs-Engine: Berechnet Profit, ROI und gibt BUY / MAYBE / NO aus.

Formel:
    expected_profit = expected_sell_price - buy_price - fees - cost_buffer
    roi = expected_profit / buy_price * 100

Entscheidung:
    BUY   -> ROI >= MIN_ROI_BUY  UND risk_level != HIGH
    MAYBE -> ROI >= MIN_ROI_MAYBE UND risk_level != HIGH
    NO    -> alles andere
"""
from dataclasses import dataclass
from database.models import Event
from analyzers.demand_analyzer import DemandAnalyzer
from analyzers.risk_analyzer import RiskAnalyzer, RiskFactor
from config import cfg


@dataclass
class AnalysisResult:
    decision: str                    # BUY, MAYBE, NO
    expected_profit: float
    expected_roi: float              # in %
    demand_score: float              # 0–100
    risk_score: float                # 0–100
    risk_level: str                  # LOW, MEDIUM, HIGH
    sellout_probability: float       # 0–1
    buy_price: float
    estimated_sell_price: float
    total_fees: float
    reasons: list[str]
    risk_factors: list[RiskFactor]
    recommendation_text: str


class DecisionEngine:
    """Bringt alle Analyzer zusammen und trifft die finale Entscheidung."""

    def __init__(self):
        self.demand_analyzer = DemandAnalyzer()
        self.risk_analyzer = RiskAnalyzer()

    def analyze(self, event: Event) -> AnalysisResult:
        # Schritt 1: Demand & Risk berechnen
        demand_score, sellout_prob = self.demand_analyzer.analyze(event)
        risk_score, risk_factors = self.risk_analyzer.analyze(event)
        risk_level = self.risk_analyzer.risk_level(risk_score)

        # Schritt 2: Preise bestimmen
        buy_price = event.primary_price_min or 0.0
        estimated_sell_price = self._estimate_sell_price(event, demand_score)
        total_fees = self._calculate_fees(estimated_sell_price)

        # Schritt 3: Profit-Berechnung
        expected_profit = (
            estimated_sell_price - buy_price - total_fees - cfg.COST_BUFFER
        )
        roi = (expected_profit / buy_price * 100) if buy_price > 0 else 0.0

        # Schritt 4: Entscheidung
        reasons: list[str] = []
        decision = self._decide(roi, risk_level, buy_price, event, reasons)

        recommendation = self._build_recommendation(
            decision, roi, expected_profit, risk_level, demand_score, event
        )

        return AnalysisResult(
            decision=decision,
            expected_profit=round(expected_profit, 2),
            expected_roi=round(roi, 1),
            demand_score=demand_score,
            risk_score=risk_score,
            risk_level=risk_level,
            sellout_probability=sellout_prob,
            buy_price=buy_price,
            estimated_sell_price=round(estimated_sell_price, 2),
            total_fees=round(total_fees, 2),
            reasons=reasons,
            risk_factors=risk_factors,
            recommendation_text=recommendation,
        )

    # ── Interne Logik ──────────────────────────────────────

    def _estimate_sell_price(self, event: Event, demand_score: float) -> float:
        """
        Schätzt den realistischen Verkaufspreis.
        Priorität: Resale-Daten -> Primärpreis-Multiplikator -> 0
        """
        # Wenn Resale-Daten vorhanden, nutze den Durchschnitt (konservativ)
        if event.resale_price_avg and event.resale_price_avg > 0:
            # Bei hohem Demand eher den Avg, bei niedrigem den Min nehmen
            if demand_score >= 70:
                return event.resale_price_avg
            elif demand_score >= 50:
                avg = event.resale_price_avg
                low = event.resale_price_min or avg
                return (avg + low) / 2   # konservativer Mittelwert
            else:
                return event.resale_price_min or event.resale_price_avg

        # Fallback: Schätzung via Demand-Score-Multiplikator
        primary = event.primary_price_min or 0
        if primary <= 0:
            return 0.0

        if demand_score >= 80:
            multiplier = 2.0
        elif demand_score >= 65:
            multiplier = 1.6
        elif demand_score >= 50:
            multiplier = 1.35
        elif demand_score >= 35:
            multiplier = 1.15
        else:
            multiplier = 1.0

        return primary * multiplier

    def _calculate_fees(self, sell_price: float) -> float:
        """Berechnet Plattform-Gebühren (worst-case: StubHub/Viagogo)."""
        # Wir rechnen mit dem höchsten marktüblichen Satz
        fee_rate = max(
            cfg.STUBHUB_FEE_PERCENT,
            cfg.VIAGOGO_FEE_PERCENT,
            cfg.TICKETMASTER_RESALE_FEE_PERCENT,
        ) / 100
        return sell_price * fee_rate

    def _decide(
        self,
        roi: float,
        risk_level: str,
        buy_price: float,
        event: Event,
        reasons: list[str],
    ) -> str:
        # Harte Ausschluss-Kriterien
        if buy_price <= 0:
            reasons.append("Kein Primärpreis verfügbar.")
            return "NO"
        if event.is_personalized:
            reasons.append("Personalisiertes Ticket — Weiterverkauf verboten/unmöglich.")
            return "NO"
        if risk_level == "HIGH":
            reasons.append(f"Risiko-Level: HIGH (Score {event.risk_score:.0f}) — zu riskant.")
            return "NO"

        # ROI-basierte Entscheidung
        if roi >= cfg.MIN_ROI_BUY:
            reasons.append(
                f"ROI {roi:.1f}% >= {cfg.MIN_ROI_BUY}% Mindest-ROI. "
                f"Erwarteter Profit: {event.expected_profit:.2f}€."
            )
            return "BUY"

        if roi >= cfg.MIN_ROI_MAYBE:
            reasons.append(
                f"ROI {roi:.1f}% im Maybe-Bereich ({cfg.MIN_ROI_MAYBE}%–{cfg.MIN_ROI_BUY}%). "
                "Manuell prüfen."
            )
            return "MAYBE"

        reasons.append(
            f"ROI {roi:.1f}% < {cfg.MIN_ROI_MAYBE}% Mindest-ROI — nicht profitabel genug."
        )
        return "NO"

    def _build_recommendation(
        self,
        decision: str,
        roi: float,
        profit: float,
        risk_level: str,
        demand_score: float,
        event: Event,
    ) -> str:
        base = f"[{decision}] ROI: {roi:.1f}% | Profit: {profit:.2f}€ | Risiko: {risk_level} | Demand: {demand_score:.0f}/100"
        if decision == "BUY":
            timing = self._buy_timing(event)
            return f"{base}\n-> KAUFEN. {timing}"
        if decision == "MAYBE":
            return f"{base}\n-> PRÜFEN: Resale-Preise beobachten. Bei steigendem Demand kaufen."
        return f"{base}\n-> NICHT KAUFEN. Profit nach Gebühren zu gering oder Risiko zu hoch."

    def _buy_timing(self, event: Event) -> str:
        from datetime import datetime
        if not event.event_date:
            return "Jetzt kaufen solange Tickets verfügbar."
        days = (event.event_date - datetime.utcnow()).days
        if days <= 30:
            return "Sofort kaufen — Event nah, Preise werden weiter steigen."
        if days <= 90:
            return "Bald kaufen — Demand steigt in den nächsten Wochen."
        return "Kaufen, aber Entwicklung beobachten. Noch genug Zeit."
