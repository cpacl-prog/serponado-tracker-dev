import os
import json
import sys
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

LOGIN    = os.environ['DATAFORSEO_LOGIN']
PASSWORD = os.environ['DATAFORSEO_PASSWORD']
KEYWORD  = 'Serponado'
OUTPUT   = 'public/rankings.json'
OWN_DOMAIN  = 'optimerch.de'
OWN_URL     = 'optimerch.de/serponado'
MAX_DISPLAY = 10
MAX_HISTORY = 1440  # 30 Tage à 48 Halbstunden

payload = [{
    "keyword":                    KEYWORD,
    "location_name":              "Berlin,Berlin,Germany",
    "language_code":              "de",
    "se_domain":                  "google.de",
    "device":                     "desktop",
    "os":                         "windows",
    "depth":                      100,
    "browser_screen_width":       1920,
    "browser_screen_height":      1080,
    "browser_screen_scale_factor": 1
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
        'position': item.get('rank_group'),
        'domain':   item.get('domain'),
        'url':      item.get('url'),
        'title':    item.get('title', ''),
    }
    for item in organic
]

now = datetime.now(ZoneInfo('Europe/Berlin')).strftime('%Y-%m-%d %H:%M (Berlin)')

top20 = rankings[:MAX_DISPLAY]
positions = {r['domain']: r['position'] for r in top20 if r['domain']}

# Bestehende Daten laden (History + letzter own_url-Stand)
existing_data = {}
history = []
if os.path.exists(OUTPUT):
    try:
        with open(OUTPUT, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            history = existing_data.get('history', [])
    except (json.JSONDecodeError, IOError):
        pass

# Spezifische URL separat tracken
own_url_result = next(
    (r for r in rankings if r['url'] and OWN_URL in r['url']),
    None
)

if own_url_result:
    own_url_data = {
        'url':      'https://www.optimerch.de/serponado/',
        'position': own_url_result['position'],
        'title':    own_url_result['title'],
        'stale':    False,
    }
else:
    # Letzte bekannte Position behalten statt leer anzuzeigen
    last = existing_data.get('own_url', {})
    own_url_data = {
        'url':      'https://www.optimerch.de/serponado/',
        'position': last.get('position'),
        'title':    last.get('title', ''),
        'stale':    True,
    }

own_position = next(
    (r['position'] for r in rankings if r['domain'] and OWN_DOMAIN in r['domain']),
    None
)

history.append({'ts': now, 'positions': positions})
history = history[-MAX_HISTORY:]

# Top-3-Momente: beste Position des Tages, nur wenn Top 3
top3_moments = existing_data.get('top3_moments', [])
today = now.split(' ')[0]

if not own_url_data['stale'] and own_url_data['position'] and own_url_data['position'] <= 3:
    today_entry = next((m for m in top3_moments if m['date'] == today), None)
    if today_entry:
        if own_url_data['position'] < today_entry['position']:
            today_entry['position'] = own_url_data['position']
    else:
        top3_moments.append({'date': today, 'position': own_url_data['position']})

top3_moments.sort(key=lambda m: m['date'], reverse=True)
top3_moments = top3_moments[:90]  # max 90 Tage aufbewahren

output = {
    'keyword':      KEYWORD,
    'updated_at':   now,
    'own_url':      own_url_data,
    'top3_moments': top3_moments,
    'rankings':     top20,
    'history':      history,
}

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

stale_note = ' (zuletzt gesehen)' if own_url_data['stale'] else ''
print(f"✅ {len(rankings)} Ergebnisse gespeichert. {OWN_DOMAIN}: Position {own_position} | /serponado/: Position {own_url_data['position']}{stale_note}")
