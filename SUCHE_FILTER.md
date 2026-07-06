# SUCHE_FILTER — Suche & Kategorie-Filter auf der neuen Datenstruktur

**Stand:** 06.07.2026  
**Ziel:** Die Suche hängt nicht mehr an einer einzigen großen Datei. Q&A-Suche und Filter laufen über `data/questions/index.json`, `data/questions/by-category/` und bei Bedarf lazy geladene Chunks.

## 1. Geänderte Dateien

| Datei | Änderung |
|---|---|
| `qa-data.js` | Daten-Layer stellt `QAData.search(query, {category, limit})` und `QAData.searchDeep(query, {category, limit})` bereit. |
| `script.js` | Bestehende Suchfunktion bleibt erhalten, ruft im neuen Modus aber `QAData.search()` auf; bei 0 Treffern wird `QAData.searchDeep()` als Volltext-Fallback genutzt. |
| `test_search.mjs` | Such- und Filtertests für Titel, Frage, Antwort, Kategorie, Tags, ID, Deutsch, Englisch, Hebräisch und Legacy-Fallback. |
| `SUCHE_FILTER.md` | Diese Dokumentation. |

## 2. Suchstrategie

### Standard-Suche

`QAData.search()` sucht zuerst nur im kompakten Index. Dadurch werden keine großen Chunk-Dateien geladen.

Der Index enthält:

```json
{
  "id": "my-1001",
  "t_he": "",
  "t_en": "Title",
  "x": "question_excerpt",
  "ax": "answer_excerpt",
  "tg": ["tag"],
  "c": "halacha",
  "y": 2026,
  "ch": 1,
  "s": "miyodea"
}
```

Damit sind abgedeckt:

- Titel,
- Frage-Auszug,
- Antwort-Auszug der akzeptierten Antwort,
- Kategorie-ID über Filter,
- Tags/Schlagwörter,
- Chunk-Verweis,
- stabile ID.

Mehrwort-Suche ist UND-verknüpft. Groß-/Kleinschreibung wird ignoriert. Unicode wird per NFC normalisiert, dadurch funktionieren deutsche Umlaute und Hebräisch sauber.

### Kategorie-Filter

Wenn eine Kategorie aktiv ist, nutzt `QAData.search()` nicht die alte Riesendatei, sondern:

```text
data/questions/by-category/<category>.json
```

Das ist eine kleine Datei pro Kategorie. Kategorie allein funktioniert ohne Chunk-Load.

### ID-Suche

Die Suche erkennt:

- neue IDs wie `my-1001`, `ye-555`, `up-2026-0001`,
- nackte Alt-IDs über `aliases.json`,
- alte Nummern wie `n1002`.

### Tiefensuche

`QAData.searchDeep()` lädt Chunks nur dann lazy und gecacht, wenn Volltext nötig ist. Sie durchsucht:

- volle Frage,
- alle Antworten,
- auch nicht-akzeptierte Zweitantworten.

`script.js` nutzt diese Tiefensuche nur als Fallback, wenn die schnelle Indexsuche 0 Treffer liefert. Dadurch bleibt die normale Suche schnell, findet aber schwierige Antworttreffer trotzdem.

## 3. Bestehende Suchfunktion

Die bestehende Funktion `searchResponsa()` bleibt der Einstiegspunkt für die Oberfläche. Sie wurde nur intern umgestellt:

- neuer Modus: `QAData.search()` / `QAData.searchDeep()`,
- Legacy-Modus: alter Array-Filter über `responsa.json`,
- Kategorie-Filter bleibt über `categoryFilter`,
- Jahresfilter bleibt unverändert.

## 4. Testabdeckung

`test_search.mjs` prüft:

- englischer Titel: `sugya Gemara`,
- deutsche Frage/Sonderzeichen: `Gänsefüßchen`,
- Antwort-Exzerpt: `Dappim`,
- Hebräisch: `מוקצה`,
- hebräischer Upload-Titel: `הכוונות`,
- Kategorie allein: `halacha`,
- Kategorie + Text: `shabbat` in `halacha`,
- Schlagwort/Tag: `muktzeh`,
- neue ID: `my-2001`,
- nackte Alt-ID: `555`,
- alte Nummer: `n1002`,
- Mehrwort-UND: `temple chronology`,
- Tiefensuche in Zweitantwort: `structure of the Bavli`,
- Negativtest ohne Treffer,
- Legacy-Suche Englisch,
- Legacy-Suche Hebräisch,
- Legacy-Kategorie-Filter.

## 5. Offene Grenzen

- Standard-Suche nutzt nur Index-Auszüge. Vollständige Antwortsuche läuft über `searchDeep()`.
- Es gibt noch kein Stemming und keine hebräische Morphologie.
- Bei sehr vielen Chunks sollte `searchDeep()` später mit Fortschrittsanzeige oder explizitem Button „Erweiterte Suche“ verwendet werden.
- Teshuvot sind weiter nicht Teil des Q&A-Index; sie brauchen später einen eigenen `data/teshuvot/index.json`.
