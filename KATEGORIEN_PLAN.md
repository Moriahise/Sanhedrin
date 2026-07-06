# KATEGORIEN_PLAN

**Stand:** 06.07.2026  
**Status:** Nur Analyse und Regelentwurf. Keine Daten verändert. Keine Kategorien geschrieben.

## Vorhandenes System

Das bestehende Frontend kennt acht alte Kategorien: `civil`, `family`, `ritual`, `kashrut`, `shabbat`, `conversion`, `halacha-history` und `other`.

Diese Kategorien sind im Frontend sichtbar. `script.js` filtert nach `item.category`.

Die Schreibskripte ordnen jedoch nicht wirklich zu. `update_responsa.py` schreibt neue Responsa mit `category: other`. `build_qa.py` schreibt Q&A ebenfalls mit `category: other`, aber teilweise mit dem Label `Q&A`. Das ist keine echte Fachkategorie.

Mi-Yodeya-Daten haben oft `metadata.tags`. Diese Tags werden bisher nicht systematisch ausgewertet.

## Problem

Es gibt keine zentrale Kategorie-Datei. Die Kategorien stehen im Frontend, im README und in einzelnen Datensätzen. Dadurch können UI, Daten und Skripte auseinanderlaufen.

Die bisherige manuelle Pflege in `responsa.json` ist bei wachsender Dateigröße nicht stabil.

## Neue Zielkategorien

Die neue Q&A-Struktur soll sechs Kategorien verwenden:

- `halacha`
- `tanach`
- `talmud`
- `kabbalah`
- `history`
- `general`

`general` ist der sichere Parkplatz für alles, was nicht zuverlässig zugeordnet werden kann.

## Mindestlogik

### Halacha

Begriffe: Halacha, Responsa, Psak, Din, Shulchan Aruch, Rambam, Tur, Poskim, הלכה, פסק, דין, שולחן ערוך, רמבם, טור, פוסקים.

### Tanach

Begriffe: Tanach, Torah, Neviim, Ketuvim, Pasuk, Parasha, Bereshit, Shemot, Vayikra, Bamidbar, Devarim, Yehoshua, Shmuel, תנך, תורה, נביאים, כתובים, פסוק, פרשה.

### Talmud

Begriffe: Gemara, Talmud, Bavli, Yerushalmi, Daf, Sugya, Mishnah, Baraita, גמרא, תלמוד, בבלי, ירושלמי, דף, סוגיה, משנה, ברייתא.

### Kabbalah

Begriffe: Zohar, Kabbalah, Arizal, Rashash, Sefirot, Ramak, Etz Chaim, זוהר, קבלה, אריזל, רשעש, ספירות, רמק, עץ חיים.

### Geschichte

Begriffe: Geschichte, Chronologie, Personen, Orte, Tempel, Mikdash, Exil, היסטוריה, כרונולוגיה, מקדש, בית המקדש, גלות, חורבן.

### Allgemein

Alles, was nicht sicher zugeordnet werden kann.

## Confidence-Regeln

Sichere Zuordnung:

```json
{ "category": "talmud", "category_confidence": "high" }
```

Unsichere Zuordnung:

```json
{ "category": "tanach", "category_confidence": "low", "needs_review": true }
```

Keine belastbare Zuordnung:

```json
{ "category": "general", "category_confidence": "low", "needs_review": true }
```

## Matching-Regeln

1. Tags sind das stärkste Signal.
2. Ein starker Treffer im Titel darf `high` ergeben.
3. Zwei starke Treffer im Fragetext dürfen `high` ergeben.
4. Ein einzelner Treffer nur im Fragetext ergibt `low`.
5. Schwache Begriffe ergeben nie allein `high`.
6. Gleichstand zwischen mehreren Kategorien ergibt `low`.
7. Unklare Fragen werden nicht blind falsch zugeordnet.
8. Ohne belastbares Signal wird `general` gesetzt.

## Legacy-Mapping

Alte Kategorien werden so überführt:

- `ritual` -> `halacha`
- `civil` -> `halacha`
- `family` -> `halacha`
- `kashrut` -> `halacha`
- `shabbat` -> `halacha`
- `conversion` -> `halacha`
- `halacha-history` -> `history`
- `other` -> `general`
- `Q&A` -> `general`

## Ziel

Kategorien sollen künftig aus einer zentralen `categories.json` kommen. Das Frontend soll die Filter später aus dieser Datei bauen. Das Migrationsskript darf Kategorien nur im Testausgabeordner vorschlagen, nicht in Originaldaten schreiben.
