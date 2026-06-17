# Serponado Ranking Tracker – Komplette Anleitung

## Was das System macht
- GitHub Action läuft alle 30 Minuten automatisch
- Sendet **3 identische Anfragen** an DataForSEO und bildet einen **Mehrheitsentscheid** (2 von 3 müssen übereinstimmen)
- Speichert Top 10 als `rankings.json` im Repo
- WordPress-Seite liest die JSON-Datei und zeigt das Leaderboard

---

## Schritt 1 – GitHub Repo erstellen

1. Gehe zu https://github.com/new
2. Repository-Name: `serponado-tracker`
3. Sichtbarkeit: **Public** (wichtig! sonst kann WordPress die JSON nicht lesen)
4. Klicke **Create repository**

---

## Schritt 2 – Dateien hochladen

Lade folgende Dateien ins Repo (per Drag & Drop auf github.com):

```
.github/
  workflows/
    fetch-rankings.yml
fetch_rankings.py
public/
  rankings.json
```

**Reihenfolge:** Zuerst `public/rankings.json`, dann `fetch_rankings.py`, dann den Ordner `.github/workflows/fetch-rankings.yml`.

> Tipp: Ordner auf GitHub anlegen → beim Dateinamen einfach `ordnername/dateiname.ext` eingeben.

---

## Schritt 3 – API-Keys als Secrets hinterlegen

1. Im Repo auf **Settings** klicken
2. Links: **Secrets and variables → Actions**
3. **New repository secret** – zwei Secrets anlegen:

| Name | Wert |
|------|------|
| `DATAFORSEO_LOGIN` | Deine DataForSEO E-Mail |
| `DATAFORSEO_PASSWORD` | Dein DataForSEO Passwort |

---

## Schritt 4 – Ersten Abruf manuell starten

1. Im Repo auf **Actions** klicken
2. Links: **Fetch Serponado Rankings** auswählen
3. **Run workflow** → **Run workflow** klicken
4. Nach ~60 Sekunden (3 Abfragen à ~15 s) sollte `public/rankings.json` mit echten Daten gefüllt sein

> Prüfen: Repo → `public/rankings.json` anklicken → Rankings sichtbar?

---

## Schritt 5 – WordPress Widget einbinden

1. Öffne `wordpress-widget.html` aus diesem Repo
2. Passe diese zwei Zeilen an:
   ```javascript
   const GITHUB_USER  = 'DEIN-GITHUB-USERNAME';  // ← anpassen
   const EIGENE_DOMAIN = 'optimerch.de';          // ← eure Domain
   ```
3. In WordPress: Seite bearbeiten → Block **"Benutzerdefiniertes HTML"** hinzufügen
4. Gesamten Code aus `wordpress-widget.html` einfügen
5. Speichern & veröffentlichen

---

## Ergebnis

Das Widget zeigt:
- 🥇🥈🥉 Medaillen für Top 3
- ⭐ Eure eigene Domain farblich hervorgehoben
- Klickbare URLs zu jeder Seite
- Zeitstempel des letzten Updates

---

## Kosten

| Was | Kosten |
|-----|--------|
| GitHub Actions | kostenlos |
| DataForSEO (3 Calls/30 min, depth=10) | ~$0.60/Monat* |

*DataForSEO berechnet Live Advanced pauschal pro Task-Call, nicht nach depth. 3 Calls × 48 Läufe/Tag × 30 Tage = 4.320 Calls/Monat. Aktueller Preis Live Advanced: ~$0,00012–$0,00015 pro Call → ca. $0.50–$0.65/Monat.

---

## Troubleshooting

**Action schlägt fehl?**
→ Settings → Actions → Logs prüfen

**JSON leer / keine Rankings?**
→ DataForSEO Secrets korrekt? → `DATAFORSEO_LOGIN` und `DATAFORSEO_PASSWORD` prüfen

**Widget lädt nicht in WordPress?**
→ GitHub-Username in `wordpress-widget.html` korrekt eingetragen?
→ Repo ist **Public**?

**Zeitzone falsch?**
→ System läuft dauerhaft alle 30 Minuten (UTC-Cron), Zeitstempel werden in Berlin-Zeit gespeichert

**`uncertain: true` bei einer Domain – was bedeutet das?**
→ Alle 3 DataForSEO-Abfragen haben für diese Domain unterschiedliche Positionen zurückgegeben
→ Das System hat stattdessen den letzten bekannten stabilen Wert aus der vorherigen `rankings.json` beibehalten
→ Bei Häufung: unter **Actions → Artifacts** die `rankings-log-*.db`-Datei herunterladen und mit einem SQLite-Viewer (z. B. DB Browser for SQLite) die 3 Rohwerte vergleichen

**Diagnose-Log / Nachweis für Contest-Veranstalter**
→ Jeder der 3 API-Requests pro Lauf wird in `rankings_log.db` gespeichert (Felder: `ts`, `run_num`, `check_url`, `results_json`)
→ Die DB ist **nicht im Repo** (würde als Binary-Commit anfallen), sondern wird unter **Actions → [Run auswählen] → Artifacts → rankings-log-[Run-ID]** für 90 Tage als Download bereitgestellt
→ Inhalt zeigt: Zeitstempel, welcher Proxy/Datacenter (`check_url`) und vollständige Top-10-Rohdaten pro Request
