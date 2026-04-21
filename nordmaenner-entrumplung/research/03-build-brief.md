# Website Build Brief — Die Nordmänner
## Entrümpelung + Umzüge Kiel — Kombinierte Landingpage
**Datum:** April 2026

---

## Die 5 Kernfragen

### 1. Für wen ist diese Seite?

**Besucher Typ A — Entrümpelung:**
35–65 Jahre, unter Zeitdruck: Wohnungsübergabe, Todesfall, Umzug ins Pflegeheim, Hausverkauf.
Größte Angst: Überraschungskosten, No-Shows, Abzocke.
Entscheidet nach: Preis → Schnelligkeit → Vertrauen.

**Besucher Typ B — Umzug:**
25–50 Jahre, plant Umzug innerhalb Kiels oder von/nach Kiel.
Größte Angst: Schäden an Möbeln, zu teuer, zu stressig.
Entscheidet nach: Preis → Zuverlässigkeit → Sauberkeit/Professionalität.

**Besucher Typ C — Kombination (die Goldgrube):**
Zieht aus einer großen Wohnung aus, muss erst räumen DANN einziehen.
Sucht einen einzigen Anbieter für alles — findet aktuell niemanden in Kiel.

### 2. Eine Aktion — was soll der Besucher tun?

**Primär: Kostenloses Angebot anfordern** — Formular (Name, Tel, Service, Wohnungsgröße, Termin)

Sekundär: Direkt anrufen (für ältere Zielgruppe).

### 3. Einwände → Sections

| Einwand | Section |
|---|---|
| "Wird das teuer?" | Festpreis-Versprechen im Hero + Preistabellen |
| "Kommen die schnell?" | Reaktionszeit-Banner + Testimonials mit Zeitangaben |
| "Ist das seriös?" | Google-Bewertungen, Fotos, Kiel-Adresse |
| "Was genau machen die?" | Services-Grid mit Karten |
| "Wie läuft das ab?" | 3-Schritte-Prozess |
| "Kann ich alles aus einer Hand haben?" | Kombinations-Paket-Section |
| "Was kostet mein Umzug konkret?" | Preistabelle nach Wohnungsgröße |

### 4. Der Vibe

**Bold, lokal, schnell, zuverlässig.**

Die Nordmänner sind nicht die nette Agentur die Prozesse erklärt — sie sind die Typen die einfach erscheinen und es erledigen.

- Direkte Sprache: "Wir kommen. Wir räumen. Wir fahren."
- Männlich, handwerklich, Kiel-Identität
- Nicht verkäuferisch — einfach klar
- Bei Todesfall/Pflegeheim: ton switcht zu respektvoll, nicht der ganze Hero

**Design:** Dunkel, kräftig, Orange-Akzent — radikal anders als alle türkis-hellblauen Wettbewerber.

### 5. Bestehende Brand Assets

- Logo: Die Nordmänner (vorhanden)
- Fahrzeuge: LKWs mit Branding (für Fotos nutzen)
- Erfahrung: bestehende Kundenbewertungen aus Transportgeschäft übertragen
- Domain: Neue Unterseite oder eigene Domain, z.B. nordmaenner-kiel.de

---

## Design Direction

### Farbpalette
| Rolle | Hex |
|---|---|
| Primär Dark | `#1a1a1a` |
| Akzent | `#e8590c` |
| Hell | `#f5f4f0` |
| Trust-Grün | `#22c55e` |
| Muted | `#6b6860` |

**Warum Orange:** Alle Wettbewerber nutzen Teal/Blau. Orange signalisiert Energie und Schnelligkeit — differenziert visuell sofort.

### Typografie
- Headlines: **Oswald** oder **Bebas Neue** — breit, kraftvoll
- Body: **Inter** oder **DM Sans** — maximal lesbar
- Kein Serif

### Was vermeiden
- Teal/Türkis (= Rümpel Meister)
- Stock-Fotos mit lächelnden Arbeitern
- Zu viel Empathie-Sprache im Hero
- Mehr als einen primären CTA pro Section

---

## Seitenarchitektur

```
HERO
  └─ Headline + CTA + Rating-Badge
TRUST BANNER (Orange Streifen)
  └─ Noch heute · Festpreis · Kostenlose Besichtigung
SERVICES GRID
  └─ Entrümpelung (4 Karten) + Umzüge (3 Karten)
KOMBINATIONS-PAKET
  └─ "Erst räumen wir aus — dann ziehen wir ein."
3-SCHRITTE-PROZESS
PREISTABELLEN
  └─ Tab: Entrümpelung | Tab: Umzug
GOOGLE-BEWERTUNGEN
VORHER/NACHHER (Entrümpelung)
SONDERSITUATIONEN
  └─ Todesfall · Pflegeheim · Messie
ÜBER DIE NORDMÄNNER
FINAL CTA BLOCK
FAQ
FOOTER
```

### Navigation
Leistungen | Preise | Bewertungen | Kontakt

---

## Content Framework

### Hero Headlines

**Option A (Speed — empfohlen):**
> "Entrümpelung & Umzüge Kiel — Noch heute vor Ort."
> Subline: "Ein Anbieter für alles. Festpreis. Kostenlose Besichtigung."

**Option B (Kombination):**
> "Wir räumen aus. Wir ziehen ein."
> Subline: "Entrümpelung & Umzüge in Kiel — zum Festpreis, noch heute."

**Option C (Problem-lösung):**
> "Stress mit Entrümpelung oder Umzug? Wir sind in 2 Stunden da."
> Subline: "Lokales Kieler Team. Festpreis. Keine versteckten Kosten."

**Empfehlung:** Option A

### Kombinations-Paket-Section (einzigartiger Content)
**Headline:** "Erst räumen wir aus — dann ziehen wir ein."
**Copy:** Viele unserer Kunden brauchen beides: erst die alte Wohnung entrümpeln, dann in die neue umziehen. Kein zweiter Anbieter, keine doppelte Koordination — wir machen alles in einem Zug.
**CTA:** "Kombinationsangebot anfordern"

### Preistabelle Entrümpelung
| Größe | Preis |
|---|---|
| 1-Zi / ~40m² | ab 750 € |
| 2-Zi | ab 790 € |
| 3-Zi | ab 1.190 € |
| 4-Zi | ab 1.590 € |
*Brauchbare Gegenstände werden angerechnet und senken deinen Preis.*

### Preistabelle Umzüge
| Größe | Preis |
|---|---|
| ~30m² / 1-Zi | ab 350 € |
| ~60m² / 2-Zi | ab 700 € |
| ~80m² / 3-Zi | ab 800 € |
| 100m²+ | ab 1.000 € |
*Inklusive Be- und Entladen, Transport, Versicherung.*

### SEO-Keywords On-Page
**Primär:** Entrümpelung Kiel, Umzugsunternehmen Kiel, Haushaltsauflösung Kiel
**Sekundär:** Umzug Kiel Festpreis, Kellerräumung Kiel, Möbeltransport Kiel
**Kombination (frei!):** Entrümpelung und Umzug Kiel, Umzug mit Entrümpelung Kiel
**Speed (frei!):** Entrümpelung Kiel sofort, Umzug Kiel gleicher Tag

---

## Conversion Playbook

### Formular (max. 4 Felder)
1. Name
2. Telefonnummer
3. Service (Dropdown: Entrümpelung / Umzug / Beides)
4. Wohnungsgröße + Wunschtermin

### Trust Checkliste
- [ ] Google Rating im Hero (min. 4.7+)
- [ ] Echte Team-Fotos (keine Stock-Fotos)
- [ ] Kieler Adresse sichtbar
- [ ] Versicherung erwähnen (Umzugsgut-Schutz)
- [ ] "Kein Subunternehmer" explizit
- [ ] Betriebshaftpflicht nennen
- [ ] Impressum korrekt

### Lead Capture Extras
- Sticky Telefonnummer auf Mobile (immer sichtbar)
- Zweiter CTA nach Preistabelle
- FAQ-Antworten enden mit "Jetzt anfragen"

---

## Positionierungsaussage

Die Nordmänner sind **das einzige lokale Kieler Unternehmen das Entrümpelung und Umzug aus einer Hand** anbietet — schnell, mit Festpreis, ohne Subunternehmer. Wer beides braucht, ruft einmal an.
