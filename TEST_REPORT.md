# TEST_REPORT — Gesamttest Q&A-Struktur, Suche, Kategorien und Uploads

**Stand:** 06.07.2026  
**Branch:** `qa-full-test-2026-07-06`  
**Basis:** `qa-frontend-categories-2026-07-06`

## 1. Testumfang

Geprüft wurden die vom Auftrag geforderten Bereiche:

1. Projektstart lokal
2. Laden der Startseite
3. Laden der Fragen
4. Laden einzelner Antworten
5. Suche
6. Kategorie-Filter
7. Upload neuer Fragen
8. Speicherung neuer Fragen in Chunk-Dateien
9. Aktualisierung von `index.json`
10. Aktualisierung von `by-category` Dateien
11. Hebrew / Deutsch / Englisch / Sonderzeichen
12. bestehende IDs und Links
13. alte Funktionen / Fallback
14. fehlende Daten
15. Konsolen- beziehungsweise Laufzeitfehler, soweit prüfbar

## 2. Testumgebung

### GitHub-Connector-Prüfung

Die aktuellen Branch-Dateien wurden über den GitHub-Connector geprüft:

- `index.html`
- `script.js`
- `qa-categories.css`
- `qa_store.py`
- bestehende Lese-/Suchlogik aus den vorherigen Branches

### Lokaler Test

Ein direkter lokaler Clone aus der Sandbox war nicht möglich:

```text
fatal: unable to access 'https://github.com/Moriahise/Sanhedrin.git/': Could not resolve host: github.com
```

Deshalb wurde lokal ein statisches Testverzeichnis mit den Projektkomponenten aufgebaut und per HTTP-Server getestet. Das entspricht technisch GitHub Pages: statische Dateien + `fetch()`.

Verwendet:

- Python 3
- Node.js 22
- lokaler HTTP-Server
- Mock-Daten mit Mi-Yodeya-, Yeshiva- und Upload-ähnlichen Einträgen
- hebräische, deutsche und englische Texte
- Sonderzeichen: `äöüß`, `«»`, `עברית`, `✔`, HTML-ähnlicher Text

## 3. Durchgeführte Tests

| # | Test | Ergebnis |
|---|---|---|
| 1 | Projektstart lokal mit `python3 -m http.server` im rekonstruierten statischen Testverzeichnis | OK |
| 2 | Startseite per HTTP geladen | OK — HTTP 200 |
| 3 | `qa.html` per HTTP geladen | OK — HTTP 200 |
| 4 | `data/questions/index.json` per HTTP geladen | OK — HTTP 200 |
| 5 | `QAData.init()` erkennt neue Struktur | OK — Modus `new` |
| 6 | Fragenbestand aus `index.json` geladen | OK |
| 7 | Kategorien aus `categories.json` geladen | OK |
| 8 | Einzelne Frage per neuer ID geladen | OK |
| 9 | Einzelne Frage per nackter Alt-ID/Alias geladen | OK |
| 10 | Antwortliste einer Frage geladen | OK |
| 11 | Suche nach englischem Titel | OK |
| 12 | Suche nach deutschem Begriff mit Sonderzeichen | OK |
| 13 | Suche nach hebräischem Begriff | OK |
| 14 | Suche nach Antwort-Exzerpt | OK |
| 15 | Suche nach Schlagwort/Tag | OK |
| 16 | Suche nach stabiler ID | OK |
| 17 | Suche nach nackter Alt-ID | OK |
| 18 | Kategorie-Filter `halacha` | OK |
| 19 | Kategorie-Filter für neu hochgeladene Frage | OK |
| 20 | Tiefensuche in Antwort-Volltext | OK |
| 21 | Upload neuer Frage über `add_qa_upload.py` | OK |
| 22 | Speicherung des Uploads in neuem Chunk bei vollem Chunk | OK |
| 23 | `index.json` nach Upload aktualisiert | OK |
| 24 | `by-category/<category>.json` nach Upload aktualisiert | OK |
| 25 | Store-Konsistenz `add_qa_upload.py --verify` | OK |
| 26 | Hebrew/Deutsch/Englisch/Sonderzeichen nach Upload erhalten | OK |
| 27 | Keine unbehandelten Node-Laufzeitfehler im Testlauf | OK |

## 4. Automatischer lokaler Testlauf

Auszug aus dem finalen Node-Testlauf:

```text
[OK] Startseite HTTP 200 — 200
[OK] qa.html HTTP 200 — 200
[OK] index.json HTTP 200 — 200
[OK] QAData Modus new — new
[OK] Fragen geladen: 4 — 4
[OK] Kategorien geladen — halacha,tanach,talmud,kabbalah,history,general
[OK] Einzelne Frage per neuer ID — my-1001
[OK] Einzelne Frage per alter/nackter ID — my-1002
[OK] Suche Titel Englisch
[OK] Suche Deutsch/Sonderzeichen
[OK] Suche Hebräisch
[OK] Suche Antwort-Exzerpt
[OK] Suche Schlagwort
[OK] Suche neue/stabile ID
[OK] Suche nackte Alt-ID
[OK] Kategorie-Filter halacha
[OK] Kategorie-Filter Upload kabbalah
[OK] Tiefensuche Antwort-Volltext
[OK] Upload im neuen Chunk geladen
[OK] Upload Sonderzeichen erhalten
ERGEBNIS 20 OK, 0 FEHLER
```

Zusätzlich:

```text
OK  up-2026-0001 -> qa_0002.json  Kategorie: kabbalah (high)
Konsistenzprüfung nach Upload: OK
```

Damit sind Upload, Chunk-Rollover, Index-Aktualisierung, Kategorie-Datei und Suche im lokalen statischen Szenario geprüft.

## 5. GitHub-Codeprüfung

### Frontend

`index.html` enthält:

- `styles.css`
- zusätzlich `qa-categories.css`
- bestehendes Suchfeld
- bestehendes Kategorie-Dropdown
- bestehendes Jahres-Dropdown
- neue Gruppierungs-Checkbox
- neuen Bereich `#categoryOverview`
- bestehende Einbindung von `qa-data.js` und `script.js`

`script.js` enthält:

- `rebuildCategoryFilter()`
- `renderCategoryOverview()`
- Kategorie-Chips mit Counts
- `setCategoryFilter()`
- optionale Gruppierung nach Kategorien
- `needs_review` als Review-Badge
- Suche über `QAData.search()` / `QAData.searchDeep()` / `getQuestionsByCategory()`
- Legacy-Fallback über `responsa.json`

`qa-categories.css` enthält:

- scoped Zusatzstyles für Kategorie-Chips
- Gruppierungsüberschriften
- Review-Badge
- Tag-Anzeige
- Schutz gegen lange Texte
- mobile horizontale Chip-Leiste

### Upload / Store

`qa_store.py` enthält:

- Validierung
- stabile ID-Erzeugung
- Kategoriezuordnung
- `needs_review`
- Chunk-Rollover
- atomare JSON-Schreibweise
- `index.json` Aktualisierung
- `by-category` Aktualisierung
- `aliases.json` Aktualisierung
- `verify()` für Konsistenz
- Indexfelder `ax` für Antwort-Exzerpt und `tg` für Tags

## 6. Erfolgreiche Tests

Erfolgreich geprüft:

- Projektstart als statische Seite
- Startseite lädt
- Detailseite lädt
- neue Q&A-Struktur wird erkannt
- Fragenindex lädt
- Kategorien laden
- Einzelfrage per neuer ID lädt
- Einzelfrage per alter ID/Alias lädt
- Antworten laden
- Suche findet Titel, Frage, Antwort, Tags, IDs, Deutsch, Englisch, Hebräisch
- Kategorie-Filter funktioniert
- Upload erzeugt stabile ID
- Upload schreibt in nächsten Chunk, wenn der vorherige voll ist
- `index.json` wird erweitert
- `by-category` wird erweitert
- `aliases.json` wird erweitert
- `add_qa_upload.py --verify` meldet keine Probleme
- Sonderzeichen bleiben erhalten
- keine unbehandelten JS-Fehler im Node-Lauf

## 7. Gefundene Fehler

### Fehler 1: direkter Git-Clone in der Sandbox nicht möglich

Der lokale Clone direkt aus GitHub schlug fehl, weil die Sandbox `github.com` nicht auflösen konnte.

Status: **nicht projektbezogen**, sondern Umgebungslimit.  
Ausgleich: GitHub-Dateien über Connector geprüft, lokaler statischer Mock-Test durchgeführt.

### Fehler 2: erster lokaler Mock mit älterem Paketstand fand Tags nicht

Im ersten lokalen Testlauf mit einem älteren lokal gemounteten Paketstand fehlten im erzeugten Index die Felder `tg` und `ax`. Dadurch schlug die Tag-Suche fehl.

Status: **im GitHub-Branch bereits behoben**.  
Die aktuelle Branch-Version von `qa_store.py` schreibt `ax` und `tg` in den Index. Der finale Test wurde mit dieser Logik wiederholt und ergab 20/20 OK.

## 8. Behobene Fehler

- Testumgebung auf aktuelle Indexfelder `ax` und `tg` ausgerichtet.
- Finaler Such-/Upload-/Chunk-Test danach vollständig grün.
- Testdokumentation ergänzt, damit der echte lokale Clone auf Windows/Linux reproduzierbar getestet werden kann.

## 9. Offene Punkte

- Kein echter Browser-GitHub-Pages-Live-Test wurde ausgeführt. Der Connector kann keine Browserkonsole öffnen.
- Kein echter lokaler Clone des GitHub-Branches war in der Sandbox möglich, weil DNS für `github.com` blockiert war.
- Die optische Endkontrolle muss lokal im Browser erfolgen:
  - Desktop
  - Mobile / schmale Breite
  - RTL/Hebräisch
  - lange Fragen
  - Browser-Konsole F12
- Erst nach einem echten lokalen Clone sollte der Branch nach `main` gemerged werden.

## 10. Ergebnis

Gesamtergebnis der ausführbaren Tests: **bestanden**.

Die neue Q&A-Struktur ist im getesteten statischen Szenario funktionsfähig:

- Lesen funktioniert.
- Suche funktioniert.
- Kategorie-Filter funktionieren.
- Einzelantworten laden.
- Uploads werden chunked gespeichert.
- Index und Kategorie-Dateien werden aktualisiert.
- Sonderzeichen bleiben erhalten.
- Alte IDs/Aliases bleiben prüfbar.

Empfehlung: Jetzt lokal mit echtem Clone gemäß `TEST_ANLEITUNG.md` nachtesten, Browserkonsole prüfen, dann erst Pull Request/Merge nach `main`.
