# Sanhedrin

A Hebrew and English library of Jewish questions, answers and responsa, with original source links and full-text search.

This modernization preserves the published library while replacing manual browser-extension exports and the `responsa.json` runtime index. The original 63,051 public IDs remain valid. A clean repository migration produces **64,264 entries**, including **17 documents**, with all **246 records from the first Yeshiva upload of 2026**. Live collection can increase this total.

The catalogue searches questions **and answers**. Publication year and import year are separate filters. Hebrew search ignores niqqud; controlled English spelling variants are supported. Dashed cards indicate that a category needs review. Only a complete remote source check can establish that a question has no answers.

## Run locally

Python 3.12 or newer is required. Install and run from the repository root:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-test.txt
.venv/bin/python -m sanhedrin migrate
.venv/bin/python tools/audit_library.py --repeat
.venv/bin/python -m sanhedrin sync
.venv/bin/python -m sanhedrin build
.venv/bin/python -m sanhedrin verify-export
.venv/bin/python -m http.server 8000 --directory dist
```

Open `http://localhost:8000`. The `sync` command returns 2 when a source fails or defers; successful pages are retained, other sources continue, and building can proceed. Exit 1 indicates a failed command. The repository root still contains the original site for rollback; **serve the generated `dist` directory** for the modernized site.

## Autonomous publication

One daily GitHub Actions publisher restores the latest verified database snapshot from GitHub Releases, imports changed local files, checks configured sources, verifies all original IDs, builds the website, saves a new recovery snapshot and deploys the generated `dist` artifact. The schedule is **03:17 UTC**. Set GitHub Pages → Build and deployment → Source to **GitHub Actions** before production activation. Optional secret: `STACKEXCHANGE_KEY`.

Chabad RSS metadata collection is **enabled**, following the owner's authorization on 30 September 2026, using the official magazine feed. Mi Yodeya uses the Stack Exchange API with native answer IDs, verified acceptance and attribution. DIN and Aish currently collect metadata through their verified WordPress APIs. Yeshiva direct checks can return HTTP 403; a permitted publisher feed is required for reliable new-item discovery. Full-text adapters require an explicit permission reference in configuration.

An always-on Linux host can use the provided systemd service and timer instead of GitHub Actions. Select one publisher; do not run both against independent state.

## Verification

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/audit_library.py --repeat
.venv/bin/python -m playwright install chromium
.venv/bin/python tools/browser_checks.py
```

The full-data audit independently checks original IDs, historical aliases, first-2026 Yeshiva import charges and documents. Browser checks exercise full search, source collisions, old links, pagination, mobile layout and failed network requests. Recovery validates both snapshot checksums, database integrity, revisions and catalogue cardinality before replacing state.

- [Deutsche Anleitung](docs/BETRIEB_DE.md)
- [Architecture](docs/architecture.md)
- [Operations, activation and recovery](docs/operations.md)
- [Extension references](docs/extensions.md)
- [Implementation evidence](docs/implementation-report.md)

Original archives, chunks and `responsa.json` remain migration inputs. The new website does not fetch them, and the publisher does not rewrite them.
