# ParliamentWatch 🏛️

**Track, search, and summarize Indian Parliamentary Committee reports — all in one place.**

ParliamentWatch pulls reports from [sansad.in](https://sansad.in) (the official Indian Parliament website), lets you browse and search them, and uses AI to generate plain-English summaries. It covers all 24 Departmentally Related Standing Committees (DRSCs) — 16 chaired by Lok Sabha members and 8 chaired by Rajya Sabha members.

> **No API key required to get started.** You can browse, search, and read reports without any setup. AI summaries are optional — and you can use free providers like Ollama, Gemini, or Groq.

### Try It or Run Your Own

- **[Live Demo](https://parliamentcommittee.streamlit.app)** — browse, search, and try out AI summaries instantly. The demo resets between sessions, so summaries won't persist.
- **Fork & run locally** — for researchers who want persistent summaries, historical data, and full control. Clone the repo, run `streamlit run app.py`, and everything is cached to your disk. This is the recommended way to use ParliamentWatch for serious work.

---

## Why This Exists

In India's parliamentary democracy, **Departmentally Related Standing Committees (DRSCs)** are the most robust institutional mechanism through which the legislature exercises control over the executive. There are **24 DRSCs** — 16 chaired by Lok Sabha members and 8 chaired by Rajya Sabha members — each shadowing a cluster of central government ministries. Together, they cover every arm of the Union Government.

These committees examine:
- **Demands for Grants** — scrutinising how each ministry proposes to spend public money
- **Bills** referred to them by Parliament — providing detailed clause-by-clause analysis
- **Policy subjects** — investigating issues of national importance on their own initiative

Their reports are non-partisan, evidence-based documents that draw on testimonies from government officials, domain experts, and field visits. Unlike floor debates, committee proceedings allow for sustained, in-depth engagement with policy questions.

**Yet these reports remain under-accessed.** They are buried across government websites with no unified search, no alerts for new publications, and no easy way to quickly grasp what a 200-page PDF says.

ParliamentWatch fixes that.

### Official Sources and Further Reading

- **[ePARLIB](https://eparlib.sansad.in/)** — the government's official digital archive of parliamentary papers, including committee reports, debates, questions, and more
- **[PRS Legislative Research](https://prsindia.org/)** — an independent research organisation that tracks Parliament, analyses Bills and committee reports, and publishes accessible summaries. The gold standard for expert commentary on parliamentary functioning.

ParliamentWatch complements these resources by making it easier to *discover*, *search*, and *summarise* committee reports using AI.

---

## What You Can Do

| Feature | Needs API Key? |
|---------|---------------|
| Browse all reports for any of the 24 DRSCs | No |
| Search report titles by keyword | No |
| Full-text search across extracted PDFs | No |
| Search across multiple Lok Sabhas at once | No |
| Download report PDFs (English & Hindi) | No |
| Extract and read full text from PDFs | No |
| Sort and filter by date, category, or Lok Sabha | No |
| Color-coded report categories (DFG, Action Taken, Bills, etc.) | No |
| Export metadata, summaries, or text to CSV/Markdown | No |
| Fetch all historical data (LS 14–18) in one click | No |
| Get daily email alerts for new reports | No |
| **AI-powered summaries of reports** | **Yes (free options available)** |
| **Batch-summarize all extracted reports for a committee** | **Yes (free options available)** |

---

## Getting Started

### Step 1: Download the code

```bash
git clone https://github.com/pranaykotas/parliamentwatch.git
cd parliamentwatch
```

### Step 2: Set up Python

You need Python 3.9 or later. If you're not sure, run `python3 --version` in your terminal.

```bash
python3 -m venv .venv
source .venv/bin/activate        # On Mac/Linux
# .venv\Scripts\activate         # On Windows
pip install -r requirements.txt
```

### Step 3: Launch the app

```bash
streamlit run app.py
```

This opens a browser window at `http://localhost:8501`. That's it — you're running ParliamentWatch!

> **Why run locally?** The [live demo](https://parliamentcommittee.streamlit.app) is great for a quick look, but downloaded PDFs, extracted text, and AI summaries don't persist between sessions on the cloud. When you run locally, everything is cached to your disk — summarize a report once and it's there forever.

### Step 4: Fetch data

Click **"Fetch All Committees"** in the sidebar. This pulls the latest report listings from sansad.in. With parallel fetching, all 24 committees come back in 3–5 seconds.

Want historical data too? Use **"Fetch All Historical Data"** to download reports from Lok Sabhas 14–18 (2004 to present) in one go. Data is merged — nothing gets overwritten.

---

## Using the Web App

The app has five tabs:

### Dashboard
An overview showing:
- Total reports, committees with data, and recent publications
- Lok Sabha filter — view one LS or all at once
- Color-coded category badges (Demand for Grants, Action Taken, Bills, Assurances, Subject Reports)
- Committee table with progress indicators (text extracted / summarized)

Click on any report title to see its details, download links, and generate an AI summary.

### Committee Deep Dive
Pick a committee and optionally a Lok Sabha. You'll see all its reports in a sortable table — sort by date or report number, filter by category or keyword. Each report expander shows:
- Full title, dates, PDF links
- Extract & Summarize button
- Cached summary if available

Use the **"Summarize All"** button to batch-summarize all extracted reports for that committee in one click.

### Search
Two search modes:
- **Titles only** — fast keyword search across all report titles
- **Titles + Full text** — searches inside extracted PDF text too

Filter by committee or Lok Sabha. Search results show summary previews where available.

### Export
Download your data in three formats:
- **Report metadata** — titles, dates, committees (CSV)
- **AI summaries** — all generated summaries (Markdown or CSV)
- **Extracted text** — full text from all extracted PDFs

Individual summaries can also be downloaded directly from any report dialog.

### The Why?
Background on why parliamentary committees matter, what makes this tool different, and links to official sources (ePARLIB) and expert analysis (PRS Legislative Research).

---

## AI Summaries (Optional)

The sidebar has an **"AI Summarization"** section where you can pick a provider and enter an API key. Summaries are generated on-demand when you click "Generate Summary" on a report.

### Free Options

You don't need to pay anything to use AI summaries:

| Provider | Cost | Setup |
|----------|------|-------|
| **Ollama** | Free (runs on your computer) | [Install Ollama](https://ollama.com), then run `ollama pull llama3.2` |
| **Google Gemini** | Free tier (15 requests/min) | Get a free key at [Google AI Studio](https://aistudio.google.com/apikey) |
| **Groq** | Free tier (very fast) | Sign up at [console.groq.com](https://console.groq.com/keys) |
| **OpenRouter** | Free models available | Sign up at [openrouter.ai](https://openrouter.ai/keys) |

### Paid Options

| Provider | Notes |
|----------|-------|
| **Anthropic (Claude)** | Best quality summaries. Get a key at [console.anthropic.com](https://console.anthropic.com) |
| **OpenAI (GPT)** | Get a key at [platform.openai.com](https://platform.openai.com/api-keys) |
| **OpenCode Zen** | Unified gateway to Claude, GPT, Gemini, Qwen and more on a single key. Get a key in your [OpenCode workspace](https://opencode.ai). |

### Using Ollama (completely free, no account needed)

1. Install Ollama from [ollama.com](https://ollama.com)
2. Open a terminal and run: `ollama pull llama3.2`
3. Keep Ollama running in the background
4. In ParliamentWatch, select **"Ollama (local, no key)"** from the provider dropdown
5. Click "Generate Summary" on any report — it runs entirely on your machine

### Privacy

Your API key stays in your browser's session memory only. It is sent directly to your chosen LLM provider and nowhere else. Nothing is logged, stored on disk, or transmitted to our servers. The key is automatically erased when you close the tab. The app is fully [open source](https://github.com/pranaykotas/parliamentwatch) — you can verify this yourself.

---

## Command Line Interface

Everything the web app does is also available from the terminal:

```bash
# List all 24 committees
python cli.py --list-committees

# Browse a committee's reports
python cli.py --committee defence

# Search by keyword
python cli.py --search "budget"
python cli.py --search "grants" --committee finance

# Read and summarize a specific report
python cli.py --committee defence --report 23

# Download metadata for all committees
python cli.py --scrape

# Scrape specific committees only
python cli.py --scrape --committees defence,finance

# Rajya Sabha committees
python cli.py --scrape --house R

# Historical data (e.g. 17th Lok Sabha) — merges with existing data
python cli.py --scrape --lok-sabha 17

# Export to CSV or Markdown
python cli.py --export csv
python cli.py --export markdown --committee finance

# Check for newly published reports
python cli.py --check-new
```

For the CLI, configure your LLM API key in a `.env` file:

```bash
cp .env.example .env
# Edit .env with your preferred provider and key
```

---

## Email Alerts

ParliamentWatch can email you when new reports are published. This runs automatically via GitHub Actions — once a day at 10:00 AM IST, it checks sansad.in for new reports and sends an email if anything is new.

### Setting up email alerts

1. Fork this repository on GitHub
2. Go to **Settings → Secrets and variables → Actions**
3. Add these secrets:

| Secret | Value |
|--------|-------|
| `SMTP_SERVER` | `smtp.gmail.com` (for Gmail) |
| `SMTP_PORT` | `587` |
| `SMTP_USERNAME` | Your Gmail address |
| `SMTP_PASSWORD` | A [Gmail App Password](https://support.google.com/accounts/answer/185833) (not your regular password) |
| `NOTIFICATION_EMAIL` | Where to receive alerts |

The workflow runs automatically. You can also trigger it manually from the **Actions** tab.

---

## Committees Covered

All 24 Departmentally Related Standing Committees of the Indian Parliament:

**Lok Sabha chaired (16)**

| Committee | Key (for CLI) |
|-----------|--------------|
| Agriculture, Animal Husbandry and Food Processing | `agriculture` |
| Chemicals & Fertilizers | `chemicals` |
| Coal, Mines and Steel | `coal` |
| Communications and Information Technology | `communications` |
| Consumer Affairs, Food and Public Distribution | `consumer_affairs` |
| Defence | `defence` |
| Energy | `energy` |
| External Affairs | `external_affairs` |
| Finance | `finance` |
| Housing and Urban Affairs | `housing` |
| Labour, Textiles and Skill Development | `labour` |
| Petroleum & Natural Gas | `petroleum` |
| Railways | `railways` |
| Rural Development and Panchayati Raj | `rural_development` |
| Social Justice & Empowerment | `social_justice` |
| Water Resources | `water_resources` |

**Rajya Sabha chaired (8)**

| Committee | Key (for CLI) |
|-----------|--------------|
| Commerce | `commerce` |
| Education, Women, Children, Youth and Sports | `education` |
| Health and Family Welfare | `health` |
| Home Affairs | `home_affairs` |
| Industry | `industry` |
| Personnel, Public Grievances, Law and Justice | `personnel` |
| Science and Technology, Environment and Forests | `science` |
| Transport, Tourism and Culture | `transport` |

---

## How It Works

```
sansad.in API  →  scraper.py  →  data/reports.json  (metadata)
                                       ↓
                                  pdf_utils.py  →  data/pdfs/    (PDFs)
                                       ↓              ↓
                                                  data/text/     (extracted text)
                                       ↓
                                  summarizer.py →  data/summaries/ (AI summaries)
```

- **scraper.py** calls the sansad.in REST APIs to fetch structured report metadata. Lok Sabha–chaired committees use `api_ls/committee/lsRSAllReports`; Rajya Sabha–chaired committees use `api_rs/committee/committee-reports` (the LS endpoint returns stale, pre-2016 data for RS committees). All 24 committees are fetched in parallel for speed. Data from different Lok Sabhas is merged, not overwritten.
- **pdf_utils.py** downloads PDFs and extracts text using pypdf
- **summarizer.py** sends extracted text to your chosen LLM (BYOK) and caches the summary
- **app.py** ties it all together in a Streamlit web interface
- **cli.py** provides the same features via the command line

All downloaded data is cached locally so you don't re-download anything.

---

## Troubleshooting

**"ModuleNotFoundError: No module named 'pypdf'"**
You're probably running Streamlit with system Python instead of the virtual environment. Run:
```bash
source .venv/bin/activate
streamlit run app.py
```

**"No data available yet"**
Click "Fetch All Committees" in the sidebar to download report listings from sansad.in.

**Summaries not working**
Make sure you've selected a provider and entered an API key in the sidebar. For Ollama, make sure it's running (`ollama serve`).

**Reports not loading**
The sansad.in website occasionally goes down for maintenance. Try again in a few hours.

---

## Contributing

Found a bug or want to add a feature? [Open an issue](https://github.com/pranaykotas/parliamentwatch/issues) or submit a pull request.

---

## Acknowledgments

- **Ravichandra Tadigadapa** (Senior PS to the Chairman, Parliamentary Standing Committee on Education) — for flagging that the tool initially covered only the 16 Lok Sabha–chaired DRSCs and prompting the addition of all 8 Rajya Sabha–chaired committees.

---

## License

MIT

---

<p align="center">
  Created by <strong>Pranay Kotasthane</strong> at the <a href="https://takshashila.org.in">Takshashila Institution</a><br>
  Built with Claude Opus
</p>
