# RFP Scout

Twice-weekly automated scan for tenders, RFPs and open calls in **art production, exhibition production and cultural project management** that a Vietnam-registered LTD (Officine Gặp / Gặp Art Services) could answer. Asia and SEA first, plus known publishers in the Gulf and Central Asia (DBF, ACDF, Qatar Museums, UNESCO offices, NAC Singapore, WKCDA…).

Live digest: **https://almusallah.github.io/rfp-scout/**

Observer-only: it reads, classifies, publishes the page, emails the founders when something fits. It never applies or contacts anyone.

| File | Role |
|---|---|
| `sources.json` | the portals and news queries (edit to add one) |
| `PROFILE.md` | what counts as fit / watch / reject |
| `RUN.md` | the runbook the cloud routine follows |
| `scripts/harvest.py` | stdlib-only fetcher + keyword filter + dedup against `state.json` |
| `scripts/text.py` | page → plain text (≤ 2,500 chars) for the few fits that need reading |
| `scripts/commit_verdicts.py` | merges the agent's verdicts into `state.json` (everything seen once is never re-reported) |
| `scripts/build_page.py` | renders `docs/index.html` |
| `state.json` | canonical memory (items + seen keys) |
| `LOG.md` | one line per run |

Run locally: `python3 scripts/harvest.py` then classify `runs/new_candidates.json` into `runs/verdicts.json`, then `python3 scripts/commit_verdicts.py && python3 scripts/build_page.py`.

Cloud routine: `rfp-scout-twice-weekly`, Mon + Thu 01:00 UTC (08:00 ICT), environment `bkk-scraper` (full egress), model Sonnet, Gmail connector attached for the alert email only.
