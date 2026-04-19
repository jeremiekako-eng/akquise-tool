from flask import Flask, request, jsonify, send_from_directory, abort
import os, json, uuid, traceback, threading
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR   = Path(__file__).parent
TEMP_DIR   = BASE_DIR / 'temp'
DATA_DIR   = BASE_DIR / 'data'
TEMP_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
QUOTES_FILE = DATA_DIR / 'quotes.json'

app = Flask(__name__)

# ── helpers ──────────────────────────────────────────────────────────────────

def _load_quotes() -> dict:
    if QUOTES_FILE.exists():
        with open(QUOTES_FILE, encoding='utf-8') as f:
            return json.load(f)
    return {}

def _save_quote(quote_id: str, data: dict):
    q = _load_quotes()
    q[quote_id] = data
    with open(QUOTES_FILE, 'w', encoding='utf-8') as f:
        json.dump(q, f, indent=2, ensure_ascii=False)

# ── static files ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory(str(BASE_DIR), 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory(str(BASE_DIR), filename)

# ── API ───────────────────────────────────────────────────────────────────────

@app.route('/api/autocomplete', methods=['GET'])
def api_autocomplete():
    import requests as req
    q       = request.args.get('q', '').strip()
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
    if not q or len(q) < 3:
        return jsonify([])
    if not api_key:
        return jsonify([])
    r = req.get(
        'https://maps.googleapis.com/maps/api/place/autocomplete/json',
        params={'input': q, 'types': 'address', 'language': 'de',
                'components': 'country:de', 'key': api_key},
        timeout=5
    )
    data = r.json()
    results = []
    for p in data.get('predictions', [])[:6]:
        results.append({
            'label': p['structured_formatting']['main_text'],
            'sub':   p['structured_formatting'].get('secondary_text', ''),
            'full':  p['description']
        })
    return jsonify(results)


@app.route('/api/distance', methods=['POST'])
def api_distance():
    from services.maps import get_distance
    body = request.get_json(silent=True) or {}
    if not body.get('origin') or not body.get('destination'):
        return jsonify({'error': 'Fehlende Adressen'}), 400
    return jsonify(get_distance(body['origin'], body['destination']))


@app.route('/api/analyze-photos', methods=['POST'])
def api_analyze():
    from services.photo_analyzer import analyze_photos
    files = request.files.getlist('photos')
    svc   = request.form.get('service_type', 'umzug')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'Keine Dateien hochgeladen'}), 400
    return jsonify(analyze_photos(files, svc))


@app.route('/api/submit-quote', methods=['POST'])
def api_submit():
    from services.pricing      import calculate_price
    from services.pdf_generator import generate_pdf
    from services.email_sender  import send_quote_email

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Keine Daten empfangen'}), 400

    try:
        price     = calculate_price(data)
        quote_id  = str(uuid.uuid4())[:8].upper()
        pdf_path  = generate_pdf(data, price, quote_id, str(TEMP_DIR))
        _save_quote(quote_id, {**data, 'price': price, 'status': 'pending'})

        def _send():
            try:
                send_quote_email(data['email'], data['name'], pdf_path, quote_id)
                _save_quote(quote_id, {**data, 'price': price, 'status': 'sent'})
                print(f"Email sent for {quote_id}")
            except Exception as e:
                print(f"Email failed for {quote_id}: {e}")

        threading.Thread(target=_send, daemon=True).start()
        return jsonify({'success': True, 'quote_id': quote_id, 'price': price})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ── booking confirmation ──────────────────────────────────────────────────────

@app.route('/book/<quote_id>')
def book(quote_id):
    quotes = _load_quotes()
    if quote_id not in quotes:
        abort(404)
    quotes[quote_id]['status'] = 'booked'
    _save_quote(quote_id, quotes[quote_id])
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <title>Buchung bestätigt – Die Nordmänner</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet"/>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:Inter,sans-serif;background:#0d1b2a;color:#f0f4f8;
          display:flex;align-items:center;justify-content:center;min-height:100vh;padding:20px}}
    .box{{text-align:center;padding:3rem 2.5rem;background:#1a2a3a;border-radius:20px;
          max-width:500px;width:100%;border:1px solid rgba(232,160,32,.2)}}
    .icon{{font-size:4rem;margin-bottom:1rem}}
    h1{{color:#e8a020;font-size:1.8rem;margin-bottom:1rem}}
    p{{color:#8a9bb0;margin:.5rem 0;line-height:1.6}}strong{{color:#f0f4f8}}
    .btn{{display:inline-block;margin-top:2rem;padding:.9rem 2.5rem;background:#e8a020;
          color:#0d1b2a;border-radius:10px;text-decoration:none;font-weight:700;transition:.2s}}
    .btn:hover{{background:#f5bc50}}
  </style>
</head>
<body>
  <div class="box">
    <div class="icon">✅</div>
    <h1>Buchung bestätigt!</h1>
    <p>Angebot <strong>#{quote_id}</strong> wurde erfolgreich gebucht.</p>
    <p>Wir melden uns innerhalb von 24 Stunden zur Terminbestätigung.</p>
    <p style="margin-top:1rem">Kontakt: <strong>info@dienordmaenner.com</strong></p>
    <a href="/" class="btn">← Zur Startseite</a>
  </div>
</body>
</html>"""


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True, host='0.0.0.0', port=port)
