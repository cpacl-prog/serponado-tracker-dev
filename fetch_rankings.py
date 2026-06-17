import os
import json
import sys
import sqlite3
import requests
from urllib.parse import urlparse
from datetime import datetime
from zoneinfo import ZoneInfo

AHREFS_TOKEN = os.environ['AHREFS_API_KEY']
KEYWORD      = 'Serponado'
OUTPUT       = 'public/rankings.json'
OWN_DOMAIN   = 'optimerch.de'
OWN_URL      = 'optimerch.de/serponado'
MAX_DISPLAY  = 10
MAX_HISTORY  = 1440   # 30 Tage à 48 Halbstunden
LOG_DB       = 'rankings_log.db'

# ── SQLite Setup ──────────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(LOG_DB)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS runs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ts           TEXT    NOT NULL,
            results_json TEXT    NOT NULL
        )
    ''')
    conn.commit()
    return conn

# ── Ahrefs SERP Overview ──────────────────────────────────────────────────────

def fetch_rankings():
    date_str = datetime.now(ZoneInfo('UTC')).strftime('%Y-%m-%dT%H:%M:%SZ')
    try:
        resp = requests.get(
            'https://api.ahrefs.com/v3/serp-overview/serp-overview',
            headers={
                'Authorization': f'Bearer {AHREFS_TOKEN}',
                'Accept':        'application/json',
            },
            params={
                'keyword': KEYWORD,
                'country': 'de',
                'date':    date_str,
                'select':  'url,title,position,type',
            },
            timeout=30
        )
        if not resp.ok:
            print(f"❌ Ahrefs HTTP {resp.status_code}: {resp.text[:500]}", file=sys.stderr)
            sys.exit(1)
        data = resp.json()
    except requests.RequestException as e:
        print(f"❌ Ahrefs API-Fehler: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        raw_positions = data['positions']
    except (KeyError, TypeError) as e:
        print(f"❌ Unerwartete Ahrefs-Antwort: {e}", file=sys.stderr)
        print(json.dumps(data, indent=2), file=sys.stderr)
        sys.exit(1)

    rankings = []
    for item in raw_positions:
        types = item.get('type', [])
        if 'organic' not in types:
            continue
        url    = item.get('url', '')
        domain = item.get('domain') or urlparse(url).netloc.lstrip('www.')
        rankings.append({
            'position': item.get('position'),
            'domain':   domain,
            'url':      url,
            'title':    item.get('title', ''),
        })

    return rankings

# ── Hauptlauf ─────────────────────────────────────────────────────────────────

now  = datetime.now(ZoneInfo('Europe/Berlin')).strftime('%Y-%m-%d %H:%M (Berlin)')
conn = init_db()

rankings = fetch_rankings()
print(f"  Ahrefs: {len(rankings)} organische Ergebnisse")

conn.execute(
    'INSERT INTO runs (ts, results_json) VALUES (?, ?)',
    (now, json.dumps(rankings, ensure_ascii=False))
)
conn.commit()
conn.close()

# ── Bestehende Daten laden ────────────────────────────────────────────────────

existing_data = {}
history       = []

if os.path.exists(OUTPUT):
    try:
        with open(OUTPUT, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            history       = existing_data.get('history', [])
    except (json.JSONDecodeError, IOError):
        pass

# ── Top 10 aufbereiten ────────────────────────────────────────────────────────

top10     = rankings[:MAX_DISPLAY]
positions = {r['domain']: r['position'] for r in top10 if r['domain']}

# ── Eigene URL tracken ────────────────────────────────────────────────────────

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

# ── History ───────────────────────────────────────────────────────────────────

history.append({'ts': now, 'positions': positions})
history = history[-MAX_HISTORY:]

# ── Top-3-Momente ─────────────────────────────────────────────────────────────

top3_moments = existing_data.get('top3_moments', [])
today        = now.split(' ')[0]

if not own_url_data['stale'] and own_url_data['position'] and own_url_data['position'] <= 3:
    today_entry = next((m for m in top3_moments if m['date'] == today), None)
    if today_entry:
        if own_url_data['position'] < today_entry['position']:
            today_entry['position'] = own_url_data['position']
    else:
        top3_moments.append({'date': today, 'position': own_url_data['position']})

top3_moments.sort(key=lambda m: m['date'], reverse=True)
top3_moments = top3_moments[:90]

# ── Output schreiben ──────────────────────────────────────────────────────────

output = {
    'keyword':      KEYWORD,
    'updated_at':   now,
    'own_url':      own_url_data,
    'top3_moments': top3_moments,
    'rankings':     top10,
    'history':      history,
}

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

stale_note = ' (zuletzt gesehen)' if own_url_data['stale'] else ''
print(
    f"✅ {len(rankings)} Ergebnisse gespeichert. "
    f"{OWN_DOMAIN}: Position {own_position} | "
    f"/serponado/: Position {own_url_data['position']}{stale_note}"
)
