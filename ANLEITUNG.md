# Serponado Ranking Tracker – Komplette Anleitung

## Was das System macht
- GitHub Action läuft täglich automatisch um 11:00 Uhr (DE-Zeit)
- Ruft Google-Rankings für "Serponado" via DataForSEO ab
- Speichert Top 50 als `rankings.json` im Repo
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
4. Nach ~30 Sekunden sollte `public/rankings.json` mit echten Daten gefüllt sein

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
| DataForSEO (1x täglich, 21 Tage) | ~$0.05 gesamt |

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
→ In `fetch-rankings.yml`: `cron: '0 9 * * *'` = 11:00 Uhr MEZ / `0 8 * * *` = 11:00 Uhr MESZ (Sommerzeit)
→ Aktuell (Juni) ist MESZ aktiv → `0 9 * * *` ist korrekt
