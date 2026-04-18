import requests
import os

def get_distance(origin: str, destination: str) -> dict:
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    if not api_key:
        return {
            'distance_km': 50, 'duration_minutes': 60,
            'distance_text': '50 km', 'duration_text': '1 Std.',
            'mock': True
        }

    r = requests.get(
        'https://maps.googleapis.com/maps/api/distancematrix/json',
        params={'origins': origin, 'destinations': destination,
                'units': 'metric', 'language': 'de', 'key': api_key},
        timeout=10
    )
    data = r.json()

    if data.get('status') != 'OK':
        return {'error': 'Route nicht gefunden'}

    el = data['rows'][0]['elements'][0]
    if el.get('status') != 'OK':
        return {'error': f"Adresse nicht auflösbar ({el.get('status')})"}

    return {
        'distance_km': round(el['distance']['value'] / 1000, 1),
        'duration_minutes': round(el['duration']['value'] / 60),
        'distance_text': el['distance']['text'],
        'duration_text': el['duration']['text']
    }
