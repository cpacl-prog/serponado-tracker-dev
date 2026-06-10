import os
import json
import sys
import requests
from datetime import datetime, timezone

LOGIN    = os.environ['DATAFORSEO_LOGIN']
PASSWORD = os.environ['DATAFORSEO_PASSWORD']
KEYWORD  = 'Serponado'
OUTPUT   = 'public/rankings.json'

payload = [{
    "keyword":       KEYWORD,
    "location_code": 2276,   # Deutschland
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

output = {
    'keyword':    KEYWORD,
    'updated_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
    'rankings':   rankings[:50]  # Top 50
}

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"✅ {len(rankings)} Ergebnisse gespeichert in {OUTPUT}")
