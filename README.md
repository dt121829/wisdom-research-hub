# Wisdom Research Hub

AI-driven investment research platform for Wisdom Family Office. Aggregates and synthesises
insights from five sources — **Barron's, The Wall Street Journal, CNBC, Seeking Alpha and
Yahoo Finance** — to give staff a comprehensive, buyside-inclusive view for investment
decision-making.

AI features run on **Copilot (Azure OpenAI)**. Every AI feature is instructed to use only
material retrieved from those five sources, and to say when the material does not support a
claim rather than drawing on general knowledge.

## Features

| Page | What it does |
|---|---|
| **Dashboard** | Market snapshot (indices, sectors, trend), an AI market outlook with the source articles listed alongside it, and the latest headlines with sentiment tags plus an AI digest of what they collectively mean |
| **Buyside Views** | Reads live coverage and extracts every view attributed to a named party, then cross-checks whether that party is quoted in other sources — flagging where their attributed stance differs between outlets |
| **AI Report Generator** | Configurable reports — type (event-driven / outlook / product-specific), audience, length (1/3/10 pages), style, language (English / Traditional Chinese), purpose. Pulls per-ticker coverage, streams live, and files every report to the library |
| **Reports Library** | Archive of every report generated, filterable by topic, type and language, with download and delete |
| **Research Assistant** | Chatbot grounded in the live source material; attributes every claim to its source |
| **Sources & Methodology** | Source-selection justification, connector status, and the end-to-end AI workflow (input → processing → synthesis → output) |

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
- **Headlines** — official RSS: CNBC (Top News, Investing), WSJ / Dow Jones (Markets,
  Business), Seeking Alpha (Market Currents + long-form analysis), Yahoo Finance (markets +
  per-ticker). Cached 10–15 min, with a manual Refresh button on the dashboard. Headlines are
  interleaved round-robin so no single feed dominates.
- **Barron's** — hard-paywalled; every public RSS endpoint returns 403 to anonymous requests.
  It remains a labelled connector stub pending the firm's Dow Jones subscription credentials
  (Dow Jones DNA / Factiva API), which slot into the same layer in `services/live_data.py`.

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
services/insights.py     AI products: market outlook, news digest, buyside extraction
                         + deterministic cross-source party matching
services/live_data.py    the five source connectors (quotes, headlines, per-ticker news)
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

**How cross-source checking works.** The model extracts attributed views as structured JSON;
matching the same party across sources is then done in plain Python (`_normalise` strips
corporate suffixes, `_same_party` matches on leading whole words so "UBS" pairs with "UBS
Global Wealth" but "Ark" never pairs with "Clark"). Keeping the matching deterministic means
it is testable and can't hallucinate a connection between two firms.

*All market figures in the sample dataset are illustrative, not live quotes. Generated reports
are research synthesis, not investment advice.*
