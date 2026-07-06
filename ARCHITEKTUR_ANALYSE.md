# ARCHITEKTUR_ANALYSE — Moriahise/Sanhedrin

**Stand:** 06.07.2026  
**Branch:** `qa-data-analysis-2026-07-06`  
**Art:** Nur-Lese-Analyse. Keine Daten verändert. Keine Migration ausgeführt.

## Methodik

Geprüft wurden nur Code-Dateien und kleine Ausschnitte aus Daten-Dateien. Große JSON-Dateien wurden nicht vollständig geladen. Root-Dateien `responsa.json` und `qa_db.json` wurden nur kurz abgerufen; beide sind im aktuell geprüften `main` leer sichtbar. Das ändert aber nicht die Architektur: mehrere Skripte schreiben weiterhin in `responsa.json`.

## Aktuelle Projektstruktur für Q&A

```text
index.html                         Startseite mit Suchfeld/Kategorie-/Jahresfilter
script.js                          lädt responsa.json vollständig und filtert im Browser
qa.html                            Q&A-Detailseite, lädt Frage per id/src
responsa.json                      zentraler Index; aktuell leer, aber Ziel der Schreiblogik
qa_db.json                         Root-Monolith; aktuell leer
build_qa.py                        MiYodea -> data/qa/generated + responsa.json
scripts/ingest_miyodea_qa.py       MiYodea -> qa_db/<jahr>.json + responsa.json
update_responsa.py                 responsa/<jahr> HTML/PDF -> responsa.json
miyodea/qa/*.json                  MiYodea-Rohdaten
data/qa/generated/*.json           normalisierte Q&A-Dateien
qa_db/<jahr>.json                  Jahresdateien
.github/workflows/update-responsa.yml
```

## Zentrale Code-Beobachtungen

### `build_qa.py`

Das Skript liest `miyodea/qa/*.json`, erzeugt normalisierte Dateien unter `data/qa/generated/` und hängt pro Frage einen Eintrag an `responsa.json` an. Die Zielstruktur der normalisierten Datei ist `questions[]` mit `id`, `title`, `question`, `answer` und `metadata`.

Beim Index-Eintrag werden u. a. geschrieben:

- `number`
- `title_he`, `title_en`
- `summary_he`, `summary_en`
- `category`, `category_he`, `category_en`
- `date`, `year`
- `file`
- `type`

Kritisch: Mehrere MiYodea-Antworten werden auf ein einzelnes Feld `answer` reduziert. Außerdem schreibt das Skript weiter in den zentralen Index `responsa.json`.

### `scripts/ingest_miyodea_qa.py`

Dieses Skript ist teilweise besser, weil es `qa_db/<jahr>.json` erzeugt. Gleichzeitig schreibt es weiter neue Index-Einträge nach `responsa.json`. Es ergänzt dabei `source`, `source_url`, `tags`, `source_id` und `src`.

Damit gibt es zwei verschiedene Q&A-Schreibwege, die ähnliche, aber nicht identische Index-Einträge erzeugen.

### `update_responsa.py`

Dieses Skript scannt `responsa/` nach HTML/HTM/PDF-Dateien und hängt neue Dokumente an `responsa.json` an. Kategorien werden standardmäßig als `other` geschrieben. Datum und Jahr kommen aus der lokalen Datei-mtime.

### GitHub Workflow

`.github/workflows/update-responsa.yml` läuft bei Änderungen unter `responsa/**` oder an `update_responsa.py`. Danach wird `responsa.json` automatisch committed, falls sie sich geändert hat.

### `script.js`

Die Startseite lädt `responsa.json` vollständig in den Browser und filtert danach clientseitig nach Suche, Kategorie und Jahr. Dadurch wird `responsa.json` zur Laufzeit-Datenbank der Website.

### `qa.html`

Die Detailseite liest `id` und optional `src` aus der URL. Ohne `src` lädt sie `responsa.json`, sucht `source_id` und `src`, und lädt danach die eigentliche Q&A-Datei. Sie kann sowohl Arrays als auch Objekte mit `questions[]` verarbeiten.

## Aktuelle Datenflüsse

### Responsa-Upload

```text
responsa/<jahr>/*.html|pdf
  -> GitHub Action
  -> update_responsa.py
  -> responsa.json
```

### MiYodea-Build

```text
miyodea/qa/*.json
  -> build_qa.py
  -> data/qa/generated/*.normalized.json
  -> responsa.json
```

### MiYodea-Ingest

```text
miyodea/qa/*.json
  -> scripts/ingest_miyodea_qa.py
  -> qa_db/<jahr>.json
  -> responsa.json
```

### Startseite

```text
index.html
  -> script.js
  -> fetch('responsa.json') komplett
  -> Browser-Suche und Filter
```

### Q&A-Detailseite

```text
qa.html?id=...&src=...
  -> src-Datei laden
  -> Frage/Antwort anzeigen

qa.html?id=... ohne src
  -> responsa.json laden
  -> source_id/src suchen
  -> ggf. qa_db/<jahr>.json laden
```

## Kategorien

Kategorien sind nicht zentral definiert. Sie existieren:

- hart codiert in `index.html`,
- als Felder in `responsa.json`-Einträgen,
- als Tags in MiYodea-Metadaten.

Die Skripte ordnen fachlich nicht sauber zu. `update_responsa.py` schreibt `other`; `build_qa.py` schreibt `category: other`, aber als Label `Q&A`. Dadurch ist die Kategorie-Logik uneinheitlich.

## Datei, die zu groß wird

Im aktuellen `main` sind `responsa.json` und `qa_db.json` leer sichtbar. Die aktive Architektur schreibt aber weiter nach `responsa.json`. Deshalb ist die kritische Datei:

```text
responsa.json
```

Sie wird durch Responsa-Uploads, Q&A-Builds und MiYodea-Ingests zum zentralen Monolithen.

## Risiken bei weiterer Vergrößerung

1. `responsa.json` muss vollständig vom Browser geladen werden.
2. Mehrere Schreibwege hängen neue Daten an dieselbe Datei.
3. Bei starkem Wachstum drohen langsame Ladezeiten und große Git-Commits.
4. Kategoriepflege wird bei großer Datei unpraktisch.
5. Die Daten liegen in mehreren Schemata vor.
6. Mehrere Antworten können bei der Normalisierung verloren gehen.
7. Unbereinigtes HTML aus Fremdquellen wird in der Detailansicht direkt verarbeitet.
8. Datei-mtime ist keine zuverlässige Datumsquelle für GitHub Actions.

## Geeignete Zielarchitektur

Empfohlen wird eine klare Trennung von Suchindex und Volltexten:

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

Grundsätze:

- `index.json` enthält nur Suchfelder.
- `chunks/` enthält Frage und alle Antworten.
- `categories.json` definiert Kategorien zentral.
- `aliases.json` erhält alte Links und alte IDs auflösbar.
- Neue Uploads schreiben nicht mehr in `responsa.json`.

## Nächste Schritte

1. Exakte Eintragszahlen lokal oder streamend ermitteln.
2. Entscheiden, welches Q&A-Schema künftig Source of Truth ist.
3. Migration zuerst nur als Dry Run ausführen.
4. Frontend erst nach Validierung umstellen.
