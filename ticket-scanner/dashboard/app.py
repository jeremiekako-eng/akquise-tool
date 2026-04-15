"""Rich CLI-Dashboard: Interaktive Oberfläche für den Ticket-Scanner."""
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich import box

from database.db import get_db
from database.models import Event, Alert
from portfolio.tracker import PortfolioTracker
from alerts.notifier import Notifier

# Immer UTF-8 mit ausreichender Breite (Windows-kompatibel)
console = Console(force_terminal=True, highlight=False, width=200)
tracker = PortfolioTracker()
notifier = Notifier()


# ── Farb-Mapping ────────────────────────────────────────────
DECISION_STYLE = {
    "BUY":   "bold green",
    "MAYBE": "bold yellow",
    "NO":    "dim red",
}
RISK_STYLE = {
    "LOW":    "green",
    "MEDIUM": "yellow",
    "HIGH":   "red",
}


def print_header():
    console.print(Panel.fit(
        "[bold cyan]TICKET RESALE SCANNER[/bold cyan]  |  "
        f"[dim]{datetime.now().strftime('%d.%m.%Y %H:%M')}[/dim]",
        border_style="cyan",
    ))


def show_events(
    decisions: list[str] | None = None,
    city: str | None = None,
    limit: int = 50,
):
    """Events-Tabelle mit Analyse-Ergebnissen."""
    with get_db() as db:
        query = db.query(Event).filter(Event.primary_price_min > 0)
        if decisions:
            query = query.filter(Event.decision.in_(decisions))
        if city:
            query = query.filter(Event.city.ilike(f"%{city}%"))
        rows = query.order_by(Event.expected_roi.desc()).limit(limit).all()
        # Alle Felder innerhalb der Session auslesen
        events = [
            {
                "id": e.id, "name": e.name, "event_date": e.event_date,
                "city": e.city, "primary_price_min": e.primary_price_min,
                "resale_price_avg": e.resale_price_avg, "expected_profit": e.expected_profit,
                "expected_roi": e.expected_roi, "demand_score": e.demand_score,
                "risk_score": e.risk_score, "decision": e.decision,
            }
            for e in rows
        ]

    if not events:
        console.print("[dim]Keine Events gefunden. Scanner starten: python main.py scan[/dim]")
        return

    table = Table(
        title=f"Events ({len(events)} gefunden)",
        box=box.ROUNDED,
        show_lines=True,
        header_style="bold cyan",
    )
    table.add_column("ID", style="dim", width=4, no_wrap=True)
    table.add_column("Event", min_width=25, max_width=40, no_wrap=True)
    table.add_column("Datum", width=10, no_wrap=True)
    table.add_column("Stadt", width=12, no_wrap=True)
    table.add_column("Kauf", justify="right", width=8, no_wrap=True)
    table.add_column("Resale-Avg", justify="right", width=11, no_wrap=True)
    table.add_column("Profit", justify="right", width=10, no_wrap=True)
    table.add_column("ROI", justify="right", width=7, no_wrap=True)
    table.add_column("Demand", justify="right", width=7, no_wrap=True)
    table.add_column("Risiko", width=7, no_wrap=True)
    table.add_column("Signal", width=7, no_wrap=True)

    for e in events:
        decision_style = DECISION_STYLE.get(e["decision"] or "NO", "dim")
        risk_score = e["risk_score"] or 0
        risk_label = "HIGH" if risk_score >= 60 else "MED" if risk_score >= 30 else "LOW"
        risk_style = RISK_STYLE.get(
            "HIGH" if risk_score >= 60 else "MEDIUM" if risk_score >= 30 else "LOW", "dim"
        )
        date_str = e["event_date"].strftime("%d.%m.%Y") if e["event_date"] else "?"

        profit = e["expected_profit"] or 0
        table.add_row(
            str(e["id"]),
            Text((e["name"] or "")[:40], overflow="ellipsis"),
            date_str,
            e["city"] or "?",
            f"{e['primary_price_min']:.0f} EUR" if e["primary_price_min"] else "?",
            f"{e['resale_price_avg']:.0f} EUR" if e["resale_price_avg"] else "?",
            Text(f"{profit:+.2f} EUR", style="green" if profit > 0 else "red"),
            Text(f"{e['expected_roi']:.1f}%", style=decision_style),
            f"{e['demand_score']:.0f}" if e["demand_score"] else "?",
            Text(risk_label, style=risk_style),
            Text(e["decision"] or "?", style=decision_style),
        )

    console.print(table)


def show_event_detail(event_id: int):
    """Detail-Ansicht eines einzelnen Events."""
    with get_db() as db:
        event = db.get(Event, event_id)
        if not event:
            console.print(f"[red]Event {event_id} nicht gefunden.[/red]")
            return

        risk_label = (
            "HIGH" if (event.risk_score or 0) >= 60
            else "MEDIUM" if (event.risk_score or 0) >= 30
            else "LOW"
        )
        decision_style = DECISION_STYLE.get(event.decision or "NO", "dim")

        console.print(Panel(
            f"[bold]{event.name}[/bold]\n"
            f"[dim]{event.artist or ''}  |  {event.venue}, {event.city}  |  "
            f"{event.event_date.strftime('%d.%m.%Y %H:%M') if event.event_date else '?'}[/dim]",
            title=f"[{decision_style}]{event.decision or '?'}[/{decision_style}]",
            border_style="cyan",
        ))

        # Preise
        price_table = Table(box=box.SIMPLE, show_header=False)
        price_table.add_column("", style="bold", width=30)
        price_table.add_column("", justify="right")
        price_table.add_row("Primärpreis (min)", f"{event.primary_price_min:.2f}€" if event.primary_price_min else "?")
        price_table.add_row("Primärpreis (max)", f"{event.primary_price_max:.2f}€" if event.primary_price_max else "?")
        price_table.add_row("Resale Min", f"{event.resale_price_min:.2f}€" if event.resale_price_min else "?")
        price_table.add_row("Resale Avg", f"{event.resale_price_avg:.2f}€" if event.resale_price_avg else "?")
        price_table.add_row("Resale Max", f"{event.resale_price_max:.2f}€" if event.resale_price_max else "?")
        price_table.add_row("Aktive Listings", str(event.resale_listings_count or 0))
        console.print(Panel(price_table, title="Preise", border_style="blue"))

        # Analyse
        analysis_table = Table(box=box.SIMPLE, show_header=False)
        analysis_table.add_column("", style="bold", width=30)
        analysis_table.add_column("", justify="right")
        analysis_table.add_row("Demand-Score", f"{event.demand_score:.1f}/100")
        analysis_table.add_row("Risk-Score", f"{event.risk_score:.1f}/100")
        analysis_table.add_row("Risiko-Level", Text(risk_label, style=RISK_STYLE.get(risk_label, "dim")))
        analysis_table.add_row("Sellout-Wahrsch.", f"{(event.sellout_probability or 0)*100:.0f}%")
        analysis_table.add_row("Erwarteter Profit", f"[bold green]{event.expected_profit:.2f}€[/bold green]")
        analysis_table.add_row("ROI", f"{event.expected_roi:.1f}%")
        analysis_table.add_row("Personalisiert", "[red]JA[/red]" if event.is_personalized else "[green]NEIN[/green]")
        console.print(Panel(analysis_table, title="Analyse", border_style="blue"))

        if event.decision_reason:
            console.print(Panel(event.decision_reason, title="Begründung", border_style="yellow"))

        console.print(f"\n[dim]Quelle: {event.source}  |  Zuletzt aktualisiert: {event.last_updated.strftime('%d.%m.%Y %H:%M') if event.last_updated else '?'}[/dim]")


def show_portfolio():
    """Portfolio-Übersicht und P&L."""
    summary = tracker.get_summary()
    portfolio = tracker.get_portfolio()

    # Summary Panel
    s = summary
    console.print(Panel(
        f"Im Bestand: [bold]{s['total_tickets_holding']} Tickets[/bold]  |  "
        f"Investiert: [bold]{s['total_invested_holding']:.2f}€[/bold]  |  "
        f"Unrealisiert: [bold cyan]{s['unrealized_profit_estimate']:+.2f}€[/bold cyan]\n"
        f"Verkauft: [bold]{s['total_tickets_sold']} Tickets[/bold]  |  "
        f"Realisierter Profit: [bold green]{s['total_realized_profit']:+.2f}€[/bold green]  |  "
        f"ROI: [bold]{s['total_realized_roi']:.1f}%[/bold]",
        title="Portfolio-Übersicht",
        border_style="green",
    ))

    if not portfolio:
        console.print("[dim]Noch keine Tickets im Portfolio. Nutze: python main.py portfolio add[/dim]")
        return

    table = Table(box=box.ROUNDED, header_style="bold green")
    table.add_column("ID", width=4)
    table.add_column("Event", max_width=30)
    table.add_column("Datum", width=11)
    table.add_column("Menge", justify="right", width=6)
    table.add_column("Kaufpreis", justify="right", width=10)
    table.add_column("Investiert", justify="right", width=10)
    table.add_column("Verkaufspreis", justify="right", width=13)
    table.add_column("Profit", justify="right", width=10)
    table.add_column("Status", width=10)

    for p in portfolio:
        profit_str = f"{p['actual_profit']:+.2f}€" if p["actual_profit"] is not None else "-"
        profit_style = "green" if (p["actual_profit"] or 0) > 0 else "red" if p["actual_profit"] is not None else "dim"
        status_style = {"holding": "yellow", "sold": "green", "listed": "cyan"}.get(p["status"], "dim")

        table.add_row(
            str(p["id"]),
            Text(p["event"][:30], overflow="ellipsis"),
            p["event_date"],
            str(p["quantity"]),
            f"{p['buy_price']:.2f}€",
            f"{p['total_invested']:.2f}€",
            f"{p['sell_price']:.2f}€" if p["sell_price"] else "-",
            Text(profit_str, style=profit_style),
            Text(p["status"].upper(), style=status_style),
        )

    console.print(table)


def show_alerts():
    """Ungelesene Alerts anzeigen."""
    alerts = notifier.get_unread_alerts()

    if not alerts:
        console.print("[dim]Keine neuen Alerts.[/dim]")
        return

    console.print(Panel(f"[bold]{len(alerts)} neue Alerts[/bold]", border_style="yellow"))

    for a in alerts:
        decision_style = DECISION_STYLE.get(a["decision"], "dim")
        console.print(
            Panel(
                f"[bold]{a['event']}[/bold]  |  {a['city']}  |  {a['event_date']}\n"
                f"Profit: [bold green]{a['profit']:.2f}€[/bold green]  |  ROI: {a['roi']:.1f}%\n\n"
                f"{a['message']}",
                title=f"[{decision_style}]{a['decision']}[/{decision_style}]  {a['created_at']}",
                border_style="yellow",
            )
        )

    if Confirm.ask("Alle als gelesen markieren?"):
        notifier.mark_all_read()
        console.print("[green]Alle Alerts als gelesen markiert.[/green]")
