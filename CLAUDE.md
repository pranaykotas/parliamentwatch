# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ParliamentWatch** tracks Indian Parliamentary Committee reports from sansad.in. It scrapes report metadata via the sansad.in REST API, downloads PDFs, extracts text, and summarizes key findings using the Claude API. Works without an API key (shows text preview instead of AI summary).

## Architecture

```
cli.py           → Entry point (argparse CLI)
scraper.py       → Fetches report metadata from sansad.in API + search
jpc.py           → Discovers and tracks Joint Parliamentary/Select Committees (dynamic, not in config.py)
pdf_utils.py     → Downloads PDFs and extracts text (pypdf)
summarizer.py    → Summarizes reports via Claude API (with text preview fallback)
notifier.py      → Detects new reports (DRSCs + JPCs), formats email notifications
exporter.py      → Exports data to CSV or Markdown
config.py        → Committee mappings, API codes, paths (loaded from .env)
```

**Data flow:** `scraper.py` → `data/reports.json` → `pdf_utils.py` → `data/text/` → `summarizer.py` → `data/summaries/`

## Key Technical Details

- **Two APIs, one per house** — sansad.in serves LS and RS committee reports from different endpoints. `scraper.py` dispatches based on each committee's configured `house` field:
  - **LS-chaired (16 DRSCs + 3 Financial Committees):** `GET /api_ls/committee/lsRSAllReports` with `house=L`, `committeeCode`, `lsNo`, `page`, `size`, `sortOn`, `sortBy`. Schema uses PascalCase fields (`SubjectOfTheReport`, `LaidInRS`, etc.). The Financial Committees (`public_accounts`=26, `estimates`=10, `public_undertakings`=27) aren't departmentally related — mixed LS+RS membership, but administered solely by the Lok Sabha Secretariat, found via `sansad.in/ls/committee/financial-committees` — they use this same endpoint/schema, tagged `"category": "financial"` in `DRSC_COMMITTEES`.
  - **Joint Parliamentary / Select Committees (`jpc.py`):** a separate, *dynamically discovered* registry — not in `DRSC_COMMITTEES`, since JPCs form and dissolve per Bill and a hardcoded list would go stale (codes 67-86 as of Sept 2026, but growing). `jpc.discover_jpc_committees()` scrapes `sansad.in/ls/committee/other-committees` for the current code/name list on every run and merges into `data/jpc_committees.json` (old entries are never dropped, even once a dissolved JPC disappears from that hub page). Reports fetched the same way as LS DRSCs (`scraper._fetch_ls_committee_reports(key, lok_sabha, committee=...)`, `committee` passed explicitly since these aren't in `DRSC_COMMITTEES`) and merged into the same `data/reports.json` under keys like `jpc_79` — `search_reports()` and `load_existing_reports()` pick them up automatically since they just iterate whatever keys exist. `notifier.check_for_new_reports()` calls `jpc.detect_new_jpc_reports()` on every full run (not on a `--committees`-scoped one), so new JPC reports — and newly-formed JPCs — surface in the daily email automatically. The Streamlit app's Committee Deep Dive dropdown and Export tab are still scoped to `DRSC_COMMITTEES` only (JPCs don't have a fixed membership list to browse by); Search (title and full-text) covers them.
  - **RS-chaired (8 committees):** `GET https://integration.rajyasabha.digital/committee-integration/api/v1/web/committee-reports` with the same params as before (`mstCommId`, `departmentId`, `presentationYear`, `search`, `page`, `size`, `sortOn`, `sortBy`, `locale`), but the response is nested one level deeper: `{"success": true, "data": {"_metadata": {...}, "records": [...]}}` instead of `{"_metadata": ..., "records": ...}` at the top level. Schema is otherwise unchanged (camelCase fields: `subjectOfTheReport`, `urlHindi`, `dateOfPresentation` in `DD/MM/YYYY`). No auth required.
    - **Why the domain changed (found Sept 2026):** sansad.in's own legacy endpoint (`{BASE_URL}/api_rs/committee/committee-reports`, kept as `RS_REPORTS_API_LEGACY` in `config.py`) silently stopped receiving new data sometime around Q1-Q2 2026 — every RS DRSC's most recent report there is stuck between March and June 2026, while real reports keep being presented (e.g. report #415, Science committee, presented 7 Aug 2026, missing entirely from the legacy endpoint). Rajya Sabha has since moved report hosting to `rajyasabha.digital` (PDFs served from `bucketapi.rajyasabha.digital`), and sansad.in's own frontend now calls `integration.rajyasabha.digital` for RS committee data — found via that endpoint's CSP header (`connect-src` on `sansad.in/rs/committees/{id}`) and by extracting the actual API call from `sansad.in`'s Next.js JS bundle for the committee page. If RS data goes stale again, this is the first thing to check — sansad.in may migrate the endpoint again.
    - LS's `api_ls` endpoint shows no equivalent staleness — as of Sept 2026 it's current to within ~4 weeks. This gap has so far only affected RS.
- **`mstCommId`** for RS committees is the integer in `/rs/committees/{id}` URLs. Stored in `DRSC_COMMITTEES[key]["mst_comm_id"]`.
- **`api_code`** for LS committees maps to the api_ls `committeeCode` param. Some `api_code` values clash between LS and RS committees (e.g. 18 = Communications LS / Personnel RS) — never fetch a committee with the wrong house.
- **Parallel fetching**: `scrape_all_committees` and `detect_new_reports` both fan out via `ThreadPoolExecutor` (10 workers). Full 27-committee scrape: ~3–5 seconds.
- **`--scrape` needs `--house` omitted (or both explicitly run) to get everything** — `--house` filters to one house when passed; omitting it now defaults to both (fixed Sept 2026 — it used to silently default to `L` only, so a plain `--scrape` quietly skipped every RS committee with no error). `--check-new` (used by the daily Action) has no such filter and always checks all committees.
- **PDF URLs** follow the pattern: `https://sansad.in/getFile/app/lsscommittee/{Committee}/{lsNo}_{Committee}_{ReportNo}.pdf?source=app` for LS; for RS they live under `getFile/rsnew/Committee_site/...`.
- All data is cached: PDFs in `data/pdfs/`, extracted text in `data/text/`, summaries in `data/summaries/`.
- Config values load from `.env` via python-dotenv. Paths default to `{script_dir}/data/`.

## Common Commands

```bash
source .venv/bin/activate

# Discovery
python cli.py --list-committees              # List all 16 DRSCs
python cli.py --committee defence            # Browse all reports for a committee
python cli.py --search "budget"              # Search report titles across all committees
python cli.py --search "grants" --committee finance  # Search within one committee

# Query a specific report (downloads PDF, extracts text, summarizes or previews)
python cli.py --committee defence --report 23

# Scraping
python cli.py --scrape                       # Scrape all committees (current LS)
python cli.py --scrape --committees defence,finance
python cli.py --scrape --lok-sabha 17        # Historical Lok Sabha
python cli.py --scrape --house R             # Rajya Sabha committees

# Export
python cli.py --export csv                   # All reports to data/reports.csv
python cli.py --export markdown --committee finance  # One committee to data/reports.md

# Monitoring
python cli.py --check-new                    # Detect new reports vs stored data
python cli.py --check-new --committees defence,finance
```

## Setup

1. `python3 -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `cp .env.example .env` and configure:
   - `LLM_PROVIDER` — `anthropic` (default) or `openai` (also works for Gemini, Ollama, etc.)
   - `LLM_API_KEY` — API key for the chosen provider (falls back to `ANTHROPIC_API_KEY`)
   - `LLM_MODEL` — model name (defaults: `claude-sonnet-4-20250514` for Anthropic, `gpt-4o` for OpenAI)
   - `LLM_BASE_URL` — custom endpoint for OpenAI-compatible APIs (Gemini, Ollama, LM Studio)
   - `NOTIFICATION_EMAIL` / `SENDER_EMAIL` — for email alerts
   - `LOK_SABHA_NUMBER` — defaults to 18
   - `DATA_DIR` — custom data storage path

## API Response Schema

Each record from the sansad.in API has these fields:
- `url` / `urlH` — PDF download links (English / Hindi)
- `SubjectOfTheReport` / `SubjectOfTheReportH` — report title
- `reportNo` — integer report number
- `CommitteeName` / `CommitteeNameH` — committee name
- `Loksabha` — Lok Sabha number (e.g. 18)
- `PresentedInLS` / `LaidInRS` — date strings like "18-Mar-2026"
- `PresentedToSpeaker`, `dateOfAdoption`, `dateOfPresentation` — often null

## Known Limitations

- **Flat storage by committee key**: `data/reports.json` is keyed by committee name. Scraping a different Lok Sabha (`--lok-sabha 17`) overwrites the same key. Historical data is not preserved alongside current data.
- **Title-only search**: `--search` matches against report titles, not full-text PDF content. The Streamlit app supports full-text search across extracted reports.

## Email Notifications

Automated monitoring runs via GitHub Actions (`.github/workflows/check-reports.yml`):
- Runs daily at 10:00 AM IST
- Checks sansad.in for new reports, compares against stored data
- Sends email via SMTP if new reports are found
- Commits updated `data/reports.json` back to the repo

**GitHub Secrets required:** `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `NOTIFICATION_EMAIL`

Manual email can also be sent via Claude Code's Google Workspace MCP integration (pranay@takshashila.org.in).
