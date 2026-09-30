# Supplied browser-extension references

Seven supplied archives were inspected as references. Their original ZIPs were not modified or embedded into production. Their SHA-256 and internal file names are recorded in [extension-references.json](extension-references.json).

| Archive | Relevant behavior | Replacement |
|---|---|---|
| `yeshiva-extension-v1.2.zip` | Source IDs/URLs, question and answer selectors, browser export timestamps | Durable source-specific identity, Yeshiva JSON-LD/body parser and approved publisher-feed contract |
| `din-extension-v3.zip` | Extracted Hebrew question/answer structure and metadata | WordPress metadata collector; fail-closed full-text parser when permission is configured |
| `aish-extension-v2.zip` | Ask The Rabbi structure and article/answer distinction | WordPress Ask The Rabbi category collector and explicit reply markers |
| `chabad-extension.zip` | Native article IDs, full article text often stored in answer fields | Preserved article classification and texts; enabled official RSS metadata adapter |
| `AISH_JSON_SPLITTER_GITHUB_V3.zip` | Export part/manifest convention | Import ledger accepts supplied original parts and excludes split manifests |
| `CHABAD_JSON_SPLITTER_GITHUB_V2.zip` | Split archive format | Same repeatable import path; no manual splitting in autonomous operation |
| `DIN_JSON_SPLITTER_GITHUB_V3.zip` | Split archive format | Same repeatable import path; no append to the runtime monolith |

The new publisher does not require an open browser, a logged-in extension session, IndexedDB, manual exports or manual GitHub uploads. Old JSON exports remain accepted as migration inputs. Full historical source text already present is preserved even when a current adapter only collects metadata.

The 25 supplied architecture/migration/search/upload files were also considered. Permanent public IDs and context-aware legacy links remain. Three old assumptions are corrected: source labels do not override the actual source URL, import date is not a publication date, and the first answer is not automatically treated as accepted. Existing source-confirmed/manual categories remain; new automatic classifications require unambiguous source tags and uncertain entries keep their review flag.

Generated cleanup examples are reference reports, not permission to remove published data. No historical input archive or responsa document is deleted by this modernization.
