# KLASSIFIZIERUNG_ALTBESTAND — Fachliche Aufteilung der migrierten Fragen

**Zweck:** Die migrierten Altbestand-Einträge in `data/questions/` fachlich auf `halacha`, `tanach`, `talmud`, `kabbalah`, `history` und `general` aufteilen.

Das ist ein eigener Schritt **nach** der Migration. Die Migration erzeugt die Chunk-Dateien; die Klassifizierung ordnet danach die Einträge fachlich sauberer zu und baut `index.json`, `by-category/` und `aliases.json` neu auf.

## Ablauf

### 1. Report-Modus

```bash
python3 classify_qa.py
```

Dieser Modus schreibt nur `klassifizierungs_report.md` und ändert keine Daten.

### 2. Anwenden

```bash
python3 classify_qa.py --run
```

Dieser Modus:

1. erstellt ein lokales Backup nach `_backup_before_classification/<zeitstempel>/`,
2. klassifiziert die Fragen in den Chunk-Dateien,
3. baut `index.json` neu,
4. baut `by-category/*.json` neu,
5. baut `aliases.json` neu,
6. schreibt `klassifizierungs_report.md`.

## Schutzregeln

Nie automatisch überschrieben werden:

- `category_source: "legacy"`,
- `category_source: "manual"`,
- `category_locked: true`.

Unklare Fälle bleiben ehrlich markiert:

- `category_confidence: "low"`,
- `needs_review: true`.

## GitHub Action

Die Action `Classify questions data` kann manuell gestartet werden. Sie führt aus:

```bash
python3 classify_qa.py --run
```

Danach committed sie nur:

```text
data/questions
klassifizierungs_report.md
```

Backups bleiben lokal im Runner und werden durch `.gitignore` geschützt.

## Nach der Klassifizierung prüfen

Auf GitHub Pages hart neu laden:

```text
Strg + F5
```

Dann prüfen:

- Kategorie-Zähler,
- Suche,
- `needs_review` Markierung,
- Einzelantworten über `qa.html?id=...`.
