"""Alert-System: Benachrichtigungen bei profitablen Deals."""
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from database.db import get_db
from database.models import Alert, Event
from analyzers.decision_engine import AnalysisResult
from config import cfg


class Notifier:
    """Erstellt Alerts und versendet optionale E-Mail-Benachrichtigungen."""

    def create_alert(
        self,
        event: Event,
        result: AnalysisResult,
        alert_type: str = "new_deal",
    ) -> Alert | None:
        """Alert in DB speichern und ggf. per E-Mail versenden."""
        if result.expected_profit < cfg.ALERT_MIN_PROFIT:
            return None
        if result.decision == "NO":
            return None

        with get_db() as db:
            # Duplikat-Check (heute schon gemeldet?)
            today = datetime.utcnow().date()
            existing = (
                db.query(Alert)
                .filter(
                    Alert.event_id == event.id,
                    Alert.alert_type == alert_type,
                )
                .first()
            )
            if existing and existing.created_at.date() == today:
                return None   # Heute schon Alert für dieses Event

            alert = Alert(
                event_id=event.id,
                alert_type=alert_type,
                message=result.recommendation_text,
                expected_profit=result.expected_profit,
                expected_roi=result.expected_roi,
                decision=result.decision,
            )
            db.add(alert)
            db.flush()
            db.refresh(alert)

        if cfg.ALERT_EMAIL_ENABLED:
            self._send_email(event, result, alert)

        return alert

    def get_unread_alerts(self) -> list[dict]:
        with get_db() as db:
            alerts = (
                db.query(Alert)
                .filter(Alert.is_read == False)  # noqa: E712
                .order_by(Alert.created_at.desc())
                .limit(50)
                .all()
            )
            result = []
            for a in alerts:
                event = db.get(Event, a.event_id)
                result.append({
                    "id": a.id,
                    "event": event.name if event else "Unknown",
                    "city": event.city if event else "",
                    "event_date": event.event_date.strftime("%d.%m.%Y") if event and event.event_date else "?",
                    "decision": a.decision,
                    "type": a.alert_type,
                    "profit": a.expected_profit,
                    "roi": a.expected_roi,
                    "message": a.message,
                    "created_at": a.created_at.strftime("%d.%m.%Y %H:%M"),
                })
            return result

    def mark_all_read(self) -> None:
        with get_db() as db:
            db.query(Alert).filter(Alert.is_read == False).update(  # noqa: E712
                {"is_read": True}
            )

    # ── E-Mail ──────────────────────────────────────────────

    def _send_email(self, event: Event, result: AnalysisResult, alert: Alert) -> None:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[{result.decision}] {event.name} — {result.expected_profit:.2f}€ Profit"
            msg["From"] = cfg.SMTP_USER
            msg["To"] = cfg.ALERT_RECIPIENT

            body = self._build_email_body(event, result)
            msg.attach(MIMEText(body, "html"))

            with smtplib.SMTP(cfg.SMTP_HOST, cfg.SMTP_PORT) as server:
                server.starttls()
                server.login(cfg.SMTP_USER, cfg.SMTP_PASSWORD)
                server.sendmail(cfg.SMTP_USER, cfg.ALERT_RECIPIENT, msg.as_string())

            with get_db() as db:
                db_alert = db.get(Alert, alert.id)
                if db_alert:
                    db_alert.is_sent = True
        except Exception as e:
            print(f"[Alert] E-Mail-Versand fehlgeschlagen: {e}")

    def _build_email_body(self, event: Event, result: AnalysisResult) -> str:
        color = {"BUY": "#22c55e", "MAYBE": "#f59e0b", "NO": "#ef4444"}.get(result.decision, "#888")
        date_str = event.event_date.strftime("%d.%m.%Y %H:%M") if event.event_date else "Datum unbekannt"
        return f"""
        <html><body style="font-family: sans-serif; max-width: 600px; margin: auto;">
        <h2 style="color: {color};">[{result.decision}] {event.name}</h2>
        <table border="0" cellpadding="8" style="width:100%; border-collapse:collapse;">
            <tr><td><b>Datum</b></td><td>{date_str}</td></tr>
            <tr><td><b>Venue</b></td><td>{event.venue}, {event.city}</td></tr>
            <tr><td><b>Kaufpreis</b></td><td>{result.buy_price:.2f}€</td></tr>
            <tr><td><b>Erwarteter Verkaufspreis</b></td><td>{result.estimated_sell_price:.2f}€</td></tr>
            <tr><td><b>Erwarteter Profit</b></td><td><b style="color:{color}">{result.expected_profit:.2f}€</b></td></tr>
            <tr><td><b>ROI</b></td><td>{result.expected_roi:.1f}%</td></tr>
            <tr><td><b>Demand-Score</b></td><td>{result.demand_score:.0f}/100</td></tr>
            <tr><td><b>Risiko</b></td><td>{result.risk_level}</td></tr>
            <tr><td><b>Sellout-Wahrscheinlichkeit</b></td><td>{result.sellout_probability*100:.0f}%</td></tr>
        </table>
        <p style="color:#666; font-size:12px;">Generiert von Ticket-Scanner</p>
        </body></html>
        """
