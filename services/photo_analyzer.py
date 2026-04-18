import anthropic
import base64
import json
import os

def analyze_photos(files, service_type: str) -> dict:
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        return {'volume_m3': 20, 'weight_kg': 1500,
                'vehicle_recommendation': 'LKW 3,5t',
                'notes': 'Kein API-Key — Standardwerte verwendet.'}

    client = anthropic.Anthropic(api_key=api_key)
    content = []

    for f in files[:5]:
        raw = f.read()
        if not raw:
            continue
        b64 = base64.standard_b64encode(raw).decode()
        mime = f.content_type or 'image/jpeg'
        content.append({
            'type': 'image',
            'source': {'type': 'base64', 'media_type': mime, 'data': b64}
        })

    if not content:
        return {'volume_m3': 20, 'weight_kg': 1500,
                'vehicle_recommendation': 'LKW 3,5t',
                'notes': 'Keine Bilder hochgeladen.'}

    content.append({'type': 'text', 'text': f"""Du analysierst Fotos für eine {service_type}-Dienstleistung.
Schätze basierend auf den Bildern:
1. Gesamtvolumen der Gegenstände in m³
2. Geschätztes Gesamtgewicht in kg
3. Besondere/schwere Gegenstände (Piano, Tresor, große Möbel)
4. Empfohlenes Fahrzeug (Sprinter|LKW 3,5t|LKW 7,5t|LKW 12t)

Antworte NUR als JSON:
{{"volume_m3": <zahl>, "weight_kg": <zahl>, "special_items": ["item"], "vehicle_recommendation": "Sprinter|LKW 3,5t|LKW 7,5t|LKW 12t", "notes": "<1-2 Sätze auf Deutsch>"}}"""})

    try:
        resp = client.messages.create(
            model='claude-opus-4-7',
            max_tokens=400,
            messages=[{'role': 'user', 'content': content}]
        )
        text = resp.content[0].text
        start, end = text.find('{'), text.rfind('}') + 1
        return json.loads(text[start:end])
    except Exception as e:
        return {'volume_m3': 20, 'weight_kg': 1500,
                'vehicle_recommendation': 'LKW 3,5t',
                'notes': f'Analyse fehlgeschlagen: {e}'}
