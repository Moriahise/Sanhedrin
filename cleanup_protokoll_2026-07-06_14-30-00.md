# Bereinigungs-Protokoll — 06.07.2026 14:30:00
Modus: EXECUTE / sichere Archivierung über GitHub-Branch `cleanup-unused-files-2026-07-06`

Dieses Protokoll wurde vor dem Entfernen der Root-Dateien aus dem sichtbaren Projektwurzelbereich geschrieben. Die Dateien wurden zuerst nach `_archiv_unused/` kopiert; danach werden die Root-Pfade entfernt, sodass der Inhalt im Archiv erhalten bleibt.

| Datei | Stufe | Größe | SHA-256 | Ziel |
|---|---|---:|---|---|
| update_responsa-OLD.py | SICHER | 7.1 KB | `23e5ea3222fe21d4fcf6a229177629c556ff4cbdcc6009683168d478c55f1ed8` | _archiv_unused/update_responsa-OLD.py |
| test.txt | SICHER | 0 B | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | _archiv_unused/test.txt |

## Nicht einbezogen

Die folgenden Dateien sind in der Analyse nur als wahrscheinlich bzw. weiter zu prüfen markiert und wurden deshalb nicht verschoben:

- `qa_db.json`
- `test_local.py`
- `SETUP-ANLEITUNG.html`

## Schutzliste

Nicht angefasst wurden insbesondere:

- `index.html`
- `qa.html`
- `script.js`
- `styles.css`
- `responsa.json`
- `build_qa.py`
- `update_responsa.py`
- `.github/workflows/update-responsa.yml`
- `responsa/`, `qa_db/`, `data/`, `miyodea/`, `scripts/`, `tools/`
