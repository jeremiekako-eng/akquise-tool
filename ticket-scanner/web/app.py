"""Flask Web-Dashboard für den Ticket Resale Scanner."""
import sys
import os

# Pfad zu ticket-scanner/ (eine Ebene über web/) ins sys.path einfügen
_here = os.path.dirname(os.path.abspath(__file__))
_ticket_scanner_dir = os.path.dirname(_here)
if _ticket_scanner_dir not in sys.path:
    sys.path.insert(0, _ticket_scanner_dir)
# Fallback: PYTHONPATH=/app/ticket-scanner (Railway env var)
_env_path = os.environ.get("PYTHONPATH", "")
if _env_path and _env_path not in sys.path:
    sys.path.insert(0, _env_path)

from flask import Flask, render_template, jsonify, request
from datetime import datetime
from database.db import init_db, get_db
from database.models import Event, Alert, PortfolioEntry
from analyzers.decision_engine import DecisionEngine
from alerts.notifier import Notifier
from portfolio.tracker import PortfolioTracker

app = Flask(__name__)

# DB beim Import initialisieren (auch unter gunicorn)
from database.db import init_db as _init_db
_init_db()

decision_engine = DecisionEngine()
notifier = Notifier()
tracker = PortfolioTracker()


# ── Seiten ──────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── API-Endpunkte ───────────────────────────────────────────

@app.route("/api/events")
def api_events():
    decision = request.args.get("decision")
    city = request.args.get("city", "").strip()
    search = request.args.get("search", "").strip()
    limit = int(request.args.get("limit", 100))

    with get_db() as db:
        query = db.query(Event)
        if decision and decision != "ALL":
            query = query.filter(Event.decision == decision)
        if city:
            query = query.filter(Event.city.ilike(f"%{city}%"))
        if search:
            query = query.filter(Event.name.ilike(f"%{search}%"))
        rows = query.order_by(Event.expected_roi.desc()).limit(limit).all()

        events = []
        for e in rows:
            d = _event_to_dict(e)
            d["decision_reason"] = e.decision_reason or ""
            events.append(d)

    return jsonify(events)


@app.route("/api/events/<int:event_id>")
def api_event_detail(event_id):
    with get_db() as db:
        event = db.get(Event, event_id)
        if not event:
            return jsonify({"error": "Not found"}), 404
        data = _event_to_dict(event)
        data["decision_reason"] = event.decision_reason or ""
        data["primary_url"] = event.primary_url or ""
        data["is_personalized"] = event.is_personalized
        data["source"] = event.source
        data["last_updated"] = event.last_updated.strftime("%d.%m.%Y %H:%M") if event.last_updated else "?"

        # Risikofaktoren live berechnen und mit Beschreibungen zurückgeben
        from analyzers.risk_analyzer import RiskAnalyzer
        from analyzers.demand_analyzer import DemandAnalyzer
        _, risk_factors = RiskAnalyzer().analyze(event)
        data["risk_factors"] = [
            {"name": f.name, "score": f.score, "description": f.description}
            for f in risk_factors
        ]

        # Demand-Teilscores für Transparenz
        da = DemandAnalyzer()
        data["demand_breakdown"] = {
            "artist":    round(da._artist_score(event.artist or event.name), 1),
            "venue":     round(da._venue_score(event.capacity or 0, event.tickets_available), 1),
            "resale":    round(da._resale_activity_score(
                             event.resale_listings_count or 0,
                             event.resale_price_min or 0,
                             event.primary_price_min or 0), 1),
            "time":      round(da._time_pressure_score(event.event_date), 1),
            "premium":   round(da._price_premium_score(
                             event.resale_price_avg or 0,
                             event.primary_price_min or 0), 1),
        }

    return jsonify(data)


@app.route("/api/scan", methods=["POST"])
def api_scan():
    """Scan ausloesen (läuft im gleichen Prozess, Demo-Modus wenn kein Key)."""
    try:
        from config import cfg
        from scanners.seatgeek import SeatGeekScanner
        from scanners.ticketmaster import TicketmasterScanner
        from database.models import PriceHistory

        scanners = []
        if cfg.TICKETMASTER_API_KEY:
            scanners.append(TicketmasterScanner())
        if cfg.SEATGEEK_CLIENT_ID:
            scanners.append(SeatGeekScanner())

        if not scanners:
            _load_demo_events()
            return jsonify({"status": "demo", "message": "Demo-Modus: Kein API-Key gesetzt.", "count": 5})

        all_events = []
        for scanner in scanners:
            all_events.extend(scanner.fetch_events())

        seen = set()
        unique = [e for e in all_events if not (e.external_id in seen or seen.add(e.external_id))]

        saved = buy = maybe = 0
        with get_db() as db:
            for raw in unique:
                event = db.query(Event).filter(Event.external_id == raw.external_id).first()
                is_new = event is None
                if is_new:
                    event = Event(external_id=raw.external_id, source=raw.source)
                    db.add(event)

                for field in ["name","artist","category","subcategory","venue","city","country",
                              "event_date","on_sale_date","primary_price_min","primary_price_max",
                              "primary_currency","primary_url","tickets_available","capacity","is_personalized"]:
                    setattr(event, field, getattr(raw, field))

                if raw.resale_price_avg:
                    event.resale_price_min = raw.resale_price_min
                    event.resale_price_avg = raw.resale_price_avg
                    event.resale_price_max = raw.resale_price_max
                    event.resale_listings_count = raw.resale_listings_count

                db.flush()
                result = decision_engine.analyze(event)
                event.demand_score = result.demand_score
                event.risk_score = result.risk_score
                event.sellout_probability = result.sellout_probability
                event.expected_profit = result.expected_profit
                event.expected_roi = result.expected_roi
                event.decision = result.decision
                event.decision_reason = result.recommendation_text
                event.last_updated = datetime.utcnow()

                if is_new and result.decision in ("BUY", "MAYBE"):
                    notifier.create_alert(event, result, "new_deal")

                saved += 1
                if result.decision == "BUY": buy += 1
                elif result.decision == "MAYBE": maybe += 1

        return jsonify({"status": "ok", "count": saved, "buy": buy, "maybe": maybe})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/alerts")
def api_alerts():
    alerts = notifier.get_unread_alerts()
    return jsonify(alerts)


@app.route("/api/alerts/read", methods=["POST"])
def api_alerts_read():
    notifier.mark_all_read()
    return jsonify({"status": "ok"})


@app.route("/api/portfolio")
def api_portfolio():
    portfolio = tracker.get_portfolio()
    summary = tracker.get_summary()
    return jsonify({"entries": portfolio, "summary": summary})


@app.route("/api/portfolio/add", methods=["POST"])
def api_portfolio_add():
    data = request.json
    try:
        entry = tracker.add_ticket(
            event_id=int(data["event_id"]),
            buy_price=float(data["buy_price"]),
            quantity=int(data.get("quantity", 1)),
            seat_category=data.get("seat_category", ""),
            platform_bought=data.get("platform", ""),
            notes=data.get("notes", ""),
        )
        return jsonify({"status": "ok", "id": entry.id})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/portfolio/sell", methods=["POST"])
def api_portfolio_sell():
    data = request.json
    try:
        entry = tracker.mark_sold(
            entry_id=int(data["entry_id"]),
            sell_price=float(data["sell_price"]),
            platform_sold=data.get("platform", ""),
            platform_fee=float(data["fee"]) if data.get("fee") else None,
        )
        if not entry:
            return jsonify({"status": "error", "message": "Eintrag nicht gefunden"}), 404
        return jsonify({"status": "ok", "profit": entry.actual_profit})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/api/stats")
def api_stats():
    with get_db() as db:
        total = db.query(Event).count()
        buy = db.query(Event).filter(Event.decision == "BUY").count()
        maybe = db.query(Event).filter(Event.decision == "MAYBE").count()
        no = db.query(Event).filter(Event.decision == "NO").count()
        unread_alerts = db.query(Alert).filter(Alert.is_read == False).count()  # noqa
    summary = tracker.get_summary()
    return jsonify({
        "total_events": total, "buy": buy, "maybe": maybe, "no": no,
        "unread_alerts": unread_alerts,
        "portfolio": summary,
    })


# ── Hilfsfunktionen ─────────────────────────────────────────

def _event_to_dict(e: Event) -> dict:
    return {
        "id": e.id,
        "name": e.name,
        "artist": e.artist or "",
        "category": e.category or "",
        "venue": e.venue or "",
        "city": e.city or "",
        "country": e.country or "",
        "event_date": e.event_date.strftime("%d.%m.%Y") if e.event_date else "?",
        "event_date_iso": e.event_date.isoformat() if e.event_date else None,
        "primary_price_min": e.primary_price_min or 0,
        "primary_price_max": e.primary_price_max or 0,
        "resale_price_min": e.resale_price_min or 0,
        "resale_price_avg": e.resale_price_avg or 0,
        "resale_price_max": e.resale_price_max or 0,
        "resale_listings_count": e.resale_listings_count or 0,
        "demand_score": e.demand_score or 0,
        "risk_score": e.risk_score or 0,
        "sellout_probability": round((e.sellout_probability or 0) * 100),
        "expected_profit": e.expected_profit or 0,
        "expected_roi": e.expected_roi or 0,
        "decision": e.decision or "NO",
        "tickets_available": e.tickets_available,
    }


def _load_demo_events():
    demo = [
        {"external_id": "demo_001", "source": "demo", "name": "Taylor Swift - Eras Tour", "artist": "Taylor Swift", "category": "Music", "venue": "Olympiastadion", "city": "Berlin", "country": "DE", "event_date": datetime(2025, 7, 23, 20, 0), "primary_price_min": 80.0, "primary_price_max": 350.0, "resale_price_min": 250.0, "resale_price_avg": 420.0, "resale_price_max": 900.0, "resale_listings_count": 1240, "capacity": 74000, "is_personalized": True, "tickets_available": True},
        {"external_id": "demo_002", "source": "demo", "name": "Coldplay - Music Of The Spheres", "artist": "Coldplay", "category": "Music", "venue": "Volksparkstadion", "city": "Hamburg", "country": "DE", "event_date": datetime(2025, 6, 14, 20, 0), "primary_price_min": 65.0, "primary_price_max": 180.0, "resale_price_min": 140.0, "resale_price_avg": 220.0, "resale_price_max": 500.0, "resale_listings_count": 380, "capacity": 57000, "is_personalized": False, "tickets_available": True},
        {"external_id": "demo_003", "source": "demo", "name": "Rammstein - Europe Stadium Tour", "artist": "Rammstein", "category": "Music", "venue": "Red Bull Arena", "city": "München", "country": "DE", "event_date": datetime(2025, 8, 5, 20, 0), "primary_price_min": 95.0, "primary_price_max": 220.0, "resale_price_min": 180.0, "resale_price_avg": 280.0, "resale_price_max": 600.0, "resale_listings_count": 210, "capacity": 68000, "is_personalized": False, "tickets_available": True},
        {"external_id": "demo_004", "source": "demo", "name": "Local Band - Kleine Club Show", "artist": "Unbekannte Band", "category": "Music", "venue": "Musik Club XY", "city": "Köln", "country": "DE", "event_date": datetime(2025, 5, 30, 20, 0), "primary_price_min": 15.0, "primary_price_max": 25.0, "resale_price_min": 12.0, "resale_price_avg": 14.0, "resale_price_max": 20.0, "resale_listings_count": 3, "capacity": 500, "is_personalized": False, "tickets_available": True},
        {"external_id": "demo_005", "source": "demo", "name": "Champions League Finale", "artist": "", "category": "Sports", "venue": "Allianz Arena", "city": "München", "country": "DE", "event_date": datetime(2025, 5, 31, 21, 0), "primary_price_min": 70.0, "primary_price_max": 500.0, "resale_price_min": 350.0, "resale_price_avg": 650.0, "resale_price_max": 2000.0, "resale_listings_count": 890, "capacity": 75000, "is_personalized": False, "tickets_available": False},
    ]
    with get_db() as db:
        for data in demo:
            event = db.query(Event).filter(Event.external_id == data["external_id"]).first()
            if not event:
                event = Event(**data)
                db.add(event)
            else:
                for k, v in data.items():
                    setattr(event, k, v)
            db.flush()
            result = decision_engine.analyze(event)
            event.demand_score = result.demand_score
            event.risk_score = result.risk_score
            event.sellout_probability = result.sellout_probability
            event.expected_profit = result.expected_profit
            event.expected_roi = result.expected_roi
            event.decision = result.decision
            event.decision_reason = result.recommendation_text


if __name__ == "__main__":
    init_db()
    _load_demo_events()
    port = int(os.environ.get("PORT", 5000))
    print(f"Dashboard läuft auf http://localhost:{port}")
    app.run(debug=False, host="0.0.0.0", port=port)
