# FRONTEND_KATEGORIEN — Kategorie-Anzeige & Filter

**Stand:** 06.07.2026  
**Branch:** `qa-frontend-categories-2026-07-06`

## Ziel

Das bestehende Frontend soll Kategorien professionell anzeigen und sauber filterbar machen, ohne das bestehende Design zu zerstören. Die alte Anzeige bleibt erhalten; ergänzt wurden nur Kategorie-Übersicht, bessere Kategorie-Badges, optionales Gruppieren und eine dezente Review-Markierung.

## 1. Ausgangslage

Kategorien waren im Frontend bereits teilweise sichtbar:

- `index.html` hatte bereits ein `select#categoryFilter`.
- `script.js` hatte bereits `filterResponsa()` und zeigte pro Karte `card-category`.
- Seit der neuen Daten-Lese-Logik können Kategorien aus `data/questions/categories.json` geladen werden.

Was fehlte:

- keine übersichtliche Kategorie-Anzeige oberhalb der Karten,
- keine anklickbaren Kategorie-Chips,
- keine sichtbare, aber dezente Kennzeichnung für `needs_review`,
- keine optionale Gruppierung nach Kategorien,
- lange/hebräische/deutsche/englische Texte waren nicht speziell gegen Überlauf abgesichert.

## 2. Geänderte Dateien

| Datei | Änderung |
|---|---|
| `index.html` | `qa-categories.css` eingebunden, Gruppierungs-Checkbox ergänzt, Bereich `#categoryOverview` eingefügt. |
| `script.js` | Kategorie-Chips, aktive Kategorie, Counts, Gruppierung nach Kategorien, Review-Badge, sicherere Kartenausgabe. |
| `qa-categories.css` | Neue scoped Kategorie-Styles: Chips, Übersicht, Gruppierungsüberschriften, Review-Badge, mobile horizontale Chip-Leiste, lange Texte. |
| `FRONTEND_KATEGORIEN.md` | Diese Dokumentation. |

## 3. Kategorie-Anzeige

Direkt über dem Kartenraster wird jetzt ein Bereich `#categoryOverview` gerendert.

Er zeigt:

- Titel „קטגוריות / Categories“,
- kurzen Hinweistext,
- Button „הכול / All“,
- einen Chip pro Kategorie,
- Anzahl der Fragen pro Kategorie,
- aktive Kategorie optisch hervorgehoben.

Die Labels kommen aus `qaCategories`, also aus `QAData.loadCategories()` im neuen Modus oder aus der Legacy-Fallback-Liste.

## 4. Kategorie-Filter

Es gibt zwei gleichwertige Einstiege:

1. bestehendes Dropdown `#categoryFilter`,
2. neue Kategorie-Chips im Bereich `#categoryOverview`.

Beide setzen denselben Wert und rufen dieselbe bestehende Filterfunktion auf:

```js
filterResponsa()
```

Im neuen Modus nutzt `searchResponsa()` weiterhin:

```js
QAData.search(searchTerm, { category })
QAData.getQuestionsByCategory(category)
```

Im Legacy-Modus bleibt der bestehende Array-Filter erhalten.

## 5. Gruppierung nach Kategorien

Optional kann der Nutzer die Checkbox „קיבוץ לפי קטגוריה / Group by category“ aktivieren.

Dann rendert `displayResponsa()` die aktuell gefilterten Karten mit Gruppenüberschriften. Diese Gruppierung verändert keine URLs und keine Daten; sie betrifft nur die Darstellung der aktuell sichtbaren Treffer.

## 6. needs_review

Fragen mit unsicherer Kategorie bekommen eine dezente Markierung:

```html
<span class="review-badge">Review</span>
```

Im Hebräisch-Modus steht dort:

```html
בדיקה
```

Die Karte bleibt normal sichtbar und filterbar. Die Markierung ist absichtlich klein und nicht blockierend.

## 7. Stabilität / Texte

Die Ergänzungen achten auf:

- Desktop: Chips umbrechen sauber, Kartenraster bleibt unverändert.
- Mobile: Kategorie-Chips werden horizontal scrollbar, Karten bleiben einspaltig.
- Hebräisch/RTL: bestehende `body[dir="rtl"]`-Logik bleibt erhalten.
- Deutsch/Englisch/Sonderzeichen: Kartentexte werden HTML-escaped und lange Wörter brechen sauber um.
- Bestehende Links: Karten verlinken weiter auf `qa.html?id=<id>`.

## 8. Tests

Durchgeführt wurden:

- GitHub-Dateiprüfung: `index.html`, `script.js`, `qa-categories.css` nach dem Commit erneut gelesen.
- Strukturprüfung: Kategorie-Container, Gruppierungs-Checkbox und CSS-Link vorhanden.
- Logikprüfung im Code: `searchResponsa()` bleibt Einstiegspunkt; Chips setzen `categoryFilter`; Dropdown und Chips verwenden dieselbe Filterfunktion.
- Bestehende Suche/Filter aus dem vorherigen Schritt bleiben unangetastet: `QAData.search()`, `QAData.searchDeep()` und `getQuestionsByCategory()` werden weiterhin verwendet.

## 9. Offene Punkte

- Kein echter GitHub-Pages-Browserlauf wurde über den Connector gestartet.
- Die optische Endkontrolle im Browser sollte nach dem nächsten Deploy kurz auf Desktop und Mobile gemacht werden.
