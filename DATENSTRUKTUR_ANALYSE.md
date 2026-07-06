# DATENSTRUKTUR_ANALYSE — Frage-Antwort-Daten in Moriahise/Sanhedrin

**Stand:** 06.07.2026  
**Branch:** `qa-data-analysis-2026-07-06`  
**Art:** Nur-Lese-Analyse. Keine Daten verändert. Keine Migration ausgeführt.

## 1. Kurzantworten auf die 10 Leitfragen

### 1. Wo sind Fragen gespeichert?

Fragen liegen an mehreren Orten:

1. `miyodea/qa/*.json`  
   Rohdaten. Die Frage steckt im Feld `content` hinter der Überschrift `## Frage`.

2. `data/qa/generated/*.normalized.json`  
   Von `build_qa.py` erzeugte Normalform. Die Frage steht im Feld `question`.

3. `qa_db/<jahr>.json`  
   Jahresdateien. Sichtbar sind mindestens `qa_db/2010.json` und `qa_db/2026.json`. Die Struktur ist gemischt: teils MiYodea-artig mit `content`, teils Yeshiva-artig mit `question` und `answer`.

4. `qa_db.json`  
   Root-Monolith. Im aktuell geprüften `main` leer sichtbar.

5. `responsa.json`  
   Kein Volltext-Speicher, sondern Index. Im aktuell geprüften `main` leer sichtbar, aber Ziel der aktiven Schreibskripte.

### 2. Wo sind Antworten gespeichert?

Antworten liegen jeweils beim Frage-Eintrag:

- MiYodea-Rohdaten: im Feld `content` hinter `## Antworten` und `### Antwort` / `### ✅ Antwort`.
- Normalisierte Dateien: im Feld `answer`.
- `qa_db/<jahr>.json`: entweder im Feld `answer` oder innerhalb von `content`.

### 3. Sind Fragen und Antworten zusammen oder getrennt gespeichert?

Zusammen. Ein Frageobjekt enthält entweder:

- `content` mit Frage und Antworten gemeinsam,
- oder `question` und `answer` im selben Objekt.

Getrennt ist nur der Index: `responsa.json` enthält Titel, Kurztext und Link zur Detaildatei, aber nicht zwingend den ganzen Q&A-Volltext.

### 4. Welche Felder hat ein Eintrag?

Erkannte Varianten:

#### MiYodea-Rohform

```json
{
  "id": "miyodeya_154636",
  "title": "What does הי׳ mean?",
  "content": "# Title...\n\n## Frage...\n\n## Antworten...",
  "metadata": {
    "source": "Mi Yodeya",
    "url": "https://...",
    "tags": ["jewish-books"],
    "score": -1,
    "views": 55,
    "date": "2026-01-01T11:06:11",
    "answers": 1
  }
}
```

#### Normalisierte Form aus `build_qa.py`

```json
{
  "id": "miyodeya_154636",
  "title": "What does הי׳ mean?",
  "question": "...",
  "answer": "...",
  "metadata": {
    "source": "Mi Yodeya",
    "url": "https://...",
    "tags": [],
    "score": -1,
    "views": 55,
    "date": "2026-01-01T11:06:11",
    "answers": 1
  }
}
```

#### Jahresdatei `qa_db/2026.json`

```json
{
  "id": "149283",
  "url": "https://www.yeshiva.org.il/ask/149283",
  "title": "יהדות, שיעורים, זמנים",
  "question": "",
  "answer": "",
  "metadata": {},
  "saved_at": "2025-12-10T05:41:36.663Z",
  "filename": "2025-12-יהדות-שיעורים-זמנים.149283.html"
}
```

#### Index-Eintrag in `responsa.json`

Je nach Schreibskript gibt es zwei Varianten.

`build_qa.py` schreibt:

```json
{
  "number": 154636,
  "title_he": "...",
  "title_en": "...",
  "summary_he": "...",
  "summary_en": "...",
  "category": "other",
  "category_he": "שאלות ותשובות",
  "category_en": "Q&A",
  "date": "01/01/2026",
  "year": 2026,
  "file": "qa.html?id=miyodeya_154636&src=data/qa/generated/DATEI.normalized.json",
  "type": "html"
}
```

`scripts/ingest_miyodea_qa.py` ergänzt zusätzlich:

```json
{
  "source": "Mi Yodeya",
  "source_url": "https://...",
  "tags": [],
  "source_id": "miyodeya_154636",
  "src": "miyodea/qa/DATEI.json"
}
```

### 5. Sind IDs vorhanden?

Ja, aber uneinheitlich.

- MiYodea: `miyodeya_<nummer>` oder ähnliche Quellen-ID.
- Yeshiva-artige Jahresdateien: numerische ID als String.
- `responsa.json`: zusätzlich `number`, aber kein einheitlicher Primärschlüssel.

Problem: `number` wird je nach Skript anders erzeugt. Ein globales Schema wie `my-154636` oder `ye-149283` gibt es noch nicht.

### 6. Sind Kategorien vorhanden?

Formal ja, praktisch schwach.

- `index.html` hat Kategorieoptionen.
- `responsa.json`-Einträge haben `category`, `category_he`, `category_en`.
- MiYodea hat `metadata.tags`.

Aber:

- `update_responsa.py` schreibt immer `other`.
- `build_qa.py` schreibt ebenfalls `other`, aber mit Label `Q&A`.
- Tags werden nicht zuverlässig auf Kategorien gemappt.

### 7. Schreiben Uploads neue Daten in eine große Datei?

Ja. Die aktive Logik schreibt neue Daten weiterhin in `responsa.json`:

- `update_responsa.py` für HTML/PDF-Responsa.
- `build_qa.py` für normalisierte MiYodea-Q&A.
- `scripts/ingest_miyodea_qa.py` für MiYodea-Jahresdaten.

### 8. Welche Datei wird aktuell zu groß?

Im aktuell geprüften `main` sind `responsa.json` und `qa_db.json` leer sichtbar. Trotzdem ist die Architektur so gebaut, dass `responsa.json` bei Nutzung zum großen Monolithen wird.

Kritische Datei:

```text
responsa.json
```

Sekundäre Wachstumsorte:

```text
qa_db/<jahr>.json
miyodea/qa/*.json
data/qa/generated/*.normalized.json
```

### 9. Wie viele Fragen sind ungefähr vorhanden?

Exakte Zählung wurde nicht durchgeführt, weil keine großen JSON-Dateien vollständig geladen wurden.

Sicher sichtbar:

- mehrere MiYodea-Rohdateien unter `miyodea/qa/`,
- mindestens `qa_db/2010.json` und `qa_db/2026.json`,
- `qa_db/2026.json` enthält im sichtbaren Ausschnitt mehrere Dutzend Einträge,
- `qa_db/2010.json` enthält MiYodea-Einträge mit mehreren Antworten.

Saubere Zählung muss lokal oder streamend erfolgen, z. B. ohne die Datei in einem Editor zu öffnen.

Empfohlener Prüfweg lokal:

```bash
python3 - <<'PY'
import json
from pathlib import Path
for p in sorted(Path('qa_db').glob('*.json')):
    with p.open(encoding='utf-8') as f:
        d=json.load(f)
    print(p, len(d.get('questions', [])) if isinstance(d, dict) else len(d))
PY
```

### 10. Welche Struktur eignet sich für die Migration?

Geeignet ist eine geteilte Struktur mit kleinem Index und Volltext-Chunks:

```text
data/questions/
├── manifest.json
├── categories.json
├── aliases.json
├── index.json
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

## 2. Aktuelle Datenstruktur

```text
miyodea/qa/*.json
  Array von Roh-Fragen
  Q&A gemeinsam in content
  Metadaten in metadata

qa_db/<jahr>.json
  questions[]
  teils content-basiert, teils question/answer-basiert

data/qa/generated/*.normalized.json
  questions[]
  question und answer getrennt, aber nur eine Antwort

responsa.json
  zentraler Index
  aktuell leer sichtbar, aber Ziel aller Schreibpfade
```

## 3. Beispiel eines Frage-Antwort-Eintrags

### MiYodea-Rohdaten

```json
{
  "id": "miyodeya_4781",
  "title": "Chamishim Umeya - mi yodeya?",
  "content": "# Titel\n\n## Frage\n\n...\n\n## Antworten\n\n### ✅ Antwort 1 ...",
  "metadata": {
    "source": "Mi Yodeya",
    "url": "https://judaism.stackexchange.com/questions/4781/...",
    "tags": ["mi-yodeya-series", "number"],
    "score": 4,
    "views": 154,
    "date": "2010-12-21T16:53:44",
    "answers": 3
  }
}
```

### Gewünschte künftige Normalform

```json
{
  "id": "my-4781",
  "source": "miyodea",
  "legacy": {
    "source_id": "miyodeya_4781"
  },
  "category": "general",
  "title": "Chamishim Umeya - mi yodeya?",
  "question": "...",
  "answers": [
    {
      "text": "...",
      "accepted": true,
      "author": null,
      "score": 7
    }
  ],
  "url": "https://judaism.stackexchange.com/questions/4781/...",
  "tags": ["mi-yodeya-series", "number"],
  "date": "2010-12-21"
}
```

## 4. Erkannte Felder

| Bereich | Felder |
|---|---|
| Roh-Q&A | `id`, `title`, `content`, `metadata`, `url` |
| Metadata | `source`, `url`, `tags`, `score`, `views`, `date`, `answers` |
| Normalisiert | `id`, `title`, `question`, `answer`, `metadata` |
| Jahresdatei | `id`, `url`, `title`, `question`, `answer`, `metadata`, `saved_at`, `filename` |
| Index | `number`, `title_he`, `title_en`, `summary_he`, `summary_en`, `category`, `category_he`, `category_en`, `date`, `year`, `file`, `type` |
| Erweiterter Index aus ingest | `source`, `source_url`, `tags`, `source_id`, `src` |

## 5. Fehlende oder schwache Felder

| Feld | Problem |
|---|---|
| globale ID | Es gibt keine einheitliche ID über alle Quellen. |
| `answers[]` | Mehrere Antworten werden nicht durchgehend als Liste erhalten. |
| `category` | Vorhanden, aber meist `other`. |
| `category_confidence` | Keine Kennzeichnung sicherer/unsicherer Zuordnung. |
| `lang` | Sprache wird nicht sauber gespeichert. |
| `author` / `rabbi` | Nicht einheitlich vorhanden. |
| `source` | Nicht überall gleich benannt. |
| `legacy` | Alte IDs und alte Links sind nicht systematisch gesammelt. |
| zuverlässiges Datum | mtime ist keine gute Quelle für GitHub Actions. |

## 6. Aktuelle Probleme

1. Zu viele parallele Datenformen.
2. `responsa.json` ist weiterhin zentraler Index.
3. Startseite lädt den ganzen Index.
4. Q&A-Detailseite hat mehrere Fallback-Wege.
5. Kategorien sind nicht zentral gepflegt.
6. Mehrfachantworten können verloren gehen.
7. Root-Monolithen `responsa.json` und `qa_db.json` sind aktuell leer, bleiben aber als Architektur-Altlasten im System.
8. `qa_db/<jahr>.json` ist nicht vollständig homogen.

## 7. Risiko bei weiterer Vergrößerung

Wenn weiter in `responsa.json` geschrieben wird:

- wächst eine einzelne Datei statt vieler kleiner Dateien,
- jeder Besucher muss mehr Daten laden,
- jeder Auto-Commit wird größer,
- Suche und Filter bleiben clientseitig teuer,
- spätere manuelle Pflege wird unpraktisch.

## 8. Vorschlag für neue geteilte Struktur

### Dateien

```text
data/questions/manifest.json
```

Kleines Steuerfile: Schema-Version, Gesamtzahl, offene Chunk-Nummer, Index-Dateien.

```text
data/questions/index.json
```

Kompakter Suchindex ohne Volltexte.

```text
data/questions/chunks/qa_0001.json
```

Volltext-Chunks mit Frage und allen Antworten.

```text
data/questions/categories.json
```

Zentrale Kategorie-Definition und Tag-Mapping.

```text
data/questions/by-category/<category>.json
```

Kleine Indexlisten pro Kategorie.

```text
data/questions/aliases.json
```

Alte IDs und alte Links zeigen auf neue IDs und Chunks.

### Index-Eintrag

```json
{
  "id": "my-4781",
  "t_he": "",
  "t_en": "Chamishim Umeya - mi yodeya?",
  "x": "kurzer Frageauszug",
  "ax": "kurzer Antwortauszug",
  "tg": ["mi-yodeya-series", "number"],
  "c": "general",
  "y": 2010,
  "ch": 1,
  "s": "miyodea"
}
```

### Chunk-Eintrag

```json
{
  "id": "my-4781",
  "source": "miyodea",
  "title": "Chamishim Umeya - mi yodeya?",
  "question": "...",
  "answers": [
    {"text": "...", "accepted": true, "author": null, "score": 7}
  ],
  "url": "https://...",
  "tags": ["mi-yodeya-series", "number"],
  "date": "2010-12-21"
}
```

## 9. Migrationsprinzip

Nicht direkt umstellen. Erst parallel aufbauen:

1. Daten nur lesen.
2. Neue Struktur unter `_migration_test_output/` erzeugen.
3. Anzahl, IDs, Felder und Antwortlisten vergleichen.
4. Erst danach produktiv nach `data/questions/` schreiben.
5. Frontend erst nach bestandener Prüfung umstellen.
6. Alte Struktur nur stilllegen, nicht sofort entfernen.
