# NEUE_DATENSTRUKTUR — Geplante Frage-Antwort-Struktur für Moriahise/Sanhedrin

**Stand:** 06.07.2026 · **Reiner Plan — keine Migration ausgeführt, keine bestehenden Daten verändert.**
Basis: ARCHITEKTUR_ANALYSE.md und DATENSTRUKTUR_ANALYSE.md. Ausgelegt auf **viele tausend bis zehntausende Fragen** bei statischem Hosting auf GitHub Pages, ohne Backend. Alle Dateien müssen direkt per `fetch()` ladbar bleiben.

---

## 1. Zielstruktur

```text
data/
└── questions/
    ├── manifest.json              # kleines Steuerfile: Schema, Zähler, offener Chunk, Indexdateien
    ├── index.json                 # zentraler kompakter Suchindex, keine Volltexte
    ├── categories.json            # Kategorie-Definitionen und Tag-/Alt-Kategorie-Mapping
    ├── aliases.json               # alte IDs, alte number-Werte und alte src-Links -> neue ID/Chunk
    ├── chunks/                    # Volltexte: Frage + alle Antworten
    │   ├── qa_0001.json
    │   ├── qa_0002.json
    │   ├── qa_0003.json
    │   └── ...
    └── by-category/               # kompakte Indexlisten pro Kategorie, keine Volltexte
        ├── halacha.json
        ├── tanach.json
        ├── talmud.json
        ├── kabbalah.json
        ├── history.json
        └── general.json
```

Diese Struktur ist absichtlich nah an der bestehenden statischen Website. Sie benötigt keinen Server und keine Datenbank. `index.html`, `script.js` und `qa.html` können später schrittweise auf diese Dateien umgestellt werden.

Wichtige Anpassungen gegenüber der Skizze:

1. **`manifest.json` wird ergänzt.** Das Frontend und spätere Upload-Skripte brauchen eine kleine Datei, die sagt, welche Indexdateien existieren, welcher Chunk offen ist und welche Schema-Version gilt.
2. **`aliases.json` wird ergänzt.** Dadurch bleiben alte Links und alte IDs möglichst erhalten.
3. **`by-category/` enthält keine Volltexte.** Dort liegen nur kompakte Indexdatensätze. Die eigentlichen Fragen und Antworten bleiben ausschließlich in `chunks/`.

---

## 2. Beschreibung jeder Datei

| Datei | Inhalt | Zweck | Zielgröße |
|---|---|---|---|
| `manifest.json` | Schema-Version, Gesamtzahl, Anzahl Chunks, offener Chunk, Indexdateien, Zeitstempel | schneller Einstieg für Frontend und Upload-Skripte | < 5 KB |
| `index.json` | ein kompakter Suchdatensatz pro Frage | schnelle Suche ohne Volltexte | möglichst < 2 MB; später shardbar |
| `categories.json` | Kategorien, Labels, alte Kategorie-Zuordnung, Tag-Mapping | zentrale Kategorie-Logik | < 10 KB |
| `aliases.json` | alte IDs/Nummern/Pfade -> neue ID und Chunk | Link-Kompatibilität | wächst nur bei Migration |
| `chunks/qa_0001.json` usw. | Volltexte: Frage + alle Antworten + Metadaten | Detailansicht lädt nur einen Chunk | max. 500 Fragen und max. ca. 1,5 MB |
| `by-category/*.json` | Indexdatensätze pro Kategorie | schneller Kategorie-Filter | abhängig von Kategorie, klein halten |

---

## 3. `manifest.json`

Beispiel:

```json
{
  "schema": 2,
  "generated": "2026-07-06T12:00:00Z",
  "total": 23450,
  "chunks": 47,
  "open_chunk": 47,
  "max_per_chunk": 500,
  "max_chunk_bytes": 1500000,
  "index_files": ["index.json"],
  "category_files": [
    "by-category/halacha.json",
    "by-category/tanach.json",
    "by-category/talmud.json",
    "by-category/kabbalah.json",
    "by-category/history.json",
    "by-category/general.json"
  ]
}
```

Regeln:

- `schema` erhöht sich nur bei inkompatiblen Strukturänderungen.
- `open_chunk` zeigt auf den einzigen Chunk, der neue Fragen aufnehmen darf.
- `index_files` erlaubt spätere Aufteilung des Index, ohne das Frontend neu zu erfinden.
- `max_per_chunk` und `max_chunk_bytes` sind verbindliche Schreibregeln.

---

## 4. Beispiel für einen Frage-Antwort-Eintrag

Datei: `data/questions/chunks/qa_0001.json`

```json
{
  "schema": 2,
  "chunk": 1,
  "count": 1,
  "questions": [
    {
      "id": "my-12345",
      "legacy": {
        "source_id": "miyodeya_12345",
        "number": 12345,
        "src": "miyodea/qa/2026-01-01-mi_yodeya_knowledge.json",
        "old_file": "qa.html?id=miyodeya_12345&src=miyodea/qa/2026-01-01-mi_yodeya_knowledge.json"
      },
      "source": "miyodea",
      "category": "halacha",
      "category_confidence": "high",
      "needs_review": false,
      "title_he": "",
      "title_en": "May one move a wallet on Shabbat?",
      "question": "Full question text ...",
      "answers": [
        {
          "text": "Full accepted answer ...",
          "accepted": true,
          "author": null,
          "score": 7
        },
        {
          "text": "Full second answer ...",
          "accepted": false,
          "author": null,
          "score": 2
        }
      ],
      "url": "https://judaism.stackexchange.com/questions/12345/...",
      "tags": ["shabbat", "muktzeh"],
      "lang": "en",
      "date": "2019-03-14",
      "year": 2019
    }
  ]
}
```

Pflichtfelder im Chunk:

| Feld | Pflicht | Erklärung |
|---|---:|---|
| `id` | ja | stabile globale ID |
| `source` | ja | `miyodea`, `yeshiva`, `upload` |
| `category` | ja | Kategorie-ID aus `categories.json` |
| `title_he` / `title_en` | ja | mindestens eines darf nicht leer sein |
| `question` | ja | Volltext der Frage |
| `answers` | ja | Liste aller Antworten, nicht nur eine Antwort |
| `url` | nein | Quelllink, falls vorhanden |
| `tags` | ja | Liste, notfalls leer |
| `date` / `year` | ja | Datum/Jahr soweit rekonstruierbar |
| `legacy` | nein, aber bei Migration ja | alte IDs und alte Links |

Wichtig: `answers` ist immer eine Liste. Damit gehen mehrere MiYodea-Antworten nicht mehr verloren.

---

## 5. Stabile IDs

Regel:

```text
<quellpräfix>-<quell-id>
```

| Quelle | Präfix | Beispiel |
|---|---|---|
| MiYodea | `my` | `my-154636` |
| Yeshiva | `ye` | `ye-149283` |
| Direkt-Upload | `up` | `up-2026-0001` |

Regeln:

1. Eine ID wird nach Veröffentlichung nie geändert.
2. Ein Eintrag wechselt nie den Chunk.
3. Alte IDs bleiben in `legacy` und `aliases.json` erhalten.
4. Bei MiYodea wird aus `miyodeya_154636` die neue ID `my-154636`.
5. Bei Yeshiva wird aus `149283` die neue ID `ye-149283`.
6. Bei Direkt-Uploads erzeugt das Schreibmodul die nächste freie `up-<jahr>-<laufnr>`-ID.

---

## 6. Beispiel für `index.json`

```json
{
  "schema": 2,
  "generated": "2026-07-06T12:00:00Z",
  "count": 2,
  "entries": [
    {
      "id": "my-12345",
      "t_he": "",
      "t_en": "May one move a wallet on Shabbat?",
      "x": "Short question excerpt, around 160 characters ...",
      "ax": "Short accepted-answer excerpt, around 160 characters ...",
      "tg": ["shabbat", "muktzeh"],
      "c": "halacha",
      "y": 2019,
      "ch": 1,
      "s": "miyodea"
    },
    {
      "id": "ye-149283",
      "t_he": "יהדות, שיעורים, זמנים",
      "t_en": "",
      "x": "תקציר השאלה ...",
      "ax": "תקציר התשובה ...",
      "tg": [],
      "c": "general",
      "y": 2026,
      "ch": 2,
      "s": "yeshiva",
      "r": 1
    }
  ]
}
```

Kurzschlüssel:

| Schlüssel | Bedeutung |
|---|---|
| `id` | stabile neue ID |
| `t_he` | hebräischer Titel |
| `t_en` | englischer/deutscher Titel |
| `x` | kurzer Frageauszug |
| `ax` | kurzer Antwortauszug |
| `tg` | Tags |
| `c` | Kategorie |
| `y` | Jahr |
| `ch` | Chunknummer |
| `s` | Quelle |
| `r` | optional: needs review |

Warum Kurzschlüssel: Bei zehntausenden Einträgen wird der Index deutlich kleiner. Der Index bleibt schnell ladbar und suchbar.

Suchregel:

- Standardsuche läuft über `index.json`.
- Durchsucht werden Titel, Frageauszug, Antwortauszug, Tags und ID.
- Volltextsuche kann später optional Chunks lazy laden, aber nicht beim normalen Start.

---

## 7. Beispiel für `categories.json`

```json
{
  "schema": 2,
  "default_category": "general",
  "categories": [
    { "id": "halacha", "label_he": "הלכה", "label_en": "Halacha", "label_de": "Halacha", "order": 1 },
    { "id": "tanach", "label_he": "תנ\"ך", "label_en": "Tanakh", "label_de": "Tanach", "order": 2 },
    { "id": "talmud", "label_he": "תלמוד", "label_en": "Talmud", "label_de": "Talmud", "order": 3 },
    { "id": "kabbalah", "label_he": "קבלה", "label_en": "Kabbalah", "label_de": "Kabbala", "order": 4 },
    { "id": "history", "label_he": "היסטוריה", "label_en": "History", "label_de": "Geschichte", "order": 5 },
    { "id": "general", "label_he": "כללי", "label_en": "General", "label_de": "Allgemein", "order": 6 }
  ],
  "legacy_map": {
    "ritual": "halacha",
    "civil": "halacha",
    "family": "halacha",
    "kashrut": "halacha",
    "shabbat": "halacha",
    "conversion": "halacha",
    "halacha-history": "history",
    "other": "general",
    "Q&A": "general"
  },
  "tag_map": {
    "halacha": "halacha",
    "shabbat": "halacha",
    "kashrut": "halacha",
    "muktzeh": "halacha",
    "tefillah-betzibbur": "halacha",
    "tanakh": "tanach",
    "torah-reading": "tanach",
    "parashat-hashavua": "tanach",
    "gemara": "talmud",
    "talmud": "talmud",
    "mishna": "talmud",
    "zohar": "kabbalah",
    "kabbalah": "kabbalah",
    "chassidut": "kabbalah",
    "jewish-history": "history",
    "history": "history",
    "temple": "history"
  }
}
```

Regeln:

1. `categories.json` ist die einzige Quelle für Kategorie-IDs.
2. UI-Filter werden später aus dieser Datei erzeugt.
3. `legacy_map` übersetzt alte Kategorien aus `index.html`/`responsa.json`.
4. `tag_map` übersetzt Tags beim Import.
5. Wenn keine Regel greift: `general` plus `needs_review: true`.

---

## 8. Beispiel für `by-category/halacha.json`

```json
{
  "schema": 2,
  "category": "halacha",
  "count": 1,
  "entries": [
    {
      "id": "my-12345",
      "t_he": "",
      "t_en": "May one move a wallet on Shabbat?",
      "x": "Short question excerpt ...",
      "ax": "Short accepted-answer excerpt ...",
      "tg": ["shabbat", "muktzeh"],
      "c": "halacha",
      "y": 2019,
      "ch": 1,
      "s": "miyodea"
    }
  ]
}
```

Regeln:

- Das Format ist identisch mit `index.json`.
- Es enthält keine Volltexte.
- Quelle der Wahrheit bleibt der Chunk.
- Die Datei wird automatisch aus `index.json` oder aus den Chunks generiert.

---

## 9. `aliases.json`

Beispiel:

```json
{
  "schema": 2,
  "aliases": {
    "miyodeya_12345": { "id": "my-12345", "ch": 1 },
    "12345": { "id": "my-12345", "ch": 1 },
    "n12345": { "id": "my-12345", "ch": 1 },
    "qa.html?id=miyodeya_12345&src=miyodea/qa/example.json": { "id": "my-12345", "ch": 1 }
  }
}
```

Zweck:

- Alte Links sollen weiter funktionieren.
- Alte `number`-Werte sollen auflösbar bleiben.
- Alte `source_id`-Werte sollen auflösbar bleiben.
- Alte `src`-Pfade sollen auflösbar bleiben.

---

## 10. Regeln für Chunk-Größe

Standard:

```text
max_per_chunk = 500 Fragen
max_chunk_bytes = 1.500.000 Bytes
```

Ein Chunk wird geschlossen, sobald eine der beiden Grenzen erreicht ist.

Regeln:

1. Nur der im Manifest genannte `open_chunk` darf neue Einträge bekommen.
2. Geschlossene Chunks werden nicht umsortiert.
3. Ein Eintrag bleibt dauerhaft in seinem ursprünglichen Chunk.
4. Korrekturen ändern nur den betroffenen Chunk und die abgeleiteten Indexdateien.
5. Der Dateiname ist vierstellig: `qa_0001.json`, `qa_0002.json`, usw.
6. 500 Fragen pro Datei ist der sichere Standard. Falls die durchschnittlichen Antworten sehr kurz sind, kann später 1000 geprüft werden, aber nicht als Startwert.

Begründung:

- kleine Git-Diffs,
- schnelle Detailansicht,
- keine riesige Einzeldatei,
- einfache Wiederherstellung,
- stabile Links.

---

## 11. Regeln für neue Uploads

Neue Uploads sollen später nicht mehr direkt in `responsa.json` schreiben.

Geplanter Schreibablauf:

1. Eingabe validieren.
2. stabile ID erzeugen.
3. Duplikatprüfung gegen Index und Aliases.
4. Kategorie bestimmen.
5. Frage in offenen Chunk schreiben.
6. Kompakten Indexeintrag erzeugen.
7. `index.json` aktualisieren.
8. passende `by-category/<category>.json` aktualisieren.
9. `aliases.json` aktualisieren.
10. `manifest.json` aktualisieren.
11. Konsistenzprüfung ausführen.
12. alles gemeinsam committen.

Geplantes zentrales Modul:

```text
scripts/qa_store.py
```

Dieses Modul soll die einzige Schreibstelle werden. Dadurch schreiben `build_qa.py`, künftige Uploads und künftige Importer nicht mehr unterschiedlich.

Atomarität:

- zuerst Temp-Datei schreiben,
- dann Rename,
- erst nach erfolgreicher Validierung committen.

---

## 12. Validierungsregeln

Vor jedem Commit muss geprüft werden:

1. Jede ID ist eindeutig.
2. Jeder Indexeintrag zeigt auf einen existierenden Chunk.
3. Die ID aus dem Index existiert im angegebenen Chunk.
4. Jede Kategorie existiert in `categories.json`.
5. Jede `by-category`-Datei enthält nur Einträge ihrer Kategorie.
6. Die Summe aller `by-category`-Einträge entspricht der Gesamtzahl.
7. Chunk-Grenzen werden eingehalten.
8. `aliases.json` zeigt nur auf existierende IDs.
9. Jede Frage hat mindestens Titel oder Fragetext.
10. Jede Frage hat eine `answers`-Liste.

---

## 13. Migrationsstrategie

Noch nicht ausführen. Nur später in getrennten Schritten.

### Phase 0 — Sicherung und Inventur

- Backup-Branch oder Git-Tag erstellen.
- Eintragszahlen lokal/streamend ermitteln.
- Erste und letzte Einträge prüfen.
- Verhältnis `qa_db.json` zu `qa_db/<jahr>.json` klären.

### Phase 1 — Dry Run

- Konverter erstellt neue Struktur nur unter `_migration_test_output/`.
- Originaldaten bleiben unverändert.
- Keine Website-Umstellung.

### Phase 2 — Validierung

- Anzahl alt/neu vergleichen.
- Stichproben prüfen.
- Antwortlisten prüfen.
- Aliases prüfen.
- Kategorien prüfen.

### Phase 3 — Produktiver Parallelaufbau

- Neue Struktur unter `data/questions/` erzeugen.
- Alte Struktur bleibt vollständig liegen.
- Frontend liest noch nicht zwingend daraus.

### Phase 4 — Frontend-Umstellung

- `script.js` lädt `manifest.json`, `categories.json` und `index.json`.
- `qa.html` lädt gezielt den passenden Chunk.
- Alte Pfade bleiben als Fallback im Code.

### Phase 5 — Schreibpfade umstellen

- `build_qa.py` oder Nachfolger schreibt über `qa_store.py`.
- Neue Uploads landen in Chunks.
- `responsa.json` wird nicht mehr für Q&A erweitert.

### Phase 6 — Beobachtung

- Einige Wochen parallel laufen lassen.
- Fehlerhafte Links prüfen.
- Performance prüfen.

### Phase 7 — Alte Bestände archivieren

Nur wenn alles stabil ist:

- alte redundante Dateien ins Archiv verschieben,
- nicht löschen,
- Protokoll schreiben.

---

## 14. Rollback-Prinzip

Bis zur endgültigen Stilllegung bleibt die alte Struktur liegen. Ein Rollback besteht dann nur aus:

1. Frontend-Änderungen zurücknehmen.
2. Schreibworkflow zurücknehmen.
3. Alte Datenpfade weiterverwenden.

Deshalb muss die neue Struktur zuerst parallel aufgebaut werden und darf alte Daten nicht überschreiben.
