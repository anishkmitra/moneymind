# MoneyMind — Institutional Research Scraper

Automated scraping, storage, and summarization of research from the world's foremost investment managers. Feeds into trading/investment decision workflows.

## What it does

- **Scrapes** research and insights pages from a configured set of firms (Citadel Securities, Bridgewater, BlackRock, AQR, Two Sigma, Man Group, D.E. Shaw, JPMorgan AM, Goldman Sachs AM, and more)
- **Downloads** any linked PDFs to local storage and Supabase Storage
- **Extracts** text from HTML articles and PDF reports
- **Summarizes** each piece with Claude (thesis, market view, key data, actionable insights, tags)
- **Generates** a cross-firm market intelligence digest identifying consensus vs. contrarian views
- **Stores** everything in Supabase (Postgres + Storage) for permanent reference even if source sites change
- **Displays** results in a Next.js dashboard deployed to Vercel

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Scraper     │────▶│   Supabase   │◀────│  Next.js     │
│  (Python)    │     │  Postgres +  │     │  Dashboard   │
│  Playwright  │     │  Storage     │     │  (Vercel)    │
└──────────────┘     └──────────────┘     └──────────────┘
       │
       ▼
   Claude API
  (summaries)
```

## Setup

### 1. Supabase
Create a project at [supabase.com](https://supabase.com). In the SQL Editor, run `supabase_schema.sql`. Copy your project URL + `service_role` key into `.env`.

### 2. Python scraper
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
playwright install chromium
cp .env.example .env   # fill in your keys
```

### 3. Run
```bash
scraper firms                          # list configured firms
scraper scrape -f citadel-securities   # scrape one firm
scraper scrape                         # scrape all firms
scraper scrape --no-store              # test without writing to Supabase
scraper recent                         # show recently scraped articles
scraper watch 24                       # run every 24 hours
```

### 4. Dashboard
```bash
cd dashboard
cp .env.example .env.local   # fill in NEXT_PUBLIC_SUPABASE_URL + ANON_KEY
npm install
npm run dev
```

Deploy to Vercel by connecting the `dashboard/` directory and setting the same env vars.

## Project structure

```
scraper/
├── config.py         # env + settings
├── firms.py          # registry of investment managers
├── engine.py         # Playwright scraper + PDF downloader
├── pdf_extract.py    # pdfplumber text extraction
├── summarizer.py     # Claude summarization
├── storage.py        # Supabase integration
└── cli.py            # command-line interface

dashboard/            # Next.js app for Vercel
supabase_schema.sql   # DB schema
```

## Adding a new firm

Edit `scraper/firms.py` and append a `FirmConfig` with:
- `research_url` — the listing page
- `link_selector` + `link_filter` — how to find article links
- `title_selector`, `date_selector`, `body_selector` — how to extract content from each article
- `pdf_selector` — how to find PDF download links

## Roadmap

**V2 (planned):**
- Autonomous discovery — have the agent find research from anywhere on the web, not just a fixed firm list
- Credibility scoring — weight sources by firm AUM, regulatory status, track record, citation count
- Trading signals — convert summaries into structured features for a trading/investment system
- Scheduling via GitHub Actions / Vercel Cron instead of local `watch`
