# Wisdom Research Hub

AI-driven investment research platform for Wisdom Family Office. Aggregates and synthesises
insights from five sources — **Barron's, The Wall Street Journal, CNBC, Seeking Alpha, and the
firm's Bloomberg Terminal** — to give staff a comprehensive, buyside-inclusive view for
investment decision-making.

## Features

| Page | What it does |
|---|---|
| **Dashboard** | Market snapshot (indices, sectors, trend), AI-generated market outlook, latest headlines across all five sources with sentiment tags |
| **Buyside Views** | The coverage gap this platform closes: asset-manager and hedge-fund perspectives (fund letters, 13F positioning, buyside contributors), plus a consensus-vs-divergence map |
| **AI Report Generator** | Configurable reports — type (event-driven / outlook / product-specific), audience, length (1/3/10 pages), style, language (English / Traditional Chinese), purpose — streamed live from Claude and downloadable as Markdown |
| **Research Assistant** | Chatbot grounded in the aggregated content; attributes every claim to its source |
| **Sources & Methodology** | Source-selection justification and the end-to-end AI workflow (input → processing → synthesis → output) |

## Run it

```bash
cd wisdom-research-app
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
streamlit run app.py
```

## Live data

Real-time data streams without any credentials:

- **Market quotes** — Yahoo Finance (`yfinance`): S&P 500, Nasdaq, Dow, TAIEX, US 10Y, VIX,
  plus 12 sector ETFs for the sector-performance chart. Cached 5 min.
- **Headlines** — official RSS feeds: CNBC (Top News, Investing), WSJ / Dow Jones (Markets,
  Business), Seeking Alpha (Market Currents + long-form analysis). Cached 10–15 min, with a
  manual Refresh button on the dashboard.
- **Barron's / Bloomberg Terminal** — no free public feeds exist (licensed content); these are
  connector stubs with clearly labelled sample data until the firm's licences are wired in.

Every connector falls back to the bundled sample dataset if unreachable, so the app degrades
gracefully offline.

## AI modes

- **Demo mode (default)** — no credentials needed; the chatbot and report generator return
  pre-built sample outputs. Live market data still streams.
- **Live Claude** — provide an Anthropic API key one of three ways: paste it in the sidebar
  (per-session), copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and set
  `ANTHROPIC_API_KEY` there (loads automatically for all users), or set the `ANTHROPIC_API_KEY`
  environment variable. The outlook, chatbot, and report generator then call Claude
  (`claude-opus-5`) grounded in the **live** quotes and headlines, streaming in real time.

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
Fly.io. Run `streamlit run app.py --server.port $PORT --server.address 0.0.0.0` and supply
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
- [ ] `ANTHROPIC_API_KEY` set in the host's secrets — every user then shares the firm's API
      billing, which is the intent for an internal tool. Monitor usage in the Anthropic console.
- [ ] Confirm you are comfortable with the sample buyside content being visible, or replace
      `data/sample_data.py` with real content first
- [ ] Note: Yahoo Finance occasionally rate-limits shared cloud IPs. The app falls back to
      sample quotes automatically and labels them ⚪ — for guaranteed uptime, move to a paid
      market-data API in `services/live_data.py`

## Architecture

```
data/sample_data.py     sample content store (production: replaced by the ingestion pipeline)
services/ai.py          Claude client, system prompt, context builder, streaming
services/reports.py     report spec → prompt construction + demo fallbacks
services/demo.py        canned chatbot replies for demo mode
services/charts.py      shared Plotly styling (validated accessible palette)
views/                  one module per page
app.py                  navigation + sidebar (API key, mode indicator)
```

In production, stage 1 (data input) is implemented with RSS/API pulls for CNBC and Seeking
Alpha, licensed content feeds for WSJ and Barron's, and Bloomberg Terminal exports; Claude's
native PDF and vision input handles charts and tables inside documents. The sample dataset
mirrors the record shapes that pipeline produces, so swapping it in requires no UI changes.

*All market figures in the sample dataset are illustrative, not live quotes. Generated reports
are research synthesis, not investment advice.*
