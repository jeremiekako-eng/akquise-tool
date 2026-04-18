import os
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, HRFlowable)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

NAVY      = HexColor('#0d1b2a')
DARK      = HexColor('#152030')
GOLD      = HexColor('#e8a020')
GOLD2     = HexColor('#f5bc50')
WHITE_T   = HexColor('#f0f4f8')
GRAY      = HexColor('#8a9bb0')
LIGHT_BG  = HexColor('#f7f8fa')
DARK_TEXT = HexColor('#1a1a2e')
MID_TEXT  = HexColor('#444455')

SERVICE_NAMES = {
    'transport':     '🚚 Transport & Lieferung',
    'umzug':         '🏠 Umzug',
    'entruempelung': '🗑️ Entrümpelung'
}

def _s(name, **kw):
    defaults = dict(fontName='Helvetica', fontSize=10, leading=14)
    defaults.update(kw)
    return ParagraphStyle(name, **defaults)

def generate_pdf(data: dict, price: dict, quote_id: str, temp_dir: str) -> str:
    path = os.path.join(temp_dir, f'Angebot_{quote_id}.pdf')
    base_url = os.getenv('BASE_URL', 'http://localhost:8080')

    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )

    now        = datetime.now()
    valid_till = now + timedelta(days=14)
    svc_name   = SERVICE_NAMES.get(data.get('service_type', 'transport'), 'Transport')
    booking    = f"{base_url}/book/{quote_id}"
    W          = 17.4 * cm

    elems = []

    # ── HEADER ──────────────────────────────────────────────
    header = Table([[
        Paragraph('<font color="#f0f4f8"><b>DIE NORDMÄNNER</b></font><br/>'
                  '<font color="#8a9bb0" size="9">Spedition &amp; Transport</font>',
                  _s('h1', fontSize=22, fontName='Helvetica-Bold', leading=28)),
        Paragraph(f'<font color="#e8a020"><b>Angebot #{quote_id}</b></font>',
                  _s('qid', fontSize=16, fontName='Helvetica-Bold', alignment=TA_RIGHT))
    ]], colWidths=[W*0.6, W*0.4])
    header.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), NAVY),
        ('PADDING',    (0,0), (-1,-1), 16),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elems.append(header)

    # date bar
    date_bar = Table([[
        Paragraph(f'<font color="#8a9bb0">Datum: {now.strftime("%d.%m.%Y")}</font>',
                  _s('db', fontSize=9)),
        Paragraph(f'<font color="#e8a020">Gültig bis: {valid_till.strftime("%d.%m.%Y")}</font>',
                  _s('db2', fontSize=9, alignment=TA_RIGHT))
    ]], colWidths=[W*0.5, W*0.5])
    date_bar.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), DARK),
        ('PADDING',    (0,0), (-1,-1), 8),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elems.append(date_bar)
    elems.append(Spacer(1, 0.5*cm))

    # ── CUSTOMER + JOB ─────────────────────────────────────
    cust_text = (f"<b>{data.get('name','')}</b><br/>"
                 f"{data.get('email','')}<br/>"
                 f"{data.get('phone','')}")
    job_text  = (f"<b>Leistung:</b> {svc_name}<br/>"
                 f"<b>Datum:</b> {data.get('date','Nach Vereinbarung')}<br/>"
                 f"<b>Zeitfenster:</b> {data.get('time_window','Flexibel')}")
    if data.get('is_express'):
        job_text += '<br/><font color="#e8a020"><b>⚡ Express</b></font>'

    info = Table([
        [Paragraph('<font color="#e8a020"><b>AUFTRAGGEBER</b></font>',
                   _s('lbl', fontSize=8, fontName='Helvetica-Bold')),
         Paragraph('<font color="#e8a020"><b>AUFTRAGSDETAILS</b></font>',
                   _s('lbl2', fontSize=8, fontName='Helvetica-Bold'))],
        [Paragraph(cust_text, _s('ci', fontSize=10, textColor=DARK_TEXT, leading=16)),
         Paragraph(job_text,  _s('ji', fontSize=10, textColor=DARK_TEXT, leading=16))]
    ], colWidths=[W*0.48, W*0.48])
    info.setStyle(TableStyle([
        ('BACKGROUND',  (0,0), (-1,0), LIGHT_BG),
        ('BACKGROUND',  (0,1), (-1,1), white),
        ('PADDING',     (0,0), (-1,-1), 10),
        ('VALIGN',      (0,0), (-1,-1), 'TOP'),
        ('LINEBELOW',   (0,0), (-1,0), 1, GOLD),
        ('BOX',         (0,0), (-1,-1), 0.5, HexColor('#dde0e8')),
        ('INNERGRID',   (0,0), (-1,-1), 0.5, HexColor('#dde0e8')),
    ]))
    elems.append(info)
    elems.append(Spacer(1, 0.4*cm))

    # ── ROUTE ──────────────────────────────────────────────
    elems.append(HRFlowable(width=W, thickness=2, color=GOLD))
    elems.append(Spacer(1, 0.25*cm))
    elems.append(Paragraph('<font color="#1a1a2e"><b>Route &amp; Leistungsumfang</b></font>',
                            _s('sec', fontSize=12, fontName='Helvetica-Bold')))
    elems.append(Spacer(1, 0.2*cm))

    route_rows = [
        ['Von',         data.get('origin', '–')],
        ['Nach',        data.get('destination', '–')],
        ['Distanz',     f"{data.get('distance_km', '–')} km"],
        ['Fahrtzeit',   f"{data.get('duration_minutes', '–')} Min."],
        ['Fahrzeug',    price.get('vehicle', '–')],
    ]
    if data.get('weight_kg'):
        route_rows.append(['Gewicht (gesch.)', f"{data.get('weight_kg')} kg"])
    if data.get('volume_m3'):
        route_rows.append(['Volumen (gesch.)', f"{data.get('volume_m3')} m³"])
    if data.get('notes'):
        route_rows.append(['Hinweise', data.get('notes')])

    route_tbl = Table(
        [[Paragraph(f'<font color="#8a9bb0"><b>{r[0]}</b></font>', _s('rl', fontSize=9)),
          Paragraph(str(r[1]), _s('rv', fontSize=10, textColor=DARK_TEXT))]
         for r in route_rows],
        colWidths=[4.5*cm, W - 4.5*cm]
    )
    route_tbl.setStyle(TableStyle([
        ('PADDING',      (0,0), (-1,-1), 7),
        ('ROWBACKGROUNDS',(0,0), (-1,-1), [LIGHT_BG, white]),
        ('GRID',         (0,0), (-1,-1), 0.5, HexColor('#dde0e8')),
        ('VALIGN',       (0,0), (-1,-1), 'TOP'),
    ]))
    elems.append(route_tbl)
    elems.append(Spacer(1, 0.4*cm))

    # ── PRICE ──────────────────────────────────────────────
    elems.append(HRFlowable(width=W, thickness=2, color=GOLD))
    elems.append(Spacer(1, 0.25*cm))
    elems.append(Paragraph('<font color="#1a1a2e"><b>Preisaufstellung</b></font>',
                            _s('sec2', fontSize=12, fontName='Helvetica-Bold')))
    elems.append(Spacer(1, 0.2*cm))

    def pr(label, amount, bold=False):
        fn = 'Helvetica-Bold' if bold else 'Helvetica'
        return [
            Paragraph(f'<font name="{fn}" color="#444455">{label}</font>',
                      _s('pl', fontSize=10, fontName=fn, textColor=MID_TEXT)),
            Paragraph(f'<font name="{fn}" color="#1a1a2e">€ {amount:.2f}</font>',
                      _s('pa', fontSize=10, fontName=fn, textColor=DARK_TEXT, alignment=TA_RIGHT))
        ]

    p_rows  = [['Position', 'Betrag']]
    p_rows += [pr('Fahrtkosten (Hin- & Rückfahrt)', price['distance_cost'])]
    p_rows += [pr('Arbeitszeit inkl. Be-/Entladen',  price['time_cost'])]
    if price.get('weight_extra', 0) > 0:
        p_rows += [pr('Gewichtszuschlag', price['weight_extra'])]
    for k, v in price.get('surcharges', {}).items():
        p_rows += [pr(k, v)]
    p_rows += [pr('Nettobetrag',  price['net'],  bold=True)]
    p_rows += [pr('MwSt. 19 %',  price['vat'])]
    p_rows += [[
        Paragraph('<b>GESAMTBETRAG</b>', _s('gt', fontSize=13, fontName='Helvetica-Bold', textColor=NAVY)),
        Paragraph(f'<b>€ {price["gross"]:.2f}</b>',
                  _s('gv', fontSize=14, fontName='Helvetica-Bold', textColor=NAVY, alignment=TA_RIGHT))
    ]]

    price_tbl = Table(p_rows, colWidths=[W*0.72, W*0.28])
    price_tbl.setStyle(TableStyle([
        ('BACKGROUND',   (0,0),  (-1,0),  NAVY),
        ('TEXTCOLOR',    (0,0),  (-1,0),  white),
        ('FONTNAME',     (0,0),  (-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',     (0,0),  (-1,0),  10),
        ('PADDING',      (0,0),  (-1,-1), 9),
        ('ALIGN',        (1,0),  (1,-1),  'RIGHT'),
        ('ROWBACKGROUNDS',(0,1), (-1,-3), [LIGHT_BG, white]),
        ('LINEABOVE',    (0,-2), (-1,-2), 1, GOLD),
        ('LINEABOVE',    (0,-1), (-1,-1), 2, NAVY),
        ('BACKGROUND',   (0,-1), (-1,-1), GOLD),
        ('FONTNAME',     (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('GRID',         (0,0),  (-1,-1), 0.5, HexColor('#dde0e8')),
    ]))
    elems.append(price_tbl)
    elems.append(Spacer(1, 0.6*cm))

    # ── BOOKING ────────────────────────────────────────────
    book_tbl = Table([[
        Paragraph(
            f'<b>Jetzt verbindlich buchen:</b><br/>'
            f'<font color="#e8a020">{booking}</font>',
            _s('bk', fontSize=11, textColor=DARK_TEXT, leading=20)
        )
    ]], colWidths=[W])
    book_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_BG),
        ('BOX',        (0,0), (-1,-1), 2, GOLD),
        ('PADDING',    (0,0), (-1,-1), 14),
    ]))
    elems.append(book_tbl)
    elems.append(Spacer(1, 0.5*cm))

    # ── FOOTER ─────────────────────────────────────────────
    foot = Table([[
        Paragraph(
            '<font color="#8a9bb0">Die Nordmänner – Spedition &amp; Transport&nbsp;&nbsp;|&nbsp;&nbsp;'
            'info@dienordmaenner.com&nbsp;&nbsp;|&nbsp;&nbsp;'
            'Dieses Angebot ist 14 Tage gültig.</font>',
            _s('ft', fontSize=8, textColor=GRAY, alignment=TA_CENTER)
        )
    ]], colWidths=[W])
    foot.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), NAVY),
        ('PADDING',    (0,0), (-1,-1), 10),
    ]))
    elems.append(foot)

    doc.build(elems)
    return path
