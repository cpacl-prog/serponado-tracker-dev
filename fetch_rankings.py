import os
import json
import sys
import time
import sqlite3
import requests
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

LOGIN    = os.environ['DATAFORSEO_LOGIN']
PASSWORD = os.environ['DATAFORSEO_PASSWORD']
KEYWORD  = 'Serponado'
OUTPUT   = 'public/rankings.json'
OWN_DOMAIN     = 'optimerch.de'
OWN_URL        = 'optimerch.de/serponado'
MAX_DISPLAY    = 10
MAX_HISTORY    = 1440   # 30 Tage à 48 Halbstunden
CONSENSUS_RUNS = 3
LOG_DB         = 'rankings_log.db'

PAYLOAD = {
    "keyword":                     KEYWORD,
    "location_name":               "Dortmund,North Rhine-Westphalia,Germany",
    "language_code":               "de",
    "se_domain":                   "google.de",
    "device":                      "desktop",
    "os":                          "windows",
    "depth":                       10,
    "browser_screen_width":        1920,
    "browser_screen_height":       1080,
    "browser_screen_scale_factor": 1
}

# ── SQLite Setup ──────────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(LOG_DB)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS runs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ts           TEXT    NOT NULL,
            run_num      INTEGER NOT NULL,
            check_url    TEXT,
            results_json TEXT    NOT NULL
        )
    ''')
    conn.commit()
    return conn

# ── API ───────────────────────────────────────────────────────────────────────

def fetch_once(run_num):
    try:
        resp = requests.post(
            'https://api.dataforseo.com/v3/serp/google/organic/live/advanced',
            auth=(LOGIN, PASSWORD),
            json=[PAYLOAD],
            timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"❌ API-Fehler (Run {run_num}): {e}", file=sys.stderr)
        sys.exit(1)

    try:
        result    = data['tasks'][0]['result'][0]
        items     = result['items']
        check_url = result.get('check_url', '')
        organic   = [i for i in items if i.get('type') == 'organic']
    except (KeyError, IndexError, TypeError) as e:
        print(f"❌ Unerwartete API-Antwort (Run {run_num}): {e}", file=sys.stderr)
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
    return rankings, check_url

# ── Mehrheitsentscheid ────────────────────────────────────────────────────────

def majority_consensus(all_runs, stable_prev):
    """Baut Top-10 per Mehrheitsentscheid aus CONSENSUS_RUNS Ergebnissen."""
    prev_by_domain = {r['domain']: r for r in (stable_prev or [])}

    # Positionen pro Domain über alle Runs sammeln
    domain_entries = {}   # domain -> [item, item, ...]
    for run in all_runs:
        for item in run:
            domain_entries.setdefault(item['domain'], []).append(item)

    consensus = []
    for domain, entries in domain_entries.items():
        positions    = [e['position'] for e in entries]
        pos_count    = Counter(positions)
        best_pos, cnt = pos_count.most_common(1)[0]
        uncertain    = cnt < 2  # weniger als 2 von 3 stimmen überein

        if uncertain and domain in prev_by_domain:
            prev = prev_by_domain[domain]
            consensus.append({
                'position':  prev.get('position'),
                'domain':    domain,
                'url':       prev.get('url'),
                'title':     prev.get('title', ''),
                'uncertain': True,
            })
        else:
            ref = next((e for e in entries if e['position'] == best_pos), entries[0])
            consensus.append({
                'position':  best_pos,
                'domain':    domain,
                'url':       ref['url'],
                'title':     ref['title'],
                'uncertain': uncertain,
            })

    consensus.sort(key=lambda x: (x['position'] is None, x['position'] or 9999))
    return consensus[:MAX_DISPLAY]

# ── Hauptlauf ─────────────────────────────────────────────────────────────────

now    = datetime.now(ZoneInfo('Europe/Berlin')).strftime('%Y-%m-%d %H:%M (Berlin)')
conn   = init_db()
all_runs = []

for run_num in range(1, CONSENSUS_RUNS + 1):
    rankings, check_url = fetch_once(run_num)
    all_runs.append(rankings)

    conn.execute(
        'INSERT INTO runs (ts, run_num, check_url, results_json) VALUES (?, ?, ?, ?)',
        (now, run_num, check_url, json.dumps(rankings, ensure_ascii=False))
    )
    conn.commit()

    short_url = (check_url[:80] + '…') if len(check_url) > 80 else check_url
    print(f"  Run {run_num}/{CONSENSUS_RUNS}: {len(rankings)} Ergebnisse | {short_url or 'n/a'}")

    if run_num < CONSENSUS_RUNS:
        time.sleep(2)   # kurze Pause zwischen den Requests

conn.close()

# ── Bestehende Daten laden ────────────────────────────────────────────────────

existing_data    = {}
history          = []
stable_prev      = []

if os.path.exists(OUTPUT):
    try:
        with open(OUTPUT, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            history       = existing_data.get('history', [])
            stable_prev   = [
                r for r in existing_data.get('rankings', [])
                if not r.get('uncertain', False)
            ]
    except (json.JSONDecodeError, IOError):
        pass

# ── Konsens berechnen ─────────────────────────────────────────────────────────

rankings = majority_consensus(all_runs, stable_prev)

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
    'keyword':        KEYWORD,
    'updated_at':     now,
    'consensus_runs': CONSENSUS_RUNS,
    'own_url':        own_url_data,
    'top3_moments':   top3_moments,
    'rankings':       top10,
    'history':        history,
}

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

uncertain_count = sum(1 for r in top10 if r.get('uncertain'))
stale_note      = ' (zuletzt gesehen)' if own_url_data['stale'] else ''
print(
    f"✅ {len(rankings)} Ergebnisse gespeichert "
    f"({uncertain_count} unsicher durch Konsens). "
    f"{OWN_DOMAIN}: Position {own_position} | "
    f"/serponado/: Position {own_url_data['position']}{stale_note}"
)
