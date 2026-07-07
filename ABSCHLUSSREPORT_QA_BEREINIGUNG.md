# ABSCHLUSSREPORT_QA_BEREINIGUNG

**Stand:** 06.07.2026  
**Repository:** `Moriahise/Sanhedrin`  
**Status:** Migration, Klassifizierung und Qualitätsbereinigung wurden durchgeführt.

## 1. Aktueller Gesamtstand

Die neue Q&A-Struktur ist aktiv:

```text
data/questions/
├── manifest.json
├── index.json
├── categories.json
├── aliases.json
├── chunks/
│   ├── qa_0001.json
│   ├── qa_0002.json
│   └── ...
└── by-category/
    ├── general.json
    ├── halacha.json
    ├── tanach.json
    ├── talmud.json
    ├── history.json
    └── kabbalah.json
```

`responsa.json` bleibt als Altbestand/Fallback bestehen, wird aber für neue Uploads nicht mehr erweitert.

## 2. Migration

Die Migration hat `data/questions/` erzeugt. Danach waren vorhanden:

- `manifest.json`
- `index.json`
- `categories.json`
- `aliases.json`
- Chunk-Dateien unter `data/questions/chunks/`
- Kategorie-Dateien unter `data/questions/by-category/`

Die neue Struktur ist chunked. Dadurch entstehen keine riesigen Einzeldateien mehr.

Aktuelle Chunk-Grenzen:

- maximal 500 Fragen pro Chunk
- maximal ca. 1.500.000 Bytes pro Chunk

## 3. Fachliche Klassifizierung

Die fachliche Klassifizierung wurde ausgeführt.

Ergebnis laut `klassifizierungs_report.md`:

- 87.849 Einträge bewertet
- 6 Kategorien geladen
- Backup erstellt
- Index neu aufgebaut
- Konsistenz: OK

Verteilung nach Klassifizierung:

| Kategorie | Anzahl vor Qualitätscleanup |
|---|---:|
| general | 33.453 |
| halacha | 29.811 |
| tanach | 14.132 |
| talmud | 6.651 |
| history | 2.767 |
| kabbalah | 1.035 |

Hinweis: Viele `general` und `needs_review` Fälle bleiben bewusst erhalten, weil unsichere Fälle nicht geraten werden sollen.

## 4. Qualitätsprüfung und Bereinigung

Die Qualitätsprüfung wurde zuerst im Report-Modus durchgeführt und danach bewusst angewendet.

Geprüft wurden:

- komplett leere Fragen
- reine Überschriften ohne Frage und ohne Antwort
- inhaltslose Mini-Fragmente
- echte Duplikate mit identischem normalisiertem Inhalt
- Fragen ohne Antwort
- gleiche Fragen mit unterschiedlichen Antworten

Ergebnis laut `qualitaets_report.md`:

| Prüfung | Ergebnis |
|---|---:|
| LEER | 0 |
| NUR_TITEL | 40 |
| INHALTSLOS | 0 |
| DUPLIKATE entfernt | 40.738 |
| OHNE_ANTWORT | 22.904 nur gemeldet, nicht entfernt |
| GLEICHE_FRAGE mit anderen Antworten | 2 nur gemeldet, nicht entfernt |
| Entfernt gesamt | 40.778 |

Wichtig:

- Entfernt wurden nur sichere Fälle: reine Titel ohne Inhalt und echte Duplikate.
- Fragen ohne Antwort wurden nicht entfernt.
- Gleiche Frage mit verschiedenen Antworten wurde nicht entfernt.
- Vor der Entfernung wurde ein Backup im GitHub-Runner erzeugt.
- Entfernte Einträge wurden in eine Quarantäne-Datei geschrieben.
- Aliase entfernter Duplikate wurden auf die überlebenden Einträge umgeleitet.
- Danach wurde der Index neu aufgebaut.
- Konsistenz: OK.

## 5. Aktueller Bestand nach Bereinigung

Aktueller Stand laut `data/questions/manifest.json`:

| Feld | Wert |
|---|---:|
| schema | 2 |
| total | 47.071 |
| chunks | 201 |
| open_chunk | 201 |
| max_per_chunk | 500 |
| max_chunk_bytes | 1.500.000 |

Der Bestand ist also von 87.849 auf 47.071 Einträge reduziert worden.

## 6. Index und Kategorie-Dateien

Nach Klassifizierung und Qualitätsbereinigung wurden die abgeleiteten Dateien neu aufgebaut:

- `data/questions/index.json`
- `data/questions/aliases.json`
- `data/questions/manifest.json`
- `data/questions/by-category/*.json`

`index.json` und `by-category/` sind abgeleitete Dateien aus den Chunks. Die Chunks sind die Quelle der Wahrheit.

Für spätere manuelle Korrekturen kann erneut ausgeführt werden:

```bash
python3 rebuild_index.py
```

Oder über GitHub Actions:

```text
Actions → Rebuild questions index → Run workflow
```

## 7. Neue Fragen hochladen — Kurzauffrischung

Neue Fragen werden nicht mehr in `responsa.json` geschrieben.

Neue Fragen laufen über:

```bash
python3 add_qa_upload.py
```

### Einzelne Frage mit einer Antwort

```bash
python3 add_qa_upload.py \
  --title "Titel der Frage" \
  --question "Volltext der Frage" \
  --answer "Antworttext" \
  --tags "shabbat,halacha" \
  --date 2026-07-06
```

### Einzelne Frage mit Kategorie

```bash
python3 add_qa_upload.py \
  --title "Darf man ...?" \
  --question "Hier steht die Frage" \
  --answer "Hier steht die Antwort" \
  --category halacha
```

Erlaubte Hauptkategorien:

```text
general
halacha
tanach
talmud
kabbalah
history
```

### Mehrere Antworten

```bash
python3 add_qa_upload.py \
  --title "Frage" \
  --question "Fragetext" \
  --answer "Erste Antwort" \
  --answer "Zweite Antwort"
```

Die erste Antwort gilt als akzeptierte Antwort.

### Upload aus JSON-Datei

```bash
python3 add_qa_upload.py --json neue_fragen.json
```

Beispiel für `neue_fragen.json`:

```json
[
  {
    "title": "Darf man am Schabbat ...?",
    "question": "Vollständiger Fragetext",
    "answers": [
      {"text": "Antworttext", "accepted": true}
    ],
    "tags": ["shabbat", "halacha"],
    "category": "halacha",
    "date": "2026-07-06",
    "source": "upload"
  }
]
```

### Nach jedem Upload prüfen

```bash
python3 add_qa_upload.py --verify
```

Erwartung:

```text
Konsistenzprüfung: OK — keine Probleme
```

## 8. Was beim Upload technisch passiert

Beim Upload passiert automatisch:

1. Validierung von Frage und Antwort.
2. Vergabe einer stabilen ID, zum Beispiel `up-2026-0001`.
3. Automatische oder explizite Kategoriezuordnung.
4. Falls unsicher: `needs_review` wird gesetzt.
5. Speicherung in `data/questions/chunks/qa_....json`.
6. Aktualisierung von `index.json`.
7. Aktualisierung von `by-category/<category>.json`.
8. Aktualisierung von `aliases.json`.
9. Aktualisierung von `manifest.json`.
10. Konsistenzprüfung.

Chunk-Schutz:

- Wenn ein Chunk 500 Fragen erreicht, wird ein neuer Chunk erstellt.
- Wenn ein Chunk ca. 1,5 MB überschreiten würde, wird ebenfalls ein neuer Chunk erstellt.

## 9. GitHub-Workflow für Uploads

Für automatische Upload-Dateien gibt es den Workflow:

```text
QA → data/questions (chunked)
```

Wenn neue JSON-Dateien in `data/qa/` landen, kann der Workflow sie über `tools/qa_merge.py` in die Chunk-Struktur übernehmen.

Manuell kannst du nach einem Upload zusätzlich nutzen:

```text
Actions → Rebuild questions index → Run workflow
```

## 10. Backups und Sicherheit

Backups aus den GitHub-Actions-Runs bleiben im Runner und werden nicht ins Repository gepusht.

Ignoriert werden:

```text
_backup_before_question_migration/
_backup_before_classification/
_backup_before_quality/
_migration_test_output/
__pycache__/
*.pyc
```

Wichtig: Die Quarantäne-Datei der entfernten Einträge wurde im Runner erzeugt, aber nicht ins Repo gepusht. Die Daten wurden aus dem sichtbaren Bestand entfernt, weil sie als sichere Duplikate/reine Titel erkannt wurden.

## 11. Offene Punkte

1. `OHNE_ANTWORT` Fälle prüfen: 22.904 wurden nur gemeldet und bewusst nicht entfernt.
2. `GLEICHE_FRAGE mit anderen Antworten`: 2 Gruppen manuell prüfen.
3. `needs_review` Fälle später nacharbeiten.
4. Kategorie-Regeln können weiter geschärft werden, um `general` zu reduzieren.
5. Nach jeder größeren manuellen Änderung `rebuild_index.py` ausführen.

## 12. Abschlussbewertung

Der Q&A-Bestand ist jetzt professionell migriert, fachlich klassifiziert und qualitätsbereinigt.

Aktueller Zustand:

- Neue Chunk-Struktur aktiv.
- 47.071 Einträge im bereinigten Bestand.
- Duplikate entfernt.
- Titel-ohne-Inhalt entfernt.
- Fragen ohne Antwort nicht entfernt.
- Alte IDs/Duplikat-Aliase wurden umgeleitet.
- Index und Kategorie-Dateien wurden neu aufgebaut.
- Upload neuer Fragen läuft über `add_qa_upload.py` und schreibt nicht mehr in `responsa.json`.
