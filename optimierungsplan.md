Claude Code Auftrag: dienordmaenner.com für
Google Ads vorbereiten
Du arbeitest am Projekt Die Nordmänner (dienordmaenner.com) — eine lokale
Entrümpelungs- und Umzugsfirma in Kiel. Die Website soll für Google Ads scharf
gemacht werden. Wir gehen die Optimierungen in 5 Phasen durch. Arbeite eine Phase
nach der anderen ab und frage am Ende jeder Phase, ob du zur nächsten übergehen
sollst.
 Kontext für dich
Tech-Stack: Statische HTML-Seite, deployed auf Vercel
Domain: dienordmaenner.com (DNS bei Hostinger)
Hauptseite: index.html
Unterseiten: entruempelung-kiel.html, wohnungsaufloesung-kiel.html, kellerraum￾kiel.html, dachboden-kiel.html, privatumzug-kiel.html, impressum.html,
datenschutz.html
Ziel: Quality Score bei Google Ads maximieren, Conversion-Tracking einrichten,
DSGVO-Compliance sicherstellen
Wichtig: Vor jeder Änderung den aktuellen Zustand der Datei prüfen. Nach jeder Phase
einen Git-Commit mit aussagekräftiger Message erstellen. Nicht alle Änderungen auf
einmal pushen — wir testen Phase für Phase.
 PHASE 1: Conversion-Tracking & Analytics (KRITISCH)
Ziel: Ohne Tracking ist jeder Euro für Google Ads verbrannt. Das machen wir zuerst.
Aufgaben:
1. Google Tag Manager (GTM) einbinden
Frage mich nach meiner GTM-Container-ID (Format: GTM-XXXXXXX )
Falls ich noch keinen GTM-Account habe: Anleitung geben, wie ich einen erstelle
(tagmanager.google.com)
GTM-Snippet im <head> und direkt nach <body> aller HTML-Dateien einbauen
(auch Unterseiten!)
2. Conversion-Events definieren (als JavaScript-Trigger, der dataLayer.push
ausführt):
formular_gesendet — beim Submit des Hauptformulars und des Modal￾Formulars
whatsapp_klick — bei jedem Klick auf einen wa.me-Link
telefon_klick — bei jedem Klick auf einen tel:-Link
preisrechner_abgeschlossen — wenn der Preis-Wizard Schritt 4 erreicht
preisrechner_lead — wenn nach Preisberechnung das Kontaktformular
abgesendet wird
3. Event-Werte zuweisen (für Smart Bidding später wichtig):
formular_gesendet : 30 EUR
whatsapp_klick : 15 EUR
telefon_klick : 25 EUR
preisrechner_lead : 50 EUR (höher, weil qualifizierter)
4. Google Ads Conversion-Tag vorbereiten
Platzhalter-Code für Google Ads Conversion-ID einfügen (kommentiert), den ich
später mit der echten ID füllen kann
Anweisung schreiben, wie ich die Conversion-IDs in Google Ads erstelle
5. Test: Erkläre mir am Ende der Phase, wie ich mit dem Tag Assistant Chrome
Extension prüfen kann, ob alle Events feuern.
Commit-Message: feat: add GTM and conversion tracking for Google Ads
 PHASE 2: DSGVO & Rechtssicherheit
Ziel: Google lehnt Ads ab oder bestraft dich, wenn die Landingpage nicht DSGVO-
konform ist. Außerdem Abmahnrisiko.
Aufgaben:
1. Cookie-Consent-Banner einbauen
Empfehlung: Klaro! (Open Source, DSGVO-konform, leicht) oder CookieFirst
(kostenpflichtig aber komfortabler)
Banner muss: GTM/Analytics blockieren bis Zustimmung, "Ablehnen"
gleichwertig zu "Akzeptieren" anbieten, Einstellungen änderbar machen
GTM-Trigger so konfigurieren, dass Tags erst nach Consent feuern
2. DSGVO-Checkbox im Hauptformular
Aktuell ist die Datenschutz-Zustimmung nur als Text vorhanden — das reicht
nicht
Echte <input type="checkbox" required> einbauen mit Text: "Ich habe die
Datenschutzerklärung gelesen und stimme der Verarbeitung meiner Daten zur
Angebotserstellung zu."
Submit-Button deaktivieren bis Checkbox angeklickt
Gleiche Änderung im Modal-Formular und im Preisrechner
3. Impressum prüfen und ergänzen
Datei impressum.html öffnen und checken, ob folgende Angaben enthalten sind:
Vor- und Nachname (Jeremie [Nachname])
Vollständige Adresse
Telefonnummer (0160 94904681)
E-Mail-Adresse
USt-IdNr. (falls vorhanden)
Güterkraftverkehrserlaubnis oder Hinweis darauf (wichtig für
Transportfirmen!)
Aufsichtsbehörde
Falls etwas fehlt: mich danach fragen und einbauen
4. Datenschutzerklärung erweitern
Datei datenschutz.html muss erwähnen: GTM, Google Ads, Google Analytics,
WhatsApp-Kontakt, Vercel-Hosting
Falls Sektionen fehlen: Standardtexte vorschlagen (z.B. von e-recht24.de
Generator)
Commit-Message: feat: GDPR compliance — cookie consent, form checkbox, legal
pages
 PHASE 3: Performance & Mobile-Optimierung
Ziel: Google Ads belohnt schnelle Landingpages mit besserem Quality Score. 80% der
Klicks kommen mobil.
Aufgaben:
1. PageSpeed Insights laufen lassen
Mir die URL nennen: https://pagespeed.web.dev/analysis?
url=https://dienordmaenner.com
Mich fragen nach Mobile-Score und Largest Contentful Paint (LCP)
2. Hero-Video optimieren
hero.mp4 ist ein Performance-Risiko auf Mobile
Optionen vorschlagen:
A) Video komprimieren (z.B. mit ffmpeg auf max. 1.5 MB)
B) Auf Mobile durch optimiertes WebP-Bild ersetzen (mit <picture> und
Media Query)
C) Video komplett entfernen, durch starkes Hero-Bild ersetzen
Mit loading="lazy" und preload="none" für Videos arbeiten
3. Bilder optimieren
Alle <img> Tags durchgehen und loading="lazy" (außer Hero-Bereich) sowie
width und height Attribute setzen (verhindert Cumulative Layout Shift)
Vorschlagen, große JPG/PNG Bilder zu WebP zu konvertieren
<picture> Element nutzen, wo Mobile/Desktop unterschiedliche Bilder Sinn
machen
4. Critical CSS inline einbauen
Above-the-fold CSS direkt im <head> als <style> einbinden
Rest des CSS mit media="print" Trick lazy laden
5. Schriftarten optimieren
font-display: swap setzen
Falls Google Fonts genutzt werden: prüfen, ob sie self-hosted werden können
(DSGVO + Performance)
Commit-Message: perf: optimize images, video, fonts for mobile page speed
 PHASE 4: Conversion-Optimierung & Trust
Ziel: Klicks in Anrufe verwandeln. Mehr Vertrauen, weniger Reibung.
Aufgaben:
1. Inkonsistenzen fixen
Öffnungszeiten vereinheitlichen: Im Header steht "Mo–Sa 7–19 Uhr", im Footer
"Mo–Sa 7:00–20:00 Uhr" — alle auf eine Version bringen
Mich fragen, welche Zeiten korrekt sind
2. CTA-Buttons verbessern
"In 30 Sekunden Rückruf anfordern" → ist missverständlich (klingt nach: wir
rufen in 30 Sekunden zurück)
Ändern zu: "Kostenloses Angebot anfordern"
"30 Min Antwortzeit"-Versprechen bleibt darunter
3. Trust-Signale prominenter machen
Direkt unter dem Hero-Headline eine Sterne-Bewertungs-Zeile einbauen:
 4,9/5 — basierend auf X Google-Bewertungen (mich nach aktueller
Anzahl fragen)
Falls Google Business Profile existiert: Link einbauen
4. Telefonnummer "klick-to-call" auf Desktop
Aktuell ist die Telefonnummer ein tel: -Link, was auf Desktop oft nicht klickbar
wirkt
Auf Desktop zusätzlich Hover-Effekt + "Zum Kopieren klicken" Funktionalität
(kleines JS)
5. Sticky Mobile-CTA
Auf Mobile: am unteren Bildschirmrand permanent sichtbare CTA-Leiste mit zwei
Buttons: " Anrufen" und " WhatsApp"
Verschwindet nur, wenn das Formular im Sichtbereich ist
6. Formular: Felder reduzieren
Aktuelles Hauptformular: Name, Telefon, Leistung — passt
Modal-Formular hat dieselben Felder — gut
Preisrechner-Endformular hat Name, Telefon, E-Mail — E-Mail als optional
markieren, nicht required
Commit-Message: feat: improve conversion elements — CTAs, trust signals,
sticky mobile bar
 PHASE 5: SEO & Google Ads Landing Page Quality
Ziel: Quality Score 8+ erreichen. Niedrigerer CPC, mehr Sichtbarkeit.
Aufgaben:
1. Meta-Tags pro Seite optimieren
Jede HTML-Seite öffnen und prüfen:
<title> — max. 60 Zeichen, Keyword + Stadt + USP
<meta name="description"> — max. 160 Zeichen, Call-to-Action enthalten
<meta name="robots" content="index, follow">
Beispiele für Hauptseite:
Title: Entrümpelung & Umzug Kiel — Festpreis ab 650€ | Die Nordmänner
Description: ✓ Wohnungsauflösung & Umzug aus einer Hand ✓ Festpreis ohne
Überraschungen ✓ Oft innerhalb 24h. Kostenlose Besichtigung in Kiel &
Umland. Jetzt anrufen!
2. Schema.org Structured Data einbauen
JSON-LD im <head> für LocalBusiness mit:
Name, Adresse, Telefon, Öffnungszeiten
geo Koordinaten
priceRange
aggregateRating (sobald echte Bewertungen vorhanden)
areaServed (Kiel, Neumünster, Rendsburg, Eckernförde, Plön)
3. FAQ Schema einbauen
Die FAQ-Sektion existiert bereits — JSON-LD FAQPage Schema dazu, damit Rich
Snippets in Google angezeigt werden
4. Open Graph & Twitter Cards
Für Social-Sharing einheitliche OG-Tags pro Seite (bringt indirekt auch Trust bei
manuellen Quality-Checks)
5. Landing-Page-Fokus prüfen
Für Google Ads brauchen wir dedizierte Landing-Pages pro Hauptkampagne:
entruempelung-kiel.html → Keyword "Entrümpelung Kiel"
wohnungsaufloesung-kiel.html → Keyword "Wohnungsauflösung Kiel"
privatumzug-kiel.html → Keyword "Umzug Kiel"
Pro Seite prüfen: Kommt das Hauptkeyword in H1, ersten 100 Wörtern und 2x im
Body vor? Falls nicht: Texte optimieren
6. Internal Linking & Sitemap
sitemap.xml erstellen oder updaten
robots.txt prüfen
Beide bei Google Search Console einreichen (Anleitung geben)
Commit-Message: feat: SEO meta tags, structured data, landing page
optimization
 Abschluss-Checkliste (nach Phase 5)
Bevor wir Google Ads schalten, gemeinsam abhaken:
GTM feuert alle Conversion-Events korrekt (mit Tag Assistant getestet)
Cookie-Banner blockiert Tracking bis Zustimmung
DSGVO-Checkbox in allen Formularen aktiv
Impressum vollständig (inkl. Güterkraftverkehrserlaubnis)
PageSpeed Mobile Score > 80
LCP < 2.5s auf Mobile
Mind. 5 echte Google-Rezensionen vorhanden
Google Business Profile verifiziert
Schema.org LocalBusiness validiert (mit Google Rich Results Test)
Sitemap bei Google Search Console eingereicht
Alle Inkonsistenzen (Öffnungszeiten etc.) bereinigt
 So arbeiten wir zusammen
1. Starte mit Phase 1. Lies diesen Plan, frag mich nach allen nötigen Infos (z.B. GTM￾ID), dann setze um.
2. Eine Phase auf einmal. Am Ende jeder Phase: kurze Zusammenfassung was
geändert wurde, dann fragen ob ich weiter will.
3. Git-Commits nach jeder Phase mit der angegebenen Commit-Message.
4. Bei Unklarheiten: Lieber einmal zu viel fragen als blind ändern. Besonders bei
rechtlichen Texten.
5. Tests: Wo möglich, lokal testen bevor gepusht wird.
Bereit? Dann starte mit Phase 1 — Conversion-Tracking.
