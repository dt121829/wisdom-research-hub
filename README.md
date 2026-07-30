# Wisdom Research Hub

AI-driven investment research platform for Wisdom Family Office. Aggregates and synthesises
insights from the selected sources — **Seeking Alpha, Yahoo Finance, Yahoo 奇摩股市, CNBC,
SumZero and WhaleWisdom** — to give staff a comprehensive, buyside-inclusive view for
investment decision-making.

AI features run on **Copilot (Azure OpenAI)**. Every AI feature grounds its output in
material retrieved from the selected sources; when something essential is missing it may
supplement from outside, but every such point is explicitly labelled
**⚠️ external — not from selected sources**.

## Features

| Page | What it does |
|---|---|
| **Dashboard** | Market snapshot whose tiles toggle between % and point change, a topic-structured AI market outlook with a 5-day events calendar and collapsible sources, an interactive price chart (index dropdown, security search, timeframes, zoom) with a right panel keyed to the selection — sector ETFs for an equity index, the Treasury yield curve for a bond yield, VIX term structure for volatility, constituents for TAIEX, peers for a searched security — each with a group average line, and headlines with sentiment tags (including 🟡 Mixed) |
| **Buyside Views** | Opens articles and reads them in **full text**, pulls out verbatim quotes from named investors, then searches the rest of the coverage for more voices on those same topics, reads those too, and compares the views — grouped by topic, with a "Market check" line testing each side against the day's price action. Every quote is verbatim and links to its article; nothing comes from model memory |
| **AI Report Generator** | Configurable reports — type, audience, length (1/3/10 pages), style, language (English / Traditional Chinese), purpose. When a ticker is given it pulls fundamentals and peer multiples and adds a **valuation section** (comparables table + reverse-DCF with stated assumptions), plus a price chart and a peer-return chart; the sector chart highlights the report's own sector. Renders a professional research PDF with linked inline citations, previewed page-by-page and downloadable as .pdf or .docx |
| **Reports Library** | Archive of every report generated, filterable by topic, type and language, with .pdf / .docx download and delete |
| **Research Assistant** | Chatbot grounded in the live source material; attributes every claim to its source. **Attach a screenshot** (PNG/JPG/WEBP/GIF/BMP) or a **document** (PDF, Word, text, Markdown, CSV) — from the panel or the 📎 in the message box — and ask about it. Text is extracted locally; pictures and PDF pages are sent to the model to be *looked at*, so it reads charts, tables and scans. It can also **draw a chart** in its reply from numbers already in context |
| **Sources & Methodology** | Source-selection justification, connector status, and the end-to-end AI workflow (input → processing → synthesis → output) |

## Run it

### Starting it again later (normal case)

The virtual environment and your Azure settings persist, so day to day this is the only
command you need. Open PowerShell and run:

```bash
cd C:\Users\user\.claude\sessions\wisdom-research-app; .venv\Scripts\python.exe -m streamlit run app.py
```

It opens <http://localhost:8501> in your browser. Leave the terminal window open while
you use the app — closing it stops the server. Press `Ctrl+C` in that window to stop.

If the browser says the port is already in use, an old copy is still running:

```bash
Get-Process python | Stop-Process -Force
```

### First-time setup (or after moving the folder)

```bash
cd wisdom-research-app
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

Check your Azure connection at any time with `.venv\Scripts\python.exe check_azure.py`.

Launch with `python -m streamlit`, not the bare `streamlit` command. The `streamlit.exe`
that pip generates is an unsigned launcher shim, and Windows Smart App Control blocks it
with *"An Application Control policy has blocked this file"* — usually right after a
`pip install` rewrites the shim. Going through `python -m` uses the signed Python
executable instead and sidesteps the problem entirely; it runs the identical code.

### If you see "An Application Control policy has blocked this file"

Smart App Control blocks unsigned binaries it does not recognise, and that includes some
compiled Python extensions. **pandas 3.x** is the known offender here: its
`_libs/interval` extension gets blocked, which breaks pandas, and with it yfinance, every
chart and the research assistant. `requirements.txt` therefore pins `pandas<3.0`. If it
recurs after an upgrade:

```bash
.venv\Scripts\python.exe -m pip install --force-reinstall "pandas==2.3.3"
```

Then confirm with `.venv\Scripts\python.exe -c "import pandas, yfinance"`. Do not turn
Smart App Control off to work around this — it is a system-wide protection, and pinning
the package is the narrower fix.

## Live data

Real-time data streams without any credentials:

- **Market quotes** — Yahoo Finance (`yfinance`): S&P 500, Nasdaq, Dow, TAIEX, US 10Y, VIX,
  plus 12 sector ETFs for the sector-performance chart. Cached 5 min.
- **Headlines** — 15 official RSS feeds: CNBC (Top News, Investing, Earnings, Technology,
  Business, Finance), Seeking Alpha (Market Currents, long-form analysis, Wall St
  Breakfast), Yahoo Finance (markets + per-ticker bellwethers). ~140 articles per cycle.
- **Freshness** — several of these feeds mix today's stories with evergreen items months
  old, so every article is timestamped and anything older than 30 hours is dropped (the
  window widens automatically if a pull comes back thin). Within each source the newest
  come first, then sources are interleaved so none dominates; each card shows its age.
- **De-duplication** — three passes: identical canonical URL (query strings stripped, so
  the same story arriving from two feeds collapses), identical headline, then token
  overlap for the same story written up differently. Chinese headlines are tokenised as
  character bigrams — a word regex returns nothing for them, so every 奇摩股市 story
  would otherwise look unique. Merged stories note which other sources carried them.
- **Events calendar** — built from three verified feeds, never from model recall:
  **FOMC dates** are scraped from the Federal Reserve's own calendar
  (`federalreserve.gov/monetarypolicy/fomccalendars.htm`) and lead the day they fall on;
  **earnings dates** for 20 index heavyweights come from Yahoo Finance, shown as
  "Visa (V)"; and **macro releases whose dates follow a fixed rule** (weekly jobless
  claims, non-farm payrolls, ISM Manufacturing/Services, PCE) are computed from the
  calendar in `macro_calendar()`. CPI and PPI move within the month, so they are
  deliberately omitted rather than printed with a guessed date. The model may add
  further events only with a real date, and is told not to name office-holders.
- **Currency normalisation** — for foreign issuers Yahoo quotes the price in the listing
  currency but reports financials in the company's own, which made its published
  multiples meaningless (TSM showed EV/EBITDA of 4.3x, ASML 2503.8x). Statement figures
  are now converted at spot, enterprise value is rebuilt as market cap + debt − cash, and
  every multiple is derived from figures known to be in one currency — giving TSM 20.0x
  and ASML 39.1x. The conversion rate and source currency are disclosed in the report.
- **Article bodies** — Buyside Views fetches the full text of individual articles (cached
  1 hour, fetched in parallel) because headlines and RSS summaries almost never contain
  the quote itself.
- **Re-fetching** — each section has its own refresh: `↻ Re-fetch` rebuilds the outlook
  from freshly pulled news, `↻ Prices` re-pulls quotes and price history, `↻ Refresh`
  reloads the headline list, and `↻ Re-read` on Buyside Views re-reads the articles.
- **SumZero** — members-only buyside community with no public feed. It remains a labelled
  connector stub pending the firm's membership credentials, which slot into the same layer
  in `services/live_data.py`.

Every connector falls back to the bundled sample dataset if unreachable, so the app degrades
gracefully offline.

## Connecting Copilot (Azure OpenAI)

Three values from the Azure portal — your Azure OpenAI resource → **Keys and Endpoint**, plus
the name you gave your model deployment:

```toml
AZURE_OPENAI_ENDPOINT   = "https://your-resource.openai.azure.com/"
AZURE_OPENAI_API_KEY    = "your-azure-key"
AZURE_OPENAI_DEPLOYMENT = "gpt-4o"
```

Supply them any of three ways: type them into the sidebar (per-session, good for trying it
out), copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and set them there
(loads automatically for everyone), or set them as environment variables. On Streamlit Cloud,
paste them into Settings → Secrets.

**Without credentials** the app runs in demo mode: live market data and headlines still
stream, but the AI outlook, news digest, buyside extraction and report generator fall back to
sample content, and Buyside Views explains that it needs a provider.

**Claude as a fallback.** If `ANTHROPIC_API_KEY` is set and Azure is not, the app uses Claude
instead. Azure wins when both are configured. Provider selection lives in `services/llm.py`;
adding a third backend means implementing one `stream()` branch.

## Cost control

AI results are cached against a hash of the current article set (`st.cache_data`, 30 min), so
refreshing a page or switching tabs never re-bills a call — a new call happens only when the
underlying news actually changes. The dashboard outlook, news digest and buyside extraction
are one call each per news cycle.

## Publishing the app

### Option A — Streamlit Community Cloud (free, fastest)

1. Push this folder to a GitHub repository. `.gitignore` already excludes
   `.streamlit/secrets.toml` and `.venv/` — verify with `git status` before the first push.
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub, and click
   **New app**. Point it at your repo, branch `main`, main file `app.py`.
3. Open **Advanced settings → Secrets** and paste the contents of
   `.streamlit/secrets.toml.example` with your real values:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   APP_PASSWORD = "your-shared-password"
   ```
4. Deploy. You get a URL like `https://your-app.streamlit.app` to share with staff.

Set `APP_PASSWORD` before sharing the link — a Community Cloud URL is reachable by anyone
who has it. With the password set, visitors hit a sign-in screen first.

### Option B — your own cloud (recommended for firm-wide production)

Any container host works — Azure App Service, AWS App Runner, Google Cloud Run, Render, or
Fly.io. Run `python -m streamlit run app.py --server.port $PORT --server.address 0.0.0.0` and supply
`ANTHROPIC_API_KEY` as an environment variable. This keeps the app on infrastructure you
control, and lets you put it behind your existing SSO (Entra ID / Okta) instead of a shared
password.

### Option C — internal network only

Already available: run the app on an office machine and staff on the same network open the
Network URL that Streamlit prints at startup (`http://<machine-ip>:8501`). Nothing leaves
your network, but the machine must stay on.

### Before you publish — checklist

- [ ] `git status` shows no `secrets.toml` and no `.venv/`
- [ ] `APP_PASSWORD` set (Options A and C) or SSO configured (Option B)
- [ ] Azure OpenAI credentials set in the host's secrets — every user then shares the firm's
      Azure billing, which is the intent for an internal tool. Set a spend limit in Azure Cost
      Management if you want a hard ceiling.
- [ ] Note: Yahoo Finance occasionally rate-limits shared cloud IPs. The app falls back to
      sample quotes automatically and labels them ⚪ — for guaranteed uptime, move to a paid
      market-data API in `services/live_data.py`

## Architecture

```
services/llm.py          provider abstraction — Azure OpenAI / Claude / demo; streaming + JSON
services/ai.py           system prompt and live-context builder (provider-agnostic)
services/insights.py     AI products: market outlook + the buyside quote pipeline
                         (read → verify verbatim → follow up → compare)
services/live_data.py    source connectors (quotes, 11 news feeds, article full text,
                         per-ticker news, yield/vol curves, index constituents, peers)
services/pdf.py          report → professional PDF / Word, with charts and page images
services/reports.py      report spec → prompt construction + demo fallbacks
services/report_store.py the reports archive (save / list / read / delete)
services/auth.py         optional shared-password gate
services/charts.py       shared Plotly styling (validated accessible palette)
services/demo.py         canned chatbot replies for demo mode
data/sample_data.py      offline fallback dataset
data/reports/            generated reports (git-ignored)
views/                   one module per page
app.py                   navigation + sidebar (provider config, mode indicator)
```

**How the buyside pipeline works** (`services/insights.py`, `buyside_pipeline`):

1. **Read** — the newest articles are fetched in full and the model pulls out comments from
   named people, returning each quote verbatim with the article it came from.
2. **Verify** — every returned quote is checked back against the article text it claims to
   come from; anything that isn't actually in the article is discarded. This is what stops
   paraphrase being presented as a quote.
3. **Follow up** — the firms and topics found in step 1 (buyside ones first) are searched
   across the rest of the corpus, and those articles are read in full too, so a single
   investor's comment pulls in the other voices on the same question.
4. **Compare** — the collected quotes go back to the model grouped by topic, along with the
   day's index and sector moves, producing a comparison that names who takes which side and
   tests it against the tape.

Because every quote must survive step 2, the page cannot show anything the model recalled
from memory — if the coverage contains no investor comment, it says so instead.

**Vision and generated charts.** The Research Assistant can both *see* pictures and
*draw* them:

- **Seeing** — uploaded screenshots and each page of an attached PDF are sent to the
  model as images (`services/documents.py`), so figures that are drawn rather than
  written — chart labels, scanned tables, terminal grabs — are readable. Images are
  capped at 1,600px on the longest edge and 8 per request to control token cost, and
  it is behind a toggle because pictures cost more than text. Requires a
  vision-capable deployment; verified working on `gpt-5-mini-1`.
- **Drawing** — the model never runs code. It emits a small validated JSON spec
  (`services/chartspec.py`) describing the chart it wants, and the app renders it with
  Plotly. The spec is capped at 6 series × 60 points, malformed specs are rejected, and
  the JSON is stripped from the reply mid-stream so the reader only sees the chart. The
  model is instructed to chart only numbers already in context, never invented ones.

**What counts as buyside.** Only asset management firms, hedge funds and other private
funds running outside capital, plus contributors on the firm's research platforms
(Seeking Alpha, SumZero, WhaleWisdom). Media commentators (network hosts, columnists),
retail brokers and trading platforms (eToro, Robinhood), bank and broker research,
company executives and policymakers are captured and shown, but labelled non-buyside and
excluded by the *Buyside only* filter. Classification follows who employs the speaker,
not how authoritative the comment sounds, and well-known cases are corrected
deterministically in `_correct_party_type()` rather than left to the model.

*All market figures in the sample dataset are illustrative, not live quotes. Generated reports
are research synthesis, not investment advice.*
