"""Live data connectors for the five approved sources.

    Barron's · WSJ · CNBC · Seeking Alpha · Yahoo Finance

- Market quotes: Yahoo Finance (yfinance) — indices, 10Y yield, VIX, sector ETFs.
- Headlines: official RSS from CNBC, WSJ (Dow Jones), Seeking Alpha, Yahoo Finance.
- Barron's is hard-paywalled and returns 403 on every public endpoint; it stays a
  subscription connector (see the Sources & Methodology page).

No other sources are consulted anywhere in the app.

Every function is cached and falls back to the bundled sample dataset on any
network failure, so the UI keeps working offline.
"""

import html
import re
import time as _time

import streamlit as st

from data import sample_data as d

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
}

INDEX_SYMBOLS = [
    ("S&P 500", "^GSPC", "index"),
    ("Nasdaq", "^IXIC", "index"),
    ("Dow Jones", "^DJI", "index"),
    ("TAIEX", "^TWII", "index"),
    ("US 10Y", "^TNX", "yield"),
    ("VIX", "^VIX", "level"),
]

SECTOR_ETFS = [
    ("Semiconductors", "SMH"),
    ("Technology", "XLK"),
    ("Comm. Services", "XLC"),
    ("Cons. Discretionary", "XLY"),
    ("Cons. Staples", "XLP"),
    ("Industrials", "XLI"),
    ("Financials", "XLF"),
    ("Health Care", "XLV"),
    ("Energy", "XLE"),
    ("Utilities", "XLU"),
    ("Real Estate", "XLRE"),
    ("Materials", "XLB"),
]

NEWS_FEEDS = [
    ("CNBC", "Top News", "https://www.cnbc.com/id/100003114/device/rss/rss.html", 4),
    ("CNBC", "Investing", "https://www.cnbc.com/id/20910258/device/rss/rss.html", 3),
    ("WSJ", "Markets", "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain", 5),
    ("WSJ", "Business", "https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness", 3),
    ("Seeking Alpha", "Market Currents", "https://seekingalpha.com/market_currents.xml", 5),
    ("Yahoo Finance", "Markets", "https://finance.yahoo.com/news/rssindex", 5),
]

SA_ANALYSIS_FEED = "https://seekingalpha.com/feed.xml"

# Per-ticker news, used by the report generator to gather topic-specific coverage.
YF_TICKER_FEED = ("https://feeds.finance.yahoo.com/rss/2.0/headline"
                  "?s={symbol}&region=US&lang=en-US")
SA_TICKER_FEED = "https://seekingalpha.com/api/sa/combined/{symbol}.xml"

_POS_WORDS = ("beat", "beats", "surge", "rally", "rallies", "record", "gains", "jumps",
              "soars", "upgrade", "bullish", "tops", "climbs", "boost", "strong")
_NEG_WORDS = ("falls", "drops", "miss", "misses", "cuts", "warning", "bearish", "slump",
              "tumbles", "fears", "downgrade", "plunge", "sinks", "losses", "weak", "recall")


def _sentiment(text: str) -> str:
    t = text.lower()
    pos = sum(w in t for w in _POS_WORDS)
    neg = sum(w in t for w in _NEG_WORDS)
    if pos > neg:
        return "Positive"
    if neg > pos:
        return "Negative"
    return "Neutral"


def _clean(text: str, limit: int = 240) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", "", text or "")).strip()
    text = text.replace("$", "\\$")  # avoid Streamlit's LaTeX interpretation
    return text[:limit] + ("…" if len(text) > limit else "")


def _last_two(series):
    s = series.dropna()
    if len(s) < 2:
        return None, None
    return float(s.iloc[-1]), float(s.iloc[-2])


@st.cache_data(ttl=300, show_spinner=False)
def get_market_data():
    """Indices + sectors in one batched download. Returns (indices, sectors, live)."""
    try:
        import yfinance as yf

        symbols = [s for _, s, _ in INDEX_SYMBOLS] + [s for _, s in SECTOR_ETFS]
        px = yf.download(symbols, period="5d", interval="1d", progress=False,
                         auto_adjust=True, threads=True)["Close"]

        indices = []
        for name, sym, kind in INDEX_SYMBOLS:
            last, prev = _last_two(px[sym])
            if last is None:
                continue
            if kind == "yield":
                # ^TNX is sometimes quoted at 10x the yield
                if last > 20:
                    last, prev = last / 10, prev / 10
                indices.append({"name": name, "value": f"{last:.2f}%",
                                "change": f"{(last - prev) * 100:+.0f} bps",
                                "delta": last - prev})
            elif kind == "level":
                indices.append({"name": name, "value": f"{last:.1f}",
                                "change": f"{last - prev:+.1f}", "delta": last - prev})
            else:
                chg = (last - prev) / prev * 100
                indices.append({"name": name, "value": f"{last:,.2f}",
                                "change": f"{chg:+.2f}%", "delta": chg})

        sectors = []
        for name, sym in SECTOR_ETFS:
            last, prev = _last_two(px[sym])
            if last is None:
                continue
            sectors.append({"name": name, "change": round((last - prev) / prev * 100, 2)})

        if not indices or not sectors:
            raise ValueError("no quotes returned")
        return indices, sectors, True
    except Exception:
        return d.INDICES, d.SECTORS, False


@st.cache_data(ttl=900, show_spinner=False)
def get_sp500_trend():
    """Last ~2 weeks of S&P 500 closes. Returns (dates, values, live)."""
    try:
        import yfinance as yf

        hist = yf.download("^GSPC", period="1mo", interval="1d",
                           progress=False, auto_adjust=True)["Close"].dropna()
        tail = hist.tail(10)
        dates = [idx.strftime("%Y-%m-%d") for idx in tail.index]
        values = [float(v) for v in tail.iloc[:, 0]] if tail.ndim > 1 else [float(v) for v in tail]
        if len(values) < 5:
            raise ValueError("insufficient history")
        return dates, values, True
    except Exception:
        return d.SP500_TREND["dates"], d.SP500_TREND["values"], False


def _fmt_time(entry) -> str:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return _time.strftime("%b %d, %H:%M", parsed)
    return entry.get("published", "")[:16]


@st.cache_data(ttl=600, show_spinner=False)
def get_headlines():
    """Live headlines across CNBC / WSJ / Seeking Alpha. Returns (headlines, live)."""
    try:
        import feedparser
        import requests

        out = []
        for source, category, url, count in NEWS_FEEDS:
            try:
                r = requests.get(url, headers=UA, timeout=8)
                feed = feedparser.parse(r.content)
                for e in feed.entries[:count]:
                    title = _clean(e.get("title", ""), 160)
                    if not title:
                        continue
                    out.append({
                        "source": source,
                        "category": category,
                        "title": title,
                        "summary": _clean(e.get("summary", "")),
                        "time": _fmt_time(e),
                        "sentiment": _sentiment(title),
                        "link": e.get("link", ""),
                    })
            except Exception:
                continue  # one dead feed shouldn't kill the rest
        if len(out) < 3:
            raise ValueError("feeds unavailable")

        # Round-robin across sources so no single feed dominates the top of the
        # list — the dashboard and the AI both see a balanced mix.
        by_source: dict[str, list] = {}
        for item in out:
            by_source.setdefault(item["source"], []).append(item)
        interleaved = []
        while any(by_source.values()):
            for src in list(by_source):
                if by_source[src]:
                    interleaved.append(by_source[src].pop(0))
        return interleaved, True
    except Exception:
        return d.HEADLINES, False


@st.cache_data(ttl=900, show_spinner=False)
def get_topic_news(topic: str, symbol: str = "", limit: int = 14):
    """Topic-specific coverage for the report generator.

    Pulls the per-ticker feeds when a symbol is supplied, then falls back to
    keyword-matching the general headline pool. Only the approved sources are used.
    """
    import feedparser
    import requests

    items = []
    if symbol:
        for source, url in (("Yahoo Finance", YF_TICKER_FEED.format(symbol=symbol)),
                            ("Seeking Alpha", SA_TICKER_FEED.format(symbol=symbol))):
            try:
                r = requests.get(url, headers=UA, timeout=8)
                for e in feedparser.parse(r.content).entries[:limit]:
                    title = _clean(e.get("title", ""), 160)
                    if title:
                        items.append({
                            "source": source, "category": symbol.upper(), "title": title,
                            "summary": _clean(e.get("summary", "")), "time": _fmt_time(e),
                            "sentiment": _sentiment(title), "link": e.get("link", ""),
                        })
            except Exception:
                continue

    # Supplement with any general headlines mentioning the topic.
    headlines, _ = get_headlines()
    words = [w.lower() for w in topic.split() if len(w) > 3]
    for h in headlines:
        blob = (h["title"] + " " + h["summary"]).lower()
        if any(w in blob for w in words) or symbol.lower() in blob:
            if not any(h["title"] == i["title"] for i in items):
                items.append(h)

    return items[:limit]


@st.cache_data(ttl=900, show_spinner=False)
def get_sa_analysis(count: int = 6):
    """Latest long-form analysis from Seeking Alpha. Returns (items, live)."""
    try:
        import feedparser
        import requests

        r = requests.get(SA_ANALYSIS_FEED, headers=UA, timeout=8)
        feed = feedparser.parse(r.content)
        items = []
        for e in feed.entries[:count]:
            title = _clean(e.get("title", ""), 160)
            if title:
                items.append({
                    "title": title,
                    "author": _clean(e.get("author", ""), 60),
                    "time": _fmt_time(e),
                    "link": e.get("link", ""),
                })
        if not items:
            raise ValueError("empty feed")
        return items, True
    except Exception:
        return [], False
