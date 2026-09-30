# Supplied browser-extension references

Seven supplied archives were inspected as references. Their original ZIPs were not modified or embedded into production. Their SHA-256 and internal file names are recorded in [extension-references.json](extension-references.json).

| Archive | Relevant behavior | Current integration |
|---|---|---|
| `yeshiva-extension-v1.2.zip` | Source IDs/URLs, question and answer selectors, browser export timestamps | Durable source-specific identity, Yeshiva JSON-LD/body parser and approved publisher-feed contract |
| `din-extension-v3.zip` | Extracted Hebrew question/answer structure and metadata | WordPress metadata collector; fail-closed full-text parser when permission is configured |
| `aish-extension-v2.zip` | Ask The Rabbi structure and article/answer distinction | WordPress Ask The Rabbi category collector and explicit reply markers |
| `chabad-extension.zip` | Native article IDs, full article text often stored in answer fields | Preserved article classification and texts; manual JSON import, RSS collection disabled |
| `AISH_JSON_SPLITTER_GITHUB_V3.zip` | Export part/manifest convention | Import ledger accepts supplied original parts and excludes split manifests |
| `CHABAD_JSON_SPLITTER_GITHUB_V2.zip` | Split archive format | Same repeatable manual-upload import path |
| `DIN_JSON_SPLITTER_GITHUB_V3.zip` | Split archive format | Same repeatable import path; no append to the runtime monolith |

Current owner policy: **Mi Yodeya is collected automatically**, without an open browser or manual export. **Yeshiva, DIN, Aish and Chabad are collected manually with the supplied extensions.** Their JSON exports and splitter content parts are accepted under their prepared `data/qa/<provider>/` folders; a commit on main triggers automatic import and publication. See [UPLOADS_DE.md](UPLOADS_DE.md). Disabling live collection does not disable manual imports or remove historical texts.

The 25 supplied architecture/migration/search/upload files were also considered. Permanent public IDs and context-aware legacy links remain. Three old assumptions are corrected: source labels do not override the actual source URL, import date is not a publication date, and the first answer is not automatically treated as accepted. Existing source-confirmed/manual categories remain; new automatic classifications require unambiguous source tags and uncertain entries keep their review flag.

Generated cleanup examples are reference reports, not permission to remove published data. No historical input archive or responsa document is deleted by this modernization.
