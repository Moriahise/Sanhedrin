# UPLOAD_LOGIK — Neue Speicher-Logik für Fragen & Antworten

**Stand:** 06.07.2026  
**Gilt für:** `data/questions/`  
**Kernregel:** Neue Q&A-Einträge werden nicht mehr an `responsa.json` oder eine andere riesige Einzeldatei angehängt. Die alte Struktur bleibt als Fallback liegen, aber neue Q&A-Schreibvorgänge laufen über `qa_store.py`.

## 1. Neue Bausteine

| Datei | Aufgabe |
|---|---|
| `qa_store.py` | Zentrales Schreibmodul für `data/questions/`: Validierung, ID, Kategorie, Chunk-Rollover, Index, by-category, aliases, manifest. |
| `add_qa_upload.py` | CLI für manuelle oder gebündelte Uploads. Nutzt ausschließlich `qa_store.py`. |
| `tools/qa_merge.py` | Bestehender Upload-Weg bleibt erhalten, schreibt aber Q&A jetzt nach `data/questions/` statt nach `responsa.json`. |
| `build_qa.py` | Mi-Yodeya-Import bleibt erhalten, schreibt normalisierte Hilfsdateien weiter, aber Q&A-Zugriffsdaten jetzt nach `data/questions/`. |
| `.github/workflows/qa-build.yml` | CI schreibt und committet nur noch die neue Chunk-Struktur unter `data/questions/`. |

## 2. Wie neue Fragen gespeichert werden

Neue Fragen laufen über:

```bash
python add_qa_upload.py --title "Titel" --question "Frage" --answer "Antwort" --tags shabbat,muktzeh
```

Oder gebündelt:

```bash
python add_qa_upload.py --json neue_fragen.json
```

Ablauf pro Frage:

1. Eingabe validieren.
2. stabile ID erzeugen.
3. Kategorie bestimmen.
4. bei unsicherer Kategorie `needs_review` setzen.
5. in den offenen Chunk schreiben.
6. `index.json` aktualisieren.
7. passende `by-category/<category>.json` aktualisieren.
8. `aliases.json` aktualisieren.
9. `manifest.json` aktualisieren.
10. Konsistenz prüfen.

`responsa.json` wird dabei nicht verändert.

## 3. Validierung

`qa_store.py` lehnt Einträge ab, wenn:

- weder Titel noch Fragetext vorhanden ist,
- bei Direkt-Uploads keine Antwort vorhanden ist,
- die Quelle nicht `upload`, `miyodea` oder `yeshiva` ist,
- ein Datum nicht im Format `YYYY`, `YYYY-MM` oder `YYYY-MM-DD` vorliegt,
- eine explizite Kategorie nicht in `categories.json` existiert.

Wenn Antworten vorhanden sind, aber keine Antwort als `accepted` markiert ist, wird die erste Antwort als akzeptiert markiert. Damit bleibt die bisherige Best-Antwort-Konvention erhalten.

## 4. Wie IDs erzeugt werden

IDs haben das Format:

```text
<präfix>-<source_id>
```

Präfixe:

- `my-` für Mi Yodeya,
- `ye-` für Yeshiva,
- `up-` für direkte Uploads.

Für direkte Uploads ohne externe Quelle erzeugt `qa_store.py` eine ID wie:

```text
up-2026-0001
up-2026-0002
```

Die laufende Nummer steht im `upload_counter` in `manifest.json`. Sie wird nur hochgezählt und nicht wiederverwendet.

Zusätzlich wird jede nackte Quell-ID in `aliases.json` gespeichert, damit alte oder kurze Links weiterhin auflösbar bleiben.

## 5. Wie Kategorien zugeordnet werden

Reihenfolge:

1. explizite Kategorie aus dem Upload,
2. automatische Klassifikation über Tags, Titel und Fragetext,
3. Fallback `general`.

Wenn eine Kategorie explizit angegeben wird, gilt sie als `high` und bekommt kein `needs_review`.

Wenn keine Kategorie angegeben wird, nutzt `qa_store.py` dieselbe Klassifikationslogik wie die Migration aus `migrate_qa.py`. Dadurch haben Migration und neue Uploads eine gemeinsame Quelle der Wahrheit.

Unsichere Fälle erhalten:

```json
"category_confidence": "low",
"needs_review": true
```

`categories.json` wird dabei nicht überschrieben. Sie wird nur gelesen. Falls ein ganz neuer Store ohne `categories.json` erzeugt wird, legt `qa_store.py` einmalig die Standardkategorien aus `migrate_qa.py` an.

## 6. Wie Chunks erweitert werden

Die Limits stehen in `data/questions/manifest.json`:

```json
"max_per_chunk": 500,
"max_chunk_bytes": 1500000
```

Geschrieben wird immer in den offenen Chunk aus:

```json
"open_chunk": 4
```

Wenn der Chunk voll ist, wird automatisch der nächste Chunk erzeugt:

```text
qa_0004.json
qa_0005.json
qa_0006.json
```

Geschlossene Chunks werden nicht umsortiert. Dadurch bleiben bestehende IDs und Chunk-Verweise stabil.

## 7. Wie der Index aktualisiert wird

Für jede neue Frage wird genau ein kompakter Eintrag an `index.json` angehängt.

Der Indexeintrag enthält unter anderem:

```json
{
  "id": "up-2026-0001",
  "t_he": "",
  "t_en": "Title",
  "x": "Frage-Auszug",
  "ax": "Antwort-Auszug",
  "tg": ["tag"],
  "c": "halacha",
  "y": 2026,
  "ch": 4,
  "s": "upload"
}
```

Bei Review-Fällen kommt hinzu:

```json
"r": 1
```

Derselbe kompakte Eintrag wird zusätzlich in `by-category/<category>.json` geschrieben. Die Suche über `qa-data.js` kann dadurch weiterhin über den kompakten Index und die kleinen Kategorie-Dateien arbeiten.

## 8. Atomare Schreibweise

`qa_store.py` schreibt JSON-Dateien atomar:

1. temporäre Datei im Zielordner schreiben,
2. danach per Rename ersetzen.

Dadurch wird verhindert, dass ein abgebrochener Upload halbe JSON-Dateien hinterlässt.

## 9. Konsistenzprüfung

Nach Uploads kann geprüft werden:

```bash
python add_qa_upload.py --verify
```

Geprüft wird:

- eindeutige IDs,
- Index zeigt auf existierende Chunks,
- Chunk-Limits werden eingehalten,
- Kategorien sind gültig,
- `by-category` ist eine vollständige Partition,
- Index und Chunks enthalten dieselbe ID-Menge.

## 10. Bestehende Upload-Wege

Bestehende Skripte werden nicht entfernt.

- `tools/qa_merge.py` bleibt der Upload-Merge-Weg für `data/qa/*.json`, schreibt aber jetzt in `data/questions/`.
- `build_qa.py` bleibt der Mi-Yodeya-Import, schreibt aber Q&A-Zugriffsdaten ebenfalls in `data/questions/`.
- `responsa.json` bleibt für Altbestand und Fallback bestehen, wird von diesen Q&A-Upload-Wegen aber nicht mehr erweitert.

## 11. GitHub Actions

Der Workflow `.github/workflows/qa-build.yml` wurde so angepasst, dass er:

1. `tools/qa_merge.py` ausführt,
2. `python add_qa_upload.py --verify` ausführt,
3. nur `data/questions/` committet,
4. `responsa.json` und `qa_db.json` nicht mehr als Q&A-Ziel committet.

## 12. Beispiel

```bash
python add_qa_upload.py \
  --title "Can one move a candle on Shabbat?" \
  --question "Is it permitted to move a candle on Shabbat when it is needed for space?" \
  --answer "This depends on muktzeh rules and the exact case." \
  --tags shabbat,muktzeh \
  --date 2026-07-06
```

Mögliche Ausgabe:

```text
OK  up-2026-0001 -> qa_0004.json  Kategorie: halacha (high)
Konsistenzprüfung nach Upload: OK
```
