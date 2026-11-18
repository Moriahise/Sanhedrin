# Shekhina discovery
The daily maintenance job reads the public featured lesson at Shiurim, validates both languages, extracts its guiding question, opening paragraph, discussion questions and sources, and preserves earlier sheets at stable addresses. The repository snapshot includes two original source-reading exercises. The main site build copies verified bytes from published/ into its staging directory. A failed external fetch cannot replace the last selection. The existing catalogue and storage limits still govern deployment.

Run Python 3.12 with lxml installed. From the repository root:
```sh
python visibility/run.py refresh
python visibility/run.py materialize
python visibility/run.py check
python -m unittest discover -s visibility -p 'test_*.py'
```
The maintenance workflow writes only the snapshot, its inputs and its IndexNow ledger. A normal non-forced push preserves concurrent edits. The independently scheduled Pages build picks up the latest committed snapshot. After a successful publication, the notifier compares live fingerprints, checks the live key and changed sheet bytes, and submits changed or removed URLs to IndexNow. A failed notification is retried on the next run. Keep the verification file public: its purpose is to prove control of the host.

Google Search Console uses an existing verified property and OAuth permission for the Webmasters API. If configured, GSC_CLIENT_ID, GSC_CLIENT_SECRET and GSC_REFRESH_TOKEN are repository secrets; GSC_PROPERTY is an optional variable (default sc-domain:shekhina.org). The program registers the sitemap if missing and reads 28 complete days ending three days ago. It orders evergreen sheets by smoothed click-through rate only when each has at least 30 impressions and there is at least one click. Without sufficient evidence it returns to the editorial order. Weekly sheets keep their dates. Training permissions, website code and other repositories are outside the ranking loop.

RSS feeds at /learn/he/feed.xml and /learn/en/feed.xml can be subscribed to without registration. Search impressions, citation counts, confirmed group use and repeat group use are separate measurements. Never infer attendance from requests, feed subscriptions or links. The monthly review can use voluntary feedback supplied to the operator. Do not commit names, emails, private group identities, secrets or individual search queries to this repository.

To pause changes to the selection, disable the Maintain Shekhina discovery workflow. The published snapshot remains available. To recover a faulty selection, restore only visibility/weekly.json, visibility/priority.json (if present) and visibility/published/ from a verified commit, rerun the check and publish through the normal site workflow.

Each daily run also checks the public revision, crawl entry points, both RSS feeds, each language hub, the featured sheet, a rotating historical sheet, and the English and Hebrew inbound links from Moriah and Shiurim. A public deployment check runs again after the normal publisher succeeds. Technical observations for the last 53 ISO weeks are in `visibility/state/observations.json`. To run the check locally, use `python visibility/observe.py`.

Readers of a sheet may voluntarily confirm a session using the bilingual public GitHub reporting link. Both checkboxes are initially empty. Only a checked session with a known sheet identifier counts. The report can also indicate that the same learning partners have previously studied another sheet. Weekly totals count reports and repeated sessions, never unique people or institutions. GitHub displays the submitter's username publicly. The aggregate stores no account details. The program closes the previous week's count on the next successful run.
