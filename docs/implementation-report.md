# Implementation and verification evidence

Recorded on 30 September 2026. The original main commit is preserved on `backup/main-before-modernization-2026-09-30-c18ee5c`, pointing to `c18ee5c8771fd0e1e2bb0ee3c72f29d6d25f507a`. Integration is tracked in [PR #4](https://github.com/Moriahise/Sanhedrin/pull/4).

## Delivered behavior

- Durable SQLite state with original records, revisions, source identities, contextual aliases, import ledger, quarantine, cursors and health history. Transactional pages and a process lock prevent partial progress and conflicting writers.
- Versioned static catalogue with complete weighted question/answer search, small browser reads, distinct publication/import filters, Hebrew niqqud normalization, explicit source collision choices and original source attribution.
- Sanitized document/reader pages and image assets, responsive Hebrew/English interface, original responsa paths and a public source-status page.
- Autonomous Stack Exchange and WordPress collectors, enabled official Chabad RSS metadata collection, a Yeshiva source parser and a resumable approved publisher-feed adapter.
- A daily restore → import → collect → verify → build → persist → deploy pipeline, verified GitHub Release recovery snapshots, and an alternative always-on host service.
- The overlapping old writers are removed from scheduling. Original inputs and old root website files are retained for rollback.

## Full-data results

| Independent assertion | Result |
|---|---:|
| Original public IDs retained | 63,051 / 63,051 |
| Original historical aliases retained | 260,640 / 260,640 |
| First-2026 Yeshiva upload records and import charges | 246 / 246 |
| Responsa documents | 17 / 17 |
| Clean repository migration | 64,264 entries |
| Actual local library after live collection | 65,069 entries |
| Repeat migration changed the logical state | No |
| Integrity/preservation errors | 0 |

The post-collection logical hash is `39eb589157d9c51fd711676eb8f7629b2fc12fa0ed88483b7a13d515bd177066`. Counts by provider: Mi Yodeya 41,148; DIN 15,438; Yeshiva 5,502; Chabad 2,407; Aish 557; local documents 17. Live source contents and totals are time-dependent; future verified runs may increase these numbers.

The first Yeshiva import is `data/qa/12yeshiva-qa-database-2026-01-23.json`, with original export time `2026-01-23T14:29:47.817Z`. Each record resolves using its original source context and retains its original URL. This import is not relabeled as the publication year.

## Live source checks

| Source | Result | Requests | Applied operations |
|---|---|---:|---|
| Mi Yodeya | Successful | 129 | 120 inserted; 4,145 updated operations |
| DIN | Successful | 8 | 679 inserted; 3 updated |
| Aish | Successful | 2 | 2 inserted; 2 updated |
| Chabad | Successful | 2 | First run inserted 4; following check updated 4 |
| Yeshiva | Blocked by source | — | HTTP 403; published content retained |

Updated operations can include the same public record checked through activity discovery and older-record rotation; they are not a count of distinct questions. The Chabad feed is `https://www.chabad.org/tools/rss/magazine_rss.xml`, enabled for RSS metadata and original links following the owner's explicit instruction. No claim is made that a separate publisher permission document was received.

## Tests and browser evidence

**47 unit/failure tests pass**, including transactions and cursor rollback, complete native answer reconciliation, acceptance provenance, manual-category preservation, metadata-only updates, contextual alias ambiguity, repeated import prevention, WordPress identity upgrades and source-window validation, XML entity rejection, source host/ID validation, bounded responses, authentication stripping on redirects, quotas/backoff, unsafe HTML/URLs, snapshot corruption, concurrent backup consistency and failed publication recovery.

The complete generated site passes real Chromium navigation and rendering checks: 48 initial cards, working next page, full-answer search, Hebrew niqqud equivalence, separate year filters, source collisions and old `src` links, document text/images, 390-pixel layouts, HTTP failure messages and vanished-version detection. No JavaScript page errors were observed. The live export produced 7,059 `shabbat` matches; `שבת` and `שַׁבָּת` each produced 4,369. Yeshiva import-year 2026 returned 930 records; publication-year 2026 returned 189. These query results can change after later collection.

Export verification checks every generated file hash and unique card count. The measured live export was approximately 424.6 MB before the final release checksum manifest, below the final 900 MB uncompressed budget. Maximum record JSON was 259,306 bytes; maximum token shard was 276,336 bytes. Browser checks require initial resource bodies below 250 KB; the production browser is never asked to load the old monolith. HTML/CSS/JavaScript and Python files use consistent formatting for review and maintenance.

Both Actions workflows pass actionlint 1.7.12, downloaded from its official release and verified against SHA-256. The validation workflow rebuilds from a clean clone, repeats the full-data audit, verifies the export, performs a full database snapshot/restore and runs browser checks. Its reports, screenshots and packed site preview are downloadable under [Validate library](https://github.com/Moriahise/Sanhedrin/actions/workflows/validate.yml).

## Recovery evidence and operational limits

The actual post-collection state snapshot contains 65,069 records and baseline count 63,051. Its uncompressed database was 1,832,701,952 bytes and compressed asset 382,759,601 bytes. Both SHA-256 checksums and the logical hash are recorded in `snapshot.json`; the full snapshot was successfully restored with the same total and logical hash. Restoration validates a separate candidate before replacing the target. Original text revisions, aliases, ledgers and source cursors are part of the database, not ephemeral artifacts.

Yeshiva HTTP 403 remains an external access limitation. DIN/Aish new full bodies require configured permission and verified source structure; current metadata collection preserves legacy full texts. Chabad's magazine feed does not provide a complete historical Q&A catalogue. WordPress offset pagination can shift during concurrent source edits despite overlap and validation. GitHub schedules can be delayed or disabled after prolonged repository inactivity. The always-on server service is prepared but no external host has been provisioned.

Production activation and recovery instructions are in [BETRIEB_DE.md](BETRIEB_DE.md) and [operations.md](operations.md). Integration into main does not itself prove successful Pages deployment; confirm the deployment job and public website separately.
