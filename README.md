# ParliamentWatch 🏛️

**Track, search, and summarize Indian Parliamentary Committee reports — all in one place.**

ParliamentWatch pulls reports from [sansad.in](https://sansad.in) (the official Indian Parliament website), lets you browse and search them, and uses AI to generate plain-English summaries. It covers all 16 Departmentally Related Standing Committees (DRSCs) across both Lok Sabha and Rajya Sabha.

> **No API key required to get started.** You can browse, search, and read reports without any setup. AI summaries are optional — and you can use free providers like Ollama, Gemini, or Groq.

---

## Why This Exists

Parliamentary committee reports are some of the most important documents in Indian democracy — they scrutinize government ministries, examine budgets, and recommend policy changes. But they're scattered across a clunky government website with no search, no alerts, and no way to quickly understand what a 200-page PDF says.

ParliamentWatch fixes that.

---

## What You Can Do

| Feature | Needs API Key? |
|---------|---------------|
| Browse all reports for any of the 16 DRSCs | No |
| Search report titles by keyword | No |
| Full-text search across extracted PDFs | No |
| Download report PDFs (English & Hindi) | No |
| Extract and read full text from PDFs | No |
| Sort reports by date or report number | No |
| Export metadata, summaries, or text to CSV/Markdown | No |
| Get daily email alerts for new reports | No |
| **AI-powered summaries of reports** | **Yes (free options available)** |

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

### Step 4: Fetch data

Click **"Fetch All Committees"** in the sidebar. This pulls the latest report listings from sansad.in. It takes about a minute for all 16 committees.

---

## Using the Web App

The app has four tabs:

### Dashboard
An overview showing:
- Total number of reports across all committees
- How many committees have data
- Recently published reports
- Reports per committee (bar chart)

Click on any report title to see its details, download links, and (if you have an API key) generate an AI summary.

### Committee Deep Dive
Pick a committee from the dropdown. You'll see all its reports in a sortable table — sort by date (newest/oldest) or report number. Click any report title to view details or extract its text.

### Search
Two search modes:
- **Titles only** — fast keyword search across all report titles
- **Titles + Full text** — searches inside extracted PDF text too (reports must be extracted first)

### Export
Download your data in three formats:
- **Report metadata** — titles, dates, committees (CSV or Markdown)
- **AI summaries** — all generated summaries bundled together
- **Extracted text** — full text from all extracted PDFs

---

## AI Summaries (Optional)

The sidebar has a **"AI Summarization"** section where you can enter an API key. Summaries are generated on-demand when you click "Generate Summary" on a report.

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
# List all 16 committees
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

# Historical data (e.g. 17th Lok Sabha)
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

All 16 Departmentally Related Standing Committees of the Indian Parliament:

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

- **scraper.py** calls the sansad.in REST API to fetch structured report metadata — no browser automation or web scraping needed
- **pdf_utils.py** downloads PDFs and extracts text using pypdf
- **summarizer.py** sends extracted text to your chosen LLM and caches the summary
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

## License

MIT

---

<p align="center">
  Created by <strong>Pranay Kotasthane</strong> at the <a href="https://takshashila.org.in">Takshashila Institution</a><br>
  Built with Claude Opus
</p>
