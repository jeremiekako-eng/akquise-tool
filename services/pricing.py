import json
import os
from datetime import datetime

def _tariffs():
    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'tariffs.json')
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def recommend_vehicle(kg: float, m3: float) -> str:
    if kg <= 1000 and m3 <= 8:
        return 'Sprinter (bis 1t)'
    if kg <= 3500 and m3 <= 20:
        return 'LKW 3,5t'
    if kg <= 7500 and m3 <= 40:
        return 'LKW 7,5t'
    return 'LKW 12t'

def calculate_price(data: dict) -> dict:
    t = _tariffs()
    svc       = data.get('service_type', 'transport')
    km        = float(data.get('distance_km', 50))
    mins      = float(data.get('duration_minutes', 60))
    kg        = float(data.get('weight_kg', 500))
    m3        = float(data.get('volume_m3', 5))
    express   = bool(data.get('is_express', False))
    date_str  = data.get('date', '')

    distance_cost = km * 2 * t['base_price_per_km']
    loading_h     = t['loading_hours'].get(svc, 2.0)
    time_cost     = (mins / 60 + loading_h) * t['hourly_rate']

    weight_extra = 0.0
    for threshold, surcharge in sorted(t['weight_surcharge'].items(), key=lambda x: int(x[0])):
        if kg > int(threshold):
            weight_extra = float(surcharge)

    subtotal = max(distance_cost + time_cost + weight_extra, t['min_price'].get(svc, 150))
    surcharges = {}

    if express:
        amt = subtotal * t['express_surcharge_percent'] / 100
        surcharges['Expressaufschlag'] = round(amt, 2)
        subtotal += amt

    if date_str:
        try:
            d = datetime.strptime(date_str, '%Y-%m-%d')
            if d.weekday() >= 5:
                amt = subtotal * t['weekend_surcharge_percent'] / 100
                surcharges['Wochenendzuschlag'] = round(amt, 2)
                subtotal += amt
        except Exception:
            pass

    fuel = subtotal * t['fuel_surcharge_percent'] / 100
    surcharges['Kraftstoffzuschlag'] = round(fuel, 2)
    subtotal += fuel

    net   = round(subtotal, 2)
    vat   = round(net * 0.19, 2)
    gross = round(net + vat, 2)

    return {
        'distance_cost': round(distance_cost, 2),
        'time_cost':     round(time_cost, 2),
        'weight_extra':  round(weight_extra, 2),
        'surcharges':    surcharges,
        'net':           net,
        'vat':           vat,
        'gross':         gross,
        'vehicle':       recommend_vehicle(kg, m3)
    }
