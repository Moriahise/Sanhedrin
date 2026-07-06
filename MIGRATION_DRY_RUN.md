# MIGRATION_DRY_RUN — Anleitung für den Migrations-Probelauf

**Status:** Nur Dry Run. Keine produktive Migration.

Der Probelauf liest die bestehenden Frage-Antwort-Daten nur lesend und schreibt ausschließlich in diesen Testordner:

```text
_migration_test_output/
```

Bestehende Originaldaten werden nicht überschrieben. Die neue produktive Struktur unter `data/questions/` wird in diesem Schritt noch nicht angelegt.

## 1. Dateien

Für den Dry Run werden diese Dateien benötigt:

```text
migrate_qa.py
validate_migration.py
MIGRATION_DRY_RUN.md
```

Der Bericht wird beim Lauf automatisch hier geschrieben:

```text
_migration_test_output/migration_report.md
```

## 2. Starten

Im Wurzelverzeichnis des Repositories ausführen:

```bash
python3 migrate_qa.py
```

Mit Backup-Kopie der Originaldaten im Testordner:

```bash
python3 migrate_qa.py --backup
```

Mit kleinen Test-Chunks, um die Aufteilung sichtbar zu prüfen:

```bash
python3 migrate_qa.py --max-per-chunk 4
```

Danach die Ausgabe prüfen:

```bash
python3 validate_migration.py .
```

## 3. Welche Dateien erzeugt werden

```text
_migration_test_output/
├── migration_report.md
├── _backup_originals/              # nur bei --backup
└── data/questions/
    ├── manifest.json
    ├── index.json
    ├── categories.json
    ├── aliases.json
    ├── chunks/
    │   ├── qa_0001.json
    │   ├── qa_0002.json
    │   └── ...
    └── by-category/
        ├── halacha.json
        ├── tanach.json
        ├── talmud.json
        ├── kabbalah.json
        ├── history.json
        └── general.json
```

## 4. Prüfung

Der wichtigste Prüfpunkt ist der Bericht:

```text
_migration_test_output/migration_report.md
```

Darin müssen stehen:

- Anzahl gelesener Quellen
- Anzahl eindeutiger Fragen
- Anzahl erzeugter Chunks
- Anzahl erkannter Kategorien
- Anzahl `needs_review`
- Hinweis, dass nur `_migration_test_output/` beschrieben wurde

Zusätzlich prüft `validate_migration.py`:

- jede ID ist eindeutig
- jeder Indexeintrag zeigt auf einen vorhandenen Chunk
- jede Chunk-ID existiert auch im Index
- jede Kategorie existiert in `categories.json`
- jede `by-category`-Datei enthält nur ihre Kategorie
- unsichere Kategorien tragen `needs_review`

## 5. IDs prüfen

Neue IDs folgen dieser Logik:

```text
my-<id>   MiYodeya
ye-<id>   Yeshiva
up-<id>   spätere Direkt-Uploads
```

Alte IDs bleiben in `legacy` und `aliases.json` erhalten.

Stichprobe:

```bash
python3 -m json.tool _migration_test_output/data/questions/aliases.json | head -80
```

## 6. Kategorien prüfen

Sichere Kategorien haben:

```json
"category_confidence": "high"
```

Unsichere Kategorien haben:

```json
"category_confidence": "low",
"needs_review": true
```

Unklare Fragen dürfen nicht blind falsch zugeordnet werden. Sie landen in `general` und bekommen `needs_review`.

## 7. Korrekte Migration erkennen

Eine korrekte Dry-Run-Ausgabe erfüllt diese Punkte:

1. `migration_report.md` meldet keine Fehler.
2. `validate_migration.py` meldet keine Fehler.
3. Die Anzahl der Indexeinträge entspricht der Summe der Chunk-Einträge.
4. Die Summe der `by-category`-Einträge entspricht der Gesamtzahl.
5. Alte IDs sind über `aliases.json` auffindbar.
6. Mehrfachantworten bleiben als `answers[]` erhalten.

## 8. Was jetzt noch nicht gemacht wird

- keine produktive Migration
- keine Änderung an `responsa.json`
- keine Änderung an `qa_db/`
- keine Änderung an `miyodea/qa/`
- keine Frontend-Umstellung
- kein Schreiben nach `data/questions/` im echten Projekt
