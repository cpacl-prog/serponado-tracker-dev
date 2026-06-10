import os
import json
import sys
import requests
from datetime import datetime, timezone

LOGIN    = os.environ['DATAFORSEO_LOGIN']
PASSWORD = os.environ['DATAFORSEO_PASSWORD']
KEYWORD  = 'Serponado'
OUTPUT   = 'public/rankings.json'
OWN_DOMAIN  = 'optimerch.de'
OWN_URL     = 'optimerch.de/serponado'
MAX_DISPLAY = 20
MAX_HISTORY = 576  # 24 Tage à 24 Stunden

payload = [{
    "keyword":       KEYWORD,
    "location_code": 2276,
    "language_code": "de",
    "device":        "desktop",
    "os":            "windows",
    "depth":         100
}]

try:
    response = requests.post(
        'https://api.dataforseo.com/v3/serp/google/organic/live/advanced',
        auth=(LOGIN, PASSWORD),
        json=payload,
        timeout=60
    )
    response.raise_for_status()
    data = response.json()
except requests.RequestException as e:
    print(f"❌ API-Fehler: {e}", file=sys.stderr)
    sys.exit(1)

try:
    items   = data['tasks'][0]['result'][0]['items']
    organic = [i for i in items if i.get('type') == 'organic']
except (KeyError, IndexError, TypeError) as e:
    print(f"❌ Unerwartete API-Antwort: {e}", file=sys.stderr)
    print(json.dumps(data, indent=2), file=sys.stderr)
    sys.exit(1)

rankings = [
    {
        'position': item.get('rank_absolute'),
        'domain':   item.get('domain'),
        'url':      item.get('url'),
        'title':    item.get('title', ''),
    }
    for item in organic
]

now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

top20 = rankings[:MAX_DISPLAY]
positions = {r['domain']: r['position'] for r in top20 if r['domain']}

# Spezifische URL separat tracken
own_url_result = next(
    (r for r in rankings if r['url'] and OWN_URL in r['url']),
    None
)
own_url_data = {
    'url':      'https://www.optimerch.de/serponado/',
    'position': own_url_result['position'] if own_url_result else None,
    'title':    own_url_result['title'] if own_url_result else '',
}

own_position = next(
    (r['position'] for r in rankings if r['domain'] and OWN_DOMAIN in r['domain']),
    None
)

# Bestehende History laden
history = []
if os.path.exists(OUTPUT):
    try:
        with open(OUTPUT, 'r', encoding='utf-8') as f:
            existing = json.load(f)
            history = existing.get('history', [])
    except (json.JSONDecodeError, IOError):
        pass

history.append({'ts': now, 'positions': positions})
history = history[-MAX_HISTORY:]

output = {
    'keyword':    KEYWORD,
    'updated_at': now,
    'own_url':    own_url_data,
    'rankings':   top20,
    'history':    history,
}

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"✅ {len(rankings)} Ergebnisse gespeichert. {OWN_DOMAIN}: Position {own_position} | /serponado/: Position {own_url_data['position']}")
