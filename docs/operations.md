# Operations and recovery

## Production activation

The modernization is delivered through PR #4, with the original main preserved at `backup/main-before-modernization-2026-09-30-c18ee5c` (commit `c18ee5c8771fd0e1e2bb0ee3c72f29d6d25f507a`). Validation runs do not deploy the site; production publication runs on main after integration.

1. Review the complete migration, browser evidence and source limitations in the PR.
2. In repository Settings → Pages, choose **GitHub Actions** as the build/deployment source. Existing root HTML is a rollback path, not the new publication directory.
3. Merge the validated branch. The main push triggers `Publish durable library`; the daily timer runs at 03:17 UTC. Manual `workflow_dispatch` can start a run on main.
4. Optionally configure `STACKEXCHANGE_KEY`. Without it, anonymous API quotas and the configured reserve apply.
5. Check the `health` job and public `status.html`. A partial source failure publishes verified retained content, then marks the health job failed so the failure is visible.

Do not run the old ingestion workflows alongside the new publisher. The branch replaces ten overlapping writers with validation plus one production pipeline. Original scripts and input data remain for inspection and rollback, but are no longer scheduled.

## Source configuration

| Provider | Default operation | Remaining limitation |
|---|---|---|
| Mi Yodeya | Official API, complete native answers, attribution and verified acceptance | API quota/backoff; rotating older checks are not a promise of daily full-library refresh |
| DIN | WordPress metadata and original links | Full body mode requires documented permission; markers must match source structure |
| Aish | WordPress metadata, Ask The Rabbi category 3504 | Same permission requirement for full bodies |
| Chabad | Enabled official magazine RSS, metadata and original links | Covers magazine items, not a complete historical Q&A feed; no full-article scraping |
| Yeshiva | Existing-item metadata checks and optional approved discovery feed | Direct live requests can return HTTP 403; default has no invented discovery endpoint |

Chabad activation records the owner's instruction dated 2026-09-30 and the scope **RSS metadata and original links**. This is the owner's authorization record, not a claim that a separate Chabad permission document was received. Feed URL: `https://www.chabad.org/tools/rss/magazine_rss.xml`. The live adapter was successfully exercised against this endpoint. Existing Chabad article bodies remain intact, and `article.asp?aid=...` IDs resolve to the same source identity as `/aid/...` links.

To use a publisher-provided API/feed for reliable Yeshiva discovery or permitted full texts, configure `adapter: "json_feed"`, a real HTTPS `endpoint`, allowlisted `hosts`, a request budget, `mode` and a `permission_reference` for full mode. Optional `token_env` binds a bearer token to the endpoint host. Add its secret to the execution environment; the supplied Actions workflow only passes the optional Stack Exchange key until another source credential is explicitly configured.

Expected envelope:

```json
{
  "schema": 1,
  "items": [
    {"title": "Original title", "url": "https://www.yeshiva.org.il/ask/137101", "published_at": "2026-01-23", "question": "Permitted original body", "answers": [{"text": "Permitted original answer"}]}
  ],
  "next": null,
  "cursor": "opaque-publisher-checkpoint"
}
```

A paginated `next` must be an allowlisted absolute HTTPS URL. Metadata mode strips supplied bodies. Complete page data and the resume cursor commit together. The default cursor query parameter is `cursor`; publishers can configure another name. Never add guessed endpoints or bypass an access challenge.

## Durable state

The SQLite database is excluded from git. **GitHub Releases are the production recovery store**, not runner caches or short-lived artifacts. Each state release contains `library.sqlite.gz` and `snapshot.json` with compressed/database SHA-256, sizes, total, baseline count and logical hash. The publisher restores the newest non-draft state tag and refuses an incomplete or corrupt latest release. It does not silently reset to the repository baseline after a restore error.

A new state release is written **before** Pages deployment. If deployment fails, the previous site remains available and the newest verified collection state is recoverable. Per-asset release size is limited to 2 GiB; publication refuses oversized state. Restoration has a 5 GB decompressed database bound and minimum total 63,051. No automatic release deletion is enabled. Define retention and off-site copies before long-term growth makes storage expensive; preserve multiple independently verified recovery points.

```bash
.venv/bin/python -m sanhedrin snapshot --directory .sanhedrin/snapshot
.venv/bin/python -m sanhedrin restore --directory .sanhedrin/snapshot
.venv/bin/python -m sanhedrin verify
```

Close other database connections and stop the publisher before restoration. The CLI lock covers all its commands. Restoration validates a temporary candidate before atomic replacement. Do not manually overwrite a live database or delete its WAL while a process holds it.

For GitHub state operations, `gh` and `GH_TOKEN` are needed:

```bash
.venv/bin/python -m sanhedrin restore-release --repo Moriahise/Sanhedrin --directory .sanhedrin/restore
```

## Always-on host alternative

GitHub can disable schedules on public repositories after 60 days without repository activity. If uninterrupted schedules are required, deploy the provided systemd service/timer on an approved Linux host and choose it as the sole publisher.

Create a `sanhedrin` system user, install the repository and virtual environment under `/srv/sanhedrin/repository`, initialize writable `/var/lib/sanhedrin` and `/srv/sanhedrin/public`, and optionally place source credentials in root-controlled `/etc/sanhedrin/collector.env`. Install the two units in `ops/systemd/`, reload systemd and enable the timer. The service publishes complete version directories and switches `public/current` only after build verification and a state snapshot. Point the web server at `/srv/sanhedrin/public/current`. This repository prepares the service; no external host has been provisioned.

Retain and monitor `state/reports/latest-run.json`, snapshots and previous site versions. Source partial status is exit 2 and is recorded in the report; the provided unit accepts it as a completed publication. Add host-specific monitoring of the report for source failures, and external uptime monitoring for service/publishing failures. Do not enable both Actions and this host as independent writers.

## Practical limits

Static search has no server-side accounts or editing interface. Source metadata can change after collection; a visible check date is not a guarantee of present-day source availability. Original bodies are retained, while new full-text collection is gated by configured permission and technical access. The 900 MB site budget and snapshot asset bound deliberately fail closed before exceeding deployment/storage constraints.
