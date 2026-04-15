#!/usr/bin/env python3
"""
Ticket Resale Scanner — Haupteinstiegspunkt.

Verwendung:
    python main.py scan              # Einmal scannen
    python main.py scan --watch      # Dauerhaft scannen (Intervall aus .env)
    python main.py events            # Alle Events anzeigen
    python main.py events --buy      # Nur BUY-Deals
    python main.py events --city Berlin
    python main.py event <ID>        # Event-Detail
    python main.py alerts            # Ungelesene Alerts
    python main.py portfolio         # Portfolio-Übersicht
    python main.py portfolio add     # Ticket ins Portfolio aufnehmen
    python main.py portfolio sold    # Ticket als verkauft markieren
    python main.py artist "Taylor Swift"   # Künstler-Suche
"""
import sys
import io
import time
import schedule

# Windows: UTF-8 erzwingen damit Umlaute und Sonderzeichen korrekt angezeigt werden
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from datetime import datetime
from rich.console import Console
from rich.prompt import Prompt, IntPrompt, FloatPrompt

from config import cfg
from database.db import init_db, get_db
from database.models import Event, PriceHistory
from scanners.ticketmaster import TicketmasterScanner
from scanners.seatgeek import SeatGeekScanner
from analyzers.decision_engine import DecisionEngine
from alerts.notifier import Notifier
from portfolio.tracker import PortfolioTracker
from dashboard.app import (
    print_header,
    show_events,
    show_event_detail,
    show_portfolio,
    show_alerts,
    console,
)

decision_engine = DecisionEngine()
notifier = Notifier()
tracker = PortfolioTracker()


# ── Scanner-Pipeline ────────────────────────────────────────

def run_scan(verbose: bool = True) -> int:
    """Hauptscan: Events holen, analysieren, speichern."""
    if verbose:
        print_header()
        console.print("[cyan]Starte Scan...[/cyan]")

    scanners = []
    if cfg.TICKETMASTER_API_KEY:
        scanners.append(TicketmasterScanner())
    if cfg.SEATGEEK_CLIENT_ID:
        scanners.append(SeatGeekScanner())

    if not scanners:
        console.print(
            "[yellow]Kein API-Key konfiguriert![/yellow]\n"
            "Bitte .env anlegen und TICKETMASTER_API_KEY oder SEATGEEK_CLIENT_ID setzen.\n"
            "Kopiere .env.example -> .env und füge deine Keys ein."
        )
        # Demo mit Beispiel-Daten
        _run_demo()
        return 0

    all_events = []
    for scanner in scanners:
        name = scanner.name
        if verbose:
            console.print(f"  Scanne [bold]{name}[/bold]...")
        events = scanner.fetch_events()
        if verbose:
            console.print(f"  -> {len(events)} Events gefunden")
        all_events.extend(events)

    if not all_events:
        if verbose:
            console.print("[yellow]Keine Events gefunden.[/yellow]")
        return 0

    # Deduplizieren
    seen = set()
    unique_events = []
    for e in all_events:
        if e.external_id not in seen:
            seen.add(e.external_id)
            unique_events.append(e)

    if verbose:
        console.print(f"[cyan]Analysiere {len(unique_events)} Events...[/cyan]")

    saved = 0
    buy_count = 0
    maybe_count = 0

    with get_db() as db:
        for raw in unique_events:
            # Existierendes Event aus DB laden oder neues erstellen
            event = db.query(Event).filter(
                Event.external_id == raw.external_id
            ).first()

            is_new = event is None
            if is_new:
                event = Event(external_id=raw.external_id, source=raw.source)
                db.add(event)

            # Felder aktualisieren
            event.name = raw.name
            event.artist = raw.artist
            event.category = raw.category
            event.subcategory = raw.subcategory
            event.venue = raw.venue
            event.city = raw.city
            event.country = raw.country
            event.event_date = raw.event_date
            event.on_sale_date = raw.on_sale_date
            event.primary_price_min = raw.primary_price_min
            event.primary_price_max = raw.primary_price_max
            event.primary_currency = raw.primary_currency
            event.primary_url = raw.primary_url
            event.tickets_available = raw.tickets_available
            event.capacity = raw.capacity
            event.is_personalized = raw.is_personalized

            # Resale-Daten übernehmen (falls vorhanden)
            if raw.resale_price_avg:
                event.resale_price_min = raw.resale_price_min
                event.resale_price_avg = raw.resale_price_avg
                event.resale_price_max = raw.resale_price_max
                event.resale_listings_count = raw.resale_listings_count

            # Preishistorie speichern
            history = PriceHistory(
                event_id=0,   # wird nach flush gesetzt
                primary_price_min=raw.primary_price_min,
                primary_price_max=raw.primary_price_max,
                resale_price_min=raw.resale_price_min,
                resale_price_avg=raw.resale_price_avg,
                resale_price_max=raw.resale_price_max,
                resale_listings_count=raw.resale_listings_count,
            )

            db.flush()   # ID generieren

            # Analyse durchführen
            result = decision_engine.analyze(event)

            event.demand_score = result.demand_score
            event.risk_score = result.risk_score
            event.sellout_probability = result.sellout_probability
            event.expected_profit = result.expected_profit
            event.expected_roi = result.expected_roi
            event.decision = result.decision
            event.decision_reason = result.recommendation_text
            event.last_updated = datetime.utcnow()

            history.event_id = event.id
            history.demand_score = result.demand_score
            db.add(history)

            # Alert generieren
            if is_new and result.decision in ("BUY", "MAYBE"):
                notifier.create_alert(event, result, "new_deal")

            saved += 1
            if result.decision == "BUY":
                buy_count += 1
            elif result.decision == "MAYBE":
                maybe_count += 1

    if verbose:
        console.print(
            f"\n[bold]Scan abgeschlossen:[/bold] {saved} Events  |  "
            f"[bold green]{buy_count} BUY[/bold green]  |  "
            f"[bold yellow]{maybe_count} MAYBE[/bold yellow]"
        )
        if buy_count > 0 or maybe_count > 0:
            console.print("\n[bold cyan]Top Deals:[/bold cyan]")
            show_events(decisions=["BUY", "MAYBE"], limit=10)

    return saved


def _run_demo():
    """Demo-Modus mit synthetischen Daten (ohne API-Keys)."""
    console.print("\n[bold yellow]DEMO-MODUS[/bold yellow] — Keine echten API-Keys gesetzt.\n")

    from database.db import get_db
    demo_events = [
        {
            "external_id": "demo_001", "source": "demo", "name": "Taylor Swift – Eras Tour",
            "artist": "Taylor Swift", "category": "Music", "venue": "Olympiastadion",
            "city": "Berlin", "country": "DE",
            "event_date": datetime(2025, 7, 23, 20, 0),
            "primary_price_min": 80.0, "primary_price_max": 350.0,
            "resale_price_min": 250.0, "resale_price_avg": 420.0, "resale_price_max": 900.0,
            "resale_listings_count": 1240, "capacity": 74000, "is_personalized": True,
        },
        {
            "external_id": "demo_002", "source": "demo", "name": "Coldplay – Music Of The Spheres",
            "artist": "Coldplay", "category": "Music", "venue": "Volksparkstadion",
            "city": "Hamburg", "country": "DE",
            "event_date": datetime(2025, 6, 14, 20, 0),
            "primary_price_min": 65.0, "primary_price_max": 180.0,
            "resale_price_min": 140.0, "resale_price_avg": 220.0, "resale_price_max": 500.0,
            "resale_listings_count": 380, "capacity": 57000, "is_personalized": False,
        },
        {
            "external_id": "demo_003", "source": "demo", "name": "Rammstein – Europe Stadium Tour",
            "artist": "Rammstein", "category": "Music", "venue": "Red Bull Arena",
            "city": "München", "country": "DE",
            "event_date": datetime(2025, 8, 5, 20, 0),
            "primary_price_min": 95.0, "primary_price_max": 220.0,
            "resale_price_min": 180.0, "resale_price_avg": 280.0, "resale_price_max": 600.0,
            "resale_listings_count": 210, "capacity": 68000, "is_personalized": False,
        },
        {
            "external_id": "demo_004", "source": "demo", "name": "Local Band – Kleine Club Show",
            "artist": "Unbekannte Band", "category": "Music", "venue": "Musik Club XY",
            "city": "Köln", "country": "DE",
            "event_date": datetime(2025, 5, 30, 20, 0),
            "primary_price_min": 15.0, "primary_price_max": 25.0,
            "resale_price_min": 12.0, "resale_price_avg": 14.0, "resale_price_max": 20.0,
            "resale_listings_count": 3, "capacity": 500, "is_personalized": False,
        },
        {
            "external_id": "demo_005", "source": "demo", "name": "Champions League Finale",
            "artist": "", "category": "Sports", "venue": "Allianz Arena",
            "city": "München", "country": "DE",
            "event_date": datetime(2025, 5, 31, 21, 0),
            "primary_price_min": 70.0, "primary_price_max": 500.0,
            "resale_price_min": 350.0, "resale_price_avg": 650.0, "resale_price_max": 2000.0,
            "resale_listings_count": 890, "capacity": 75000, "is_personalized": False,
        },
    ]

    with get_db() as db:
        for data in demo_events:
            event = db.query(Event).filter(Event.external_id == data["external_id"]).first()
            if not event:
                event = Event(**{k: v for k, v in data.items()})
                db.add(event)
                db.flush()
            result = decision_engine.analyze(event)
            event.demand_score = result.demand_score
            event.risk_score = result.risk_score
            event.sellout_probability = result.sellout_probability
            event.expected_profit = result.expected_profit
            event.expected_roi = result.expected_roi
            event.decision = result.decision
            event.decision_reason = result.recommendation_text

    console.print("[green]Demo-Events gespeichert und analysiert.[/green]")
    show_events(limit=20)


# ── CLI-Commands ────────────────────────────────────────────

def cmd_scan(watch: bool = False):
    run_scan()
    if watch:
        console.print(f"\n[dim]Auto-Scan alle {cfg.SCAN_INTERVAL_MINUTES} Minuten. Ctrl+C zum Beenden.[/dim]")
        schedule.every(cfg.SCAN_INTERVAL_MINUTES).minutes.do(lambda: run_scan(verbose=False))
        try:
            while True:
                schedule.run_pending()
                time.sleep(30)
        except KeyboardInterrupt:
            console.print("\n[dim]Scanner beendet.[/dim]")


def cmd_events(args: list[str]):
    print_header()
    decisions = None
    city = None
    if "--buy" in args:
        decisions = ["BUY"]
    elif "--maybe" in args:
        decisions = ["MAYBE"]
    elif "--buy-maybe" in args:
        decisions = ["BUY", "MAYBE"]
    for i, a in enumerate(args):
        if a == "--city" and i + 1 < len(args):
            city = args[i + 1]
    show_events(decisions=decisions, city=city)


def cmd_event_detail(event_id: int):
    print_header()
    show_event_detail(event_id)


def cmd_alerts():
    print_header()
    show_alerts()


def cmd_portfolio(args: list[str]):
    print_header()

    if "add" in args:
        # Ticket hinzufügen
        with get_db() as db:
            event_id = IntPrompt.ask("Event-ID")
            event = db.get(Event, event_id)
            if not event:
                console.print("[red]Event nicht gefunden.[/red]")
                return
            console.print(f"Event: [bold]{event.name}[/bold]")

        buy_price = FloatPrompt.ask("Kaufpreis (€)")
        quantity = IntPrompt.ask("Anzahl Tickets", default=1)
        platform = Prompt.ask("Plattform", default="ticketmaster")
        seat = Prompt.ask("Kategorie/Sitzplatz", default="")
        notes = Prompt.ask("Notizen", default="")

        entry = tracker.add_ticket(
            event_id=event_id,
            buy_price=buy_price,
            quantity=quantity,
            seat_category=seat,
            platform_bought=platform,
            notes=notes,
        )
        console.print(f"[green]Ticket #{entry.id} zum Portfolio hinzugefügt.[/green]")

    elif "sold" in args:
        # Als verkauft markieren
        show_portfolio()
        entry_id = IntPrompt.ask("\nPortfolio-ID (verkauft)")
        sell_price = FloatPrompt.ask("Verkaufspreis pro Ticket (€)")
        platform = Prompt.ask("Plattform", default="stubhub")
        fee = FloatPrompt.ask("Plattform-Gebühr gesamt (€, leer lassen für auto)", default=-1.0)

        entry = tracker.mark_sold(
            entry_id=entry_id,
            sell_price=sell_price,
            platform_sold=platform,
            platform_fee=None if fee < 0 else fee,
        )
        if entry:
            profit = entry.actual_profit or 0
            style = "green" if profit > 0 else "red"
            console.print(f"[{style}]Profit: {profit:+.2f}€[/{style}]")
        else:
            console.print("[red]Portfolio-Eintrag nicht gefunden.[/red]")

    else:
        show_portfolio()


def cmd_artist(name: str):
    """Gezielt nach einem Künstler suchen."""
    print_header()
    console.print(f"[cyan]Suche nach: [bold]{name}[/bold][/cyan]")
    events = []

    if cfg.TICKETMASTER_API_KEY:
        tm = TicketmasterScanner()
        events.extend(tm.search_artist(name))

    if cfg.SEATGEEK_CLIENT_ID:
        sg = SeatGeekScanner()
        events.extend(sg.search_by_artist(name))

    if not events:
        console.print("[yellow]Keine Events gefunden oder kein API-Key gesetzt.[/yellow]")
        return

    with get_db() as db:
        for raw in events:
            event = db.query(Event).filter(Event.external_id == raw.external_id).first()
            if not event:
                event = Event(external_id=raw.external_id, source=raw.source)
                db.add(event)
                event.name = raw.name
                event.artist = raw.artist
                event.city = raw.city
                event.venue = raw.venue
                event.event_date = raw.event_date
                event.primary_price_min = raw.primary_price_min
                event.resale_price_avg = raw.resale_price_avg
                event.resale_listings_count = raw.resale_listings_count
                db.flush()
                result = decision_engine.analyze(event)
                event.demand_score = result.demand_score
                event.risk_score = result.risk_score
                event.expected_profit = result.expected_profit
                event.expected_roi = result.expected_roi
                event.decision = result.decision
                event.decision_reason = result.recommendation_text

    show_events(limit=30)


def print_help():
    console.print(Panel(
        "[bold]Ticket Resale Scanner[/bold]\n\n"
        "[cyan]python main.py scan[/cyan]              -> Einmal scannen\n"
        "[cyan]python main.py scan --watch[/cyan]      -> Dauerhaft scannen\n"
        "[cyan]python main.py events[/cyan]            -> Alle Events\n"
        "[cyan]python main.py events --buy[/cyan]      -> Nur BUY-Deals\n"
        "[cyan]python main.py events --maybe[/cyan]    -> Nur MAYBE-Deals\n"
        "[cyan]python main.py events --buy-maybe[/cyan]-> BUY + MAYBE\n"
        "[cyan]python main.py events --city Berlin[/cyan]\n"
        "[cyan]python main.py event 42[/cyan]          -> Event-Detail (ID)\n"
        "[cyan]python main.py alerts[/cyan]            -> Neue Alerts\n"
        "[cyan]python main.py portfolio[/cyan]         -> Portfolio & P&L\n"
        "[cyan]python main.py portfolio add[/cyan]     -> Ticket kaufen\n"
        "[cyan]python main.py portfolio sold[/cyan]    -> Ticket als verkauft\n"
        '[cyan]python main.py artist "Coldplay"[/cyan] -> Künstler suchen',
        title="Hilfe",
        border_style="cyan",
    ))


# ── Einstiegspunkt ──────────────────────────────────────────

def main():
    init_db()
    args = sys.argv[1:]

    if not args or args[0] in ("help", "--help", "-h"):
        print_help()
        return

    cmd = args[0]

    if cmd == "scan":
        cmd_scan(watch="--watch" in args)
    elif cmd == "events":
        cmd_events(args[1:])
    elif cmd == "event" and len(args) > 1:
        try:
            cmd_event_detail(int(args[1]))
        except ValueError:
            console.print("[red]Bitte eine numerische Event-ID angeben.[/red]")
    elif cmd == "alerts":
        cmd_alerts()
    elif cmd == "portfolio":
        cmd_portfolio(args[1:])
    elif cmd == "artist" and len(args) > 1:
        cmd_artist(args[1])
    else:
        console.print(f"[red]Unbekannter Befehl: {cmd}[/red]")
        print_help()


if __name__ == "__main__":
    main()
