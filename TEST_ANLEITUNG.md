# TEST_ANLEITUNG — Sanhedrin lokal starten, migrieren, testen, pushen

**Stand:** 06.07.2026  
**Branch-Kontext:** `qa-full-test-2026-07-06` auf Basis von `qa-frontend-categories-2026-07-06`.

Diese Anleitung beschreibt den sicheren lokalen Gesamttest der neuen Q&A-Struktur mit Chunks, Index, Kategorien, Suche, Detailseiten und Uploads.

## 1. Voraussetzungen

Benötigt:

- Git
- Python 3.10 oder neuer
- Node.js 18 oder neuer, empfohlen Node 22
- Browser mit Entwicklerkonsole, zum Beispiel Chrome, Edge oder Firefox

Optional, aber empfohlen:

- GitHub Desktop für Commit/Push
- ein frischer Test-Branch statt direktem Arbeiten auf `main`

## 2. Projekt lokal starten

```bash
git clone https://github.com/Moriahise/Sanhedrin.git
cd Sanhedrin
```

Wenn du einen Test-Branch prüfen willst:

```bash
git fetch origin
git checkout qa-full-test-2026-07-06
```

Dann den statischen Server starten:

```bash
python3 -m http.server 8000
```

Im Browser öffnen:

```text
http://localhost:8000/
http://localhost:8000/qa.html?id=<ID>
```

Wichtig: Das Projekt ist statisch. Es braucht keinen Backend-Server. GitHub Pages verhält sich im Kern wie dieser lokale HTTP-Server.

## 3. Migration ausführen

Vor der Migration einen Sicherheitsanker setzen:

```bash
git status
git tag vor-migration-$(date +%F)
```

Plan anzeigen, ohne etwas zu verändern:

```bash
python3 migrate_production.py
```

Produktive, aber nicht-destruktive Migration ausführen:

```bash
python3 migrate_production.py --run
```

Erwartet:

- Backup unter `_backup_before_question_migration/<zeitstempel>/`
- neue Struktur unter `data/questions/`
- Report `migration_report.md`
- Originaldateien bleiben liegen
- alte Links bleiben über Fallback/Aliases nutzbar

Nicht committen:

```text
_backup_before_question_migration/
```

Falls noch nicht vorhanden, in `.gitignore` eintragen:

```bash
echo "_backup_before_question_migration/" >> .gitignore
```

## 4. Migration prüfen

Nach der Migration:

```bash
python3 validate_migration.py . data/questions migration_report.md
```

Zusätzlich die Store-Konsistenz prüfen:

```bash
python3 add_qa_upload.py --verify
```

Wichtige Dateien prüfen:

```bash
python3 - <<'EOF'
import json
from collections import Counter
base = "data/questions"
idx = json.load(open(f"{base}/index.json", encoding="utf-8"))
print("Index count:", idx["count"])
print("Entries:", len(idx["entries"]))
print("Kategorien:", Counter(e["c"] for e in idx["entries"]))
print("needs_review:", sum(1 for e in idx["entries"] if e.get("r")))
print("Chunks:", json.load(open(f"{base}/manifest.json", encoding="utf-8")).get("chunks"))
EOF
```

Erwartung:

- `index.json` count stimmt mit Entries überein
- keine doppelten IDs
- alle Chunk-Verweise zeigen auf existierende Chunks
- Summe der `by-category/*.json` Einträge entspricht dem Index
- `needs_review` ist sichtbar, aber kein Fehler

## 5. Neue Fragen hochladen

Einzelne Frage:

```bash
python3 add_qa_upload.py \
  --title "Titel der Frage" \
  --question "Volltext der Frage" \
  --answer "Antwort 1" \
  --answer "Antwort 2" \
  --tags shabbat,muktzeh \
  --date 2026-07-06
```

Mit expliziter Kategorie:

```bash
python3 add_qa_upload.py \
  --title "Titel" \
  --question "Frage" \
  --answer "Antwort" \
  --category halacha
```

Gebündelt aus JSON:

```bash
python3 add_qa_upload.py --json neue_fragen.json
```

Danach immer prüfen:

```bash
python3 add_qa_upload.py --verify
```

Erwartung:

- neue ID, zum Beispiel `up-2026-0001`
- Speicherung in `data/questions/chunks/qa_....json`
- `index.json` count steigt
- passende `by-category/<category>.json` wird aktualisiert
- `aliases.json` wird aktualisiert
- bei Unsicherheit erscheint `needs_review`
- `responsa.json` wird nicht erweitert

## 6. Kategorie-Filter prüfen

Lokale Startseite öffnen:

```text
http://localhost:8000/
```

Prüfen:

- Dropdown „Alle Kategorien“ zeigt Kategorien
- Kategorie-Chips oberhalb der Karten werden angezeigt
- Klick auf einen Chip filtert die Karten
- Dropdown und Chip bleiben synchron
- Zähler pro Kategorie stimmen grob mit `index.json` überein
- `needs_review` wird dezent als Review/בדיקה angezeigt
- Gruppierung „Group by category“ zeigt Überschriften pro Kategorie

Technisch prüfen:

```bash
python3 - <<'EOF'
import json, glob
idx = json.load(open("data/questions/index.json", encoding="utf-8"))["entries"]
by_sum = 0
for f in glob.glob("data/questions/by-category/*.json"):
    d = json.load(open(f, encoding="utf-8"))
    by_sum += d.get("count", 0)
    print(f, d.get("count", 0))
print("Index:", len(idx), "by-category Summe:", by_sum)
EOF
```

## 7. Suche prüfen

Auf der Startseite prüfen:

- Titel, zum Beispiel ein bekannter englischer Titel
- deutsche Begriffe mit Umlauten
- hebräische Begriffe
- Antwortbegriffe
- Schlagwörter/Tags
- Kategorie + Suchtext kombiniert
- neue ID, zum Beispiel `my-...`, `ye-...`, `up-...`
- alte nackte ID, sofern Alias vorhanden

Automatische Tests, falls vorhanden:

```bash
python3 -m http.server 8128
node test_search.mjs
```

Bei Port-Konflikt anderen Server beenden oder Testdatei/Port anpassen.

## 8. Detailseiten prüfen

Beispiele:

```text
http://localhost:8000/qa.html?id=my-1001
http://localhost:8000/qa.html?id=ye-555
http://localhost:8000/qa.html?id=up-2026-0001
```

Prüfen:

- Titel lädt
- Frage lädt
- alle Antworten laden
- Quelle/Link bleibt klickbar, falls vorhanden
- Hebräisch, Deutsch, Englisch und Sonderzeichen werden nicht zerstört
- alte Links mit `?id=...&src=...` funktionieren weiter, wenn Legacy-Daten vorhanden sind

## 9. Fehler erkennen

Browser-Konsole öffnen: F12 → Console.

Kritisch:

- rote JavaScript-Fehler
- 404 auf `qa-data.js`
- 404 auf `data/questions/index.json`, wenn die neue Struktur erwartet wird
- 404 auf Chunk-Dateien
- JSON parse errors

Nicht kritisch:

```text
[qa-data] Neue Struktur nicht gefunden — Fallback auf alte Datenstruktur.
```

Das ist nur ein Hinweis, solange `data/questions/` noch nicht existiert.

HTTP-Schnelltest:

```bash
curl -I http://localhost:8000/
curl -I http://localhost:8000/qa.html
curl -I http://localhost:8000/data/questions/index.json
```

## 10. Gesamtergebnis nach GitHub pushen

Vor dem Commit:

```bash
git status
```

Nicht committen:

```text
_backup_before_question_migration/
__pycache__/
*.tmp
```

Typischer Commit:

```bash
git add .gitignore data/questions qa-data.js qa_store.py add_qa_upload.py \
        migrate_qa.py migrate_production.py validate_migration.py \
        index.html script.js qa-categories.css \
        TEST_ANLEITUNG.md TEST_REPORT.md migration_report.md

git commit -m "Test Q&A chunks, categories, search and uploads"
git push origin <branch-name>
```

Empfehlung: erst Branch testen, dann Pull Request oder kontrollierter Merge nach `main`.

## 11. Rollback

Wenn etwas schiefgeht:

```bash
git reset --hard vor-migration-YYYY-MM-DD
```

Oder bei bereits gepushtem Commit:

```bash
git revert <commit-sha>
```

Die Originaldaten bleiben durch die Parallelstruktur und den Backup-Ordner zusätzlich geschützt.
