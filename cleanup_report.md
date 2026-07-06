# cleanup_unused_files — Bericht vom 06.07.2026

Branch: `cleanup-unused-files-2026-07-06`

## Grundlage

Es wurden nur die in `BEREINIGUNGS_ANALYSE.md` als `SICHER` markierten Dateien verarbeitet:

- `update_responsa-OLD.py`
- `test.txt`

Dateien aus der Stufe `WAHRSCHEINLICH` wurden nicht verarbeitet.

## Erstellt

- `cleanup_unused_files.py`
- `_archiv_unused/update_responsa-OLD.py`
- `_archiv_unused/test.txt`
- `cleanup_protokoll_2026-07-06_14-30-00.md`
- `cleanup_report.md`

## Archiviert

| Datei | Ziel |
|---|---|
| `update_responsa-OLD.py` | `_archiv_unused/update_responsa-OLD.py` |
| `test.txt` | `_archiv_unused/test.txt` |

Die Inhalte bleiben im Repository unter `_archiv_unused/` erhalten. Die bisherigen Root-Pfade sind auf diesem Branch nicht mehr vorhanden.

## Nicht verarbeitet

- `qa_db.json`
- `test_local.py`
- `SETUP-ANLEITUNG.html`
- `scripts/`
- `tools/`
- `miyodea/qa/`
- `qa_db/`
- `data/qa/generated/`
- `responsa/`

## Integritätsprüfung

Per GitHub-Dateiabruf geprüft: folgende Kerndateien sind auf dem Branch weiterhin vorhanden:

- `index.html`
- `qa.html`
- `script.js`
- `styles.css`
- `responsa.json`
- `build_qa.py`
- `update_responsa.py`
- `.github/workflows/update-responsa.yml`

Projektstatus: **wirkt intakt**. Es wurden keine produktiven Datenordner und keine Frontend-Kerndateien verändert.

Einschränkung: Ein echter lokaler Serverstart konnte im GitHub-Connector nicht ausgeführt werden. Geprüft wurde die strukturelle Startfähigkeit über vorhandene Hauptdateien.

## Weiter manuell prüfen

1. `qa_db.json` gegen `qa_db/<jahr>.json` per ID-/Zählabgleich prüfen.
2. `test_local.py` öffnen und entscheiden, ob es später ins Archiv gehört.
3. `SETUP-ANLEITUNG.html` auf Verlinkung prüfen.
4. `scripts/` und `tools/` lokal inventarisieren.
5. Danach lokal testen:

```bash
python3 -m http.server
```
