"""Live data connectors for the selected sources.

    Seeking Alpha · Yahoo Finance · CNBC · SumZero

- Market quotes: Yahoo Finance (yfinance) — indices, 10Y yield, VIX, sector ETFs.
- Headlines: official RSS from CNBC, Seeking Alpha, Yahoo Finance.
- SumZero is a members-only buyside research community with no public feed; it
  stays a subscription connector (see the Sources & Methodology page).

No other sources are consulted anywhere in the app. When an AI feature needs to
supplement with material beyond these sources, the UI labels it explicitly.

Every function is cached and falls back to the bundled sample dataset on any
network failure, so the UI keeps working offline.
"""

import calendar as _calendar
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

# Per-ticker news, used by the report generator and by the fresh-news pool below.
YF_TICKER_FEED = ("https://feeds.finance.yahoo.com/rss/2.0/headline"
                  "?s={symbol}&region=US&lang=en-US")
SA_TICKER_FEED = "https://seekingalpha.com/api/sa/combined/{symbol}.xml"

# Feeds are pulled deep and then filtered by age, because several of these carry
# evergreen items months old alongside today's stories.
NEWS_FEEDS = [
    ("CNBC", "Top News", "https://www.cnbc.com/id/100003114/device/rss/rss.html", 30),
    ("CNBC", "Investing", "https://www.cnbc.com/id/15839069/device/rss/rss.html", 30),
    ("CNBC", "Earnings", "https://www.cnbc.com/id/15839135/device/rss/rss.html", 30),
    ("CNBC", "Technology", "https://www.cnbc.com/id/19854910/device/rss/rss.html", 30),
    ("CNBC", "Business", "https://www.cnbc.com/id/10001147/device/rss/rss.html", 30),
    ("CNBC", "Finance", "https://www.cnbc.com/id/10000664/device/rss/rss.html", 30),
    ("Seeking Alpha", "Market Currents", "https://seekingalpha.com/market_currents.xml", 30),
    ("Seeking Alpha", "Analysis", "https://seekingalpha.com/feed.xml", 30),
    ("Seeking Alpha", "Wall St Breakfast", "https://seekingalpha.com/tag/wall-st-breakfast.xml", 20),
    ("Yahoo Finance", "Markets", "https://finance.yahoo.com/news/rssindex", 45),
    # Yahoo's general feed lags by a day or more; its per-ticker feeds are current,
    # so a few bellwethers keep Yahoo represented in the fresh pool.
    ("Yahoo Finance", "S&P 500", YF_TICKER_FEED.format(symbol="SPY"), 20),
    ("Yahoo Finance", "Nasdaq", YF_TICKER_FEED.format(symbol="QQQ"), 20),
    ("Yahoo Finance", "Nvidia", YF_TICKER_FEED.format(symbol="NVDA"), 15),
    ("Yahoo Finance", "Apple", YF_TICKER_FEED.format(symbol="AAPL"), 15),
    ("Yahoo Finance", "TSMC", YF_TICKER_FEED.format(symbol="TSM"), 15),
    # Yahoo 奇摩股市 — Taiwan-market coverage in Traditional Chinese.
    ("Yahoo 奇摩股市", "台股", "https://tw.stock.yahoo.com/rss?category=tw-market", 25),
    ("Yahoo 奇摩股市", "國際股市", "https://tw.stock.yahoo.com/rss?category=intl-markets", 15),
    ("Yahoo 奇摩股市", "財經新聞", "https://tw.stock.yahoo.com/rss?category=news", 15),
]

# Anything older than this is dropped: a "latest news" page showing last week's
# stories is worse than showing fewer. Raised automatically if a pull comes back
# too thin (quiet weekend, feed outage).
MAX_AGE_HOURS = 30
MIN_ARTICLES = 25

SOURCES_LABEL = ("Seeking Alpha · Yahoo Finance · Yahoo 奇摩股市 · CNBC · "
                 "SumZero · WhaleWisdom")

# Sources that need paid credentials and so have no live connector yet.
PENDING_SOURCES = {
    "SumZero": "members-only buyside research community; needs a SumZero membership.",
    "WhaleWisdom": ("13F institutional position changes; needs a WhaleWisdom API key "
                    "(their API returns 401 without one and they publish no RSS)."),
}

SA_ANALYSIS_FEED = "https://seekingalpha.com/feed.xml"


_POS_WORDS = ("beat", "beats", "surge", "rally", "rallies", "record", "gains", "jumps",
              "soars", "upgrade", "bullish", "tops", "climbs", "boost", "strong")
_NEG_WORDS = ("falls", "drops", "miss", "misses", "cuts", "warning", "bearish", "slump",
              "tumbles", "fears", "downgrade", "plunge", "sinks", "losses", "weak", "recall")


def _sentiment(text: str) -> str:
    t = text.lower()
    pos = sum(w in t for w in _POS_WORDS)
    neg = sum(w in t for w in _NEG_WORDS)
    # Both bullish and bearish language in the same piece, with no clear winner,
    # reads as differing views rather than a single consensus.
    if pos and neg and abs(pos - neg) <= 1:
        return "Mixed"
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
                                "change_alt": f"{(last - prev) / prev * 100:+.2f}%",
                                "delta": last - prev})
            elif kind == "level":
                indices.append({"name": name, "value": f"{last:.1f}",
                                "change": f"{last - prev:+.1f}",
                                "change_alt": f"{(last - prev) / prev * 100:+.1f}%",
                                "delta": last - prev})
            else:
                chg = (last - prev) / prev * 100
                indices.append({"name": name, "value": f"{last:,.2f}",
                                "change": f"{chg:+.2f}%",
                                "change_alt": f"{last - prev:+,.2f} pts",
                                "delta": chg})

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


# Timeframes offered in the dashboard chart. yfinance period + sensible interval.
TIMEFRAMES = {
    "1W": ("5d", "1d"),
    "1M": ("1mo", "1d"),
    "3M": ("3mo", "1d"),
    "6M": ("6mo", "1d"),
    "1Y": ("1y", "1d"),
    "2Y": ("2y", "1wk"),
}


@st.cache_data(ttl=900, show_spinner=False)
def get_history(symbol: str, timeframe: str = "3M"):
    """Close-price history for any symbol. Returns (dates, values, live).

    Falls back to the bundled S&P 500 sample for ^GSPC; other symbols return
    empty series when offline or unknown.
    """
    period, interval = TIMEFRAMES.get(timeframe, ("3mo", "1d"))
    try:
        import yfinance as yf

        hist = yf.download(symbol, period=period, interval=interval,
                           progress=False, auto_adjust=True)["Close"].dropna()
        if hist.ndim > 1:
            hist = hist.iloc[:, 0].dropna()
        dates = [idx.strftime("%Y-%m-%d") for idx in hist.index]
        values = [float(v) for v in hist]
        if len(values) < 2:
            raise ValueError("insufficient history")
        return dates, values, True
    except Exception:
        if symbol == "^GSPC":
            return d.SP500_TREND["dates"], d.SP500_TREND["values"], False
        return [], [], False


@st.cache_data(ttl=900, show_spinner=False)
def get_sector_performance(timeframe: str = "1D"):
    """Sector ETF returns over the chosen timeframe. Returns (sectors, live)."""
    if timeframe == "1D":
        _, sectors, live = get_market_data()
        return sectors, live
    period, interval = TIMEFRAMES.get(timeframe, ("3mo", "1d"))
    try:
        import yfinance as yf

        px = yf.download([s for _, s in SECTOR_ETFS], period=period, interval=interval,
                         progress=False, auto_adjust=True, threads=True)["Close"]
        sectors = []
        for name, sym in SECTOR_ETFS:
            s = px[sym].dropna()
            if len(s) < 2:
                continue
            sectors.append({"name": name,
                            "change": round((float(s.iloc[-1]) / float(s.iloc[0]) - 1) * 100, 2)})
        if not sectors:
            raise ValueError("no sector data")
        return sectors, True
    except Exception:
        return d.SECTORS, False


# Largest TAIEX constituents, used when TAIEX is the selected index.
TAIEX_CONSTITUENTS = [
    ("TSMC", "2330.TW"),
    ("Hon Hai", "2317.TW"),
    ("MediaTek", "2454.TW"),
    ("Delta Electronics", "2308.TW"),
    ("Quanta", "2382.TW"),
    ("Fubon FHC", "2881.TW"),
    ("Cathay FHC", "2882.TW"),
    ("UMC", "2303.TW"),
    ("Evergreen Marine", "2603.TW"),
    ("Largan", "3008.TW"),
]

# Large caps whose reporting dates move the index — checked for the events calendar.
CALENDAR_TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "TSM", "AMD",
    "MU", "INTC", "JPM", "XOM", "LLY", "V", "WMT", "COST", "NFLX", "ORCL",
]


FOMC_CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"

_MONTHS = {m: n for n, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}
_MONTHS.update({m[:3]: n for m, n in list(_MONTHS.items())})


@st.cache_data(ttl=86400, show_spinner=False)
def get_fomc_dates() -> list[dict]:
    """Scheduled FOMC meetings, straight from the Federal Reserve's own calendar.

    Returns [{"date": "2026-07-29", "label": "FOMC meeting (Jul 28-29)",
              "decision_day": True}, ...] for the current and next year.
    A rate decision is the single most market-moving scheduled event there is, so
    it comes from the primary source rather than from the model's recollection.
    """
    import datetime as _dt

    try:
        import requests

        html = requests.get(FOMC_CALENDAR_URL, headers=UA, timeout=15).text
    except Exception:
        return []

    out = []
    # The page groups meetings under "<year> FOMC Meetings" headings.
    parts = re.split(r"(\d{4})\s*FOMC\s*Meetings", html)
    for i in range(1, len(parts) - 1, 2):
        try:
            year = int(parts[i])
        except ValueError:
            continue
        chunk = parts[i + 1]
        # Month and date sit in sibling divs, so pair each month with the first
        # date that follows it rather than trying to split the block apart.
        months = [(m.start(), m.group(1)) for m in re.finditer(
            r"fomc-meeting__month[^>]*>\s*(?:<strong>)?\s*([A-Za-z]+)", chunk)]
        dates = [(m.start(), m.group(1), m.group(2)) for m in re.finditer(
            r"fomc-meeting__date[^>]*>\s*([0-9]{1,2})(?:\s*[-–]\s*([0-9]{1,2}))?",
            chunk)]
        for pos, month_name in months:
            following = [d for d in dates if d[0] > pos]
            if not following:
                continue
            _, first_s, last_s = following[0]
            month = _MONTHS.get(month_name[:3].title())
            if not month:
                continue
            first = int(first_s)
            last = int(last_s) if last_s else first
            short_month = month_name[:3].title()
            # "30-1" spans into the next month; the decision lands on the last day.
            end_month, end_year = month, year
            if last < first:
                end_month = 1 if month == 12 else month + 1
                end_year = year + 1 if month == 12 else year
            try:
                day = _dt.date(end_year, end_month, last)
            except ValueError:
                continue
            span = (f"{short_month} {first}-{last}" if last != first
                    else f"{short_month} {first}")
            # No chair named: who holds the chair changes, the event does not.
            out.append({"date": day.isoformat(),
                        "label": f"FOMC rate decision and press conference "
                                 f"(meeting {span})",
                        "decision_day": True})
    # De-duplicate and sort; the page repeats some meetings across sections.
    seen, unique = set(), []
    for row in sorted(out, key=lambda r: r["date"]):
        if row["date"] not in seen:
            seen.add(row["date"])
            unique.append(row)
    return unique


def upcoming_fomc(days: int = 7) -> list[dict]:
    """FOMC meetings whose decision falls within the next `days` days."""
    import datetime as _dt

    today = _dt.date.today()
    horizon = today + _dt.timedelta(days=days)
    out = []
    for row in get_fomc_dates():
        try:
            day = _dt.date.fromisoformat(row["date"])
        except ValueError:
            continue
        if today <= day <= horizon:
            out.append(row)
    return out


_LEGAL_SUFFIX_RE = re.compile(
    r"[,]?\s+(Incorporated|Inc|Corporation|Corp|Company|Co|Limited|Ltd|plc|PLC|"
    r"N\.?V|S\.?A|AG|SE|Holdings|Holding|Group)\.?$", re.I)


def _tidy_company_name(name: str) -> str:
    """"Eli Lilly and Company" → "Eli Lilly"; "Visa Inc." → "Visa"."""
    name = (name or "").strip()
    for _ in range(3):                       # "… Holdings Corporation" etc.
        stripped = _LEGAL_SUFFIX_RE.sub("", name).strip()
        if stripped == name:
            break
        name = stripped
    # Removing the suffix can leave a dangling conjunction: "Eli Lilly and".
    return re.sub(r"\s+(and|&)$", "", name).strip(" ,.&") or name


@st.cache_data(ttl=3600, show_spinner=False)
def get_earnings_calendar(days: int = 7) -> list[dict]:
    """Upcoming earnings dates for major names, from Yahoo Finance.

    Returns [{"date": "2026-07-30", "symbol": "AAPL", "name": "Apple Inc."}, ...]
    sorted by date. Empty when the data is unavailable.
    """
    import datetime as _dt

    try:
        import yfinance as yf
    except Exception:
        return []

    today = _dt.date.today()
    horizon = today + _dt.timedelta(days=days)
    rows = []
    for sym in CALENDAR_TICKERS:
        try:
            ticker = yf.Ticker(sym)
            cal = ticker.calendar or {}
            dates = cal.get("Earnings Date") or []
            if not isinstance(dates, (list, tuple)):
                dates = [dates]
            for value in dates:
                day = value.date() if hasattr(value, "date") else value
                if isinstance(day, _dt.date) and today <= day <= horizon:
                    info = ticker.info or {}
                    name = (info.get("shortName") or info.get("longName") or sym)
                    name = _tidy_company_name(name)
                    rows.append({"date": day.isoformat(), "symbol": sym,
                                 "name": name or sym})
                    break
        except Exception:
            continue
    return sorted(rows, key=lambda r: (r["date"], r["symbol"]))


def macro_calendar(days: int = 7) -> list[dict]:
    """US macro releases whose dates follow a fixed, checkable rule.

    Only the ones with a deterministic schedule are generated here — weekly
    jobless claims, non-farm payrolls, the ISM surveys and the PCE report. CPI
    and PPI move around within the month, so they are deliberately left out
    rather than printed with a guessed date.
    """
    import datetime as _dt

    today = _dt.date.today()
    out = []

    def business_days(year, month):
        day, days_out = _dt.date(year, month, 1), []
        while day.month == month:
            if day.weekday() < 5:
                days_out.append(day)
            day += _dt.timedelta(days=1)
        return days_out

    for offset in range(days + 1):
        day = today + _dt.timedelta(days=offset)
        bdays = business_days(day.year, day.month)
        if not bdays:
            continue
        if day.weekday() == 3:                       # Thursday
            out.append({"date": day.isoformat(),
                        "label": "US weekly initial jobless claims"})
        if day.weekday() == 4 and day.day <= 7:      # first Friday
            out.append({"date": day.isoformat(),
                        "label": "US non-farm payrolls and unemployment rate"})
        if day == bdays[0]:
            out.append({"date": day.isoformat(),
                        "label": "US ISM Manufacturing PMI"})
        if len(bdays) > 2 and day == bdays[2]:
            out.append({"date": day.isoformat(),
                        "label": "US ISM Services PMI"})
        if day == bdays[-1]:
            out.append({"date": day.isoformat(),
                        "label": "US personal income and outlays (PCE price index)"})
    return sorted(out, key=lambda r: r["date"])


# The overnight reverse-repo award rate is the effective floor of the money market,
# so the curve is anchored there rather than starting at the 3-month bill.
RRP_RESULTS_URL = ("https://markets.newyorkfed.org/api/rp/reverserepo/all/results/"
                   "last/{count}.json")


@st.cache_data(ttl=3600, show_spinner=False)
def get_rrp_history(count: int = 250) -> list[dict]:
    """ON RRP award rate by operation date, newest first, from the New York Fed.

    Returns [{"date": "2026-07-28", "rate": 3.5}, ...]; empty on failure.
    """
    try:
        import requests

        r = requests.get(RRP_RESULTS_URL.format(count=count), headers=UA, timeout=15)
        operations = r.json().get("repo", {}).get("operations", [])
    except Exception:
        return []

    out = []
    for op in operations:
        if "reverse" not in str(op.get("operationType", "")).lower():
            continue
        details = op.get("details") or []
        rate = next((d.get("percentAwardRate") for d in details
                     if d.get("percentAwardRate") is not None), None)
        date = op.get("operationDate")
        if rate is None or not date:
            continue
        out.append({"date": str(date)[:10], "rate": float(rate)})
    return sorted(out, key=lambda r: r["date"], reverse=True)


def rrp_rate_on(target_iso: str | None = None) -> float | None:
    """ON RRP award rate on (or most recently before) a date. Latest when None."""
    history = get_rrp_history()
    if not history:
        return None
    if not target_iso:
        return history[0]["rate"]
    for row in history:                      # newest first
        if row["date"] <= target_iso:
            return row["rate"]
    return history[-1]["rate"]


# Treasury-curve and volatility-term-structure tickers.
YIELD_CURVE_POINTS = [("3M", "^IRX"), ("5Y", "^FVX"), ("10Y", "^TNX"), ("30Y", "^TYX")]
VIX_TERM_POINTS = [("9-day", "^VIX9D"), ("30-day", "^VIX"),
                   ("3-month", "^VIX3M"), ("6-month", "^VIX6M")]


@st.cache_data(ttl=900, show_spinner=False)
def get_group_performance(pairs: tuple, timeframe: str):
    """Return-over-timeframe for a (name, symbol) tuple set. Returns (rows, live)."""
    rows = []
    for name, sym in pairs:
        dates, values, live = get_history(sym, timeframe)
        if live and len(values) >= 2 and values[0]:
            rows.append({"name": name,
                         "change": round((values[-1] / values[0] - 1) * 100, 2)})
    return rows, bool(rows)


@st.cache_data(ttl=900, show_spinner=False)
def get_curve(points: tuple, timeframe: str, anchor_rrp: bool = False):
    """Now-vs-start-of-timeframe values for curve tickers (yields or vol term).

    Returns (rows, live) where each row is {"label", "now", "then"}; yields
    quoted at 10x (^TNX style) are normalised to percent. With `anchor_rrp` the
    curve starts at the overnight reverse-repo award rate — the floor the rest of
    the curve is priced off — rather than at the 3-month bill.
    """
    rows, start_date = [], None
    for label, sym in points:
        dates, values, live = get_history(sym, timeframe)
        if not (live and len(values) >= 2):
            continue
        if start_date is None and dates:
            start_date = dates[0]
        now, then = values[-1], values[0]
        if sym in ("^TNX", "^TYX", "^FVX", "^IRX") and now > 20:
            now, then = now / 10, then / 10
        rows.append({"label": label, "now": round(now, 2), "then": round(then, 2)})

    if anchor_rrp and rows:
        now_rate = rrp_rate_on()
        then_rate = rrp_rate_on(start_date) if start_date else now_rate
        if now_rate is not None:
            rows.insert(0, {"label": "O/N RRP",
                            "now": round(now_rate, 2),
                            "then": round(then_rate if then_rate is not None
                                          else now_rate, 2)})
    return rows, bool(rows)


# Figures Yahoo reports in the company's own accounting currency.
_STATEMENT_FIELDS = ("totalRevenue", "ebitda", "grossProfit", "freeCashflow",
                     "operatingCashflow", "totalDebt", "totalCash", "netIncomeToCommon")

# Ratios and percentages that are currency-neutral, taken from Yahoo as-is.
_NEUTRAL_FIELDS = [
    ("Trailing P/E", "trailingPE", "x"),
    ("Forward P/E", "forwardPE", "x"),
    ("PEG", "pegRatio", ""),
    ("Gross margin", "grossMargins", "%"),
    ("Operating margin", "operatingMargins", "%"),
    ("Profit margin", "profitMargins", "%"),
    ("ROE", "returnOnEquity", "%"),
    ("Revenue growth (yoy)", "revenueGrowth", "%"),
    ("Earnings growth (yoy)", "earningsGrowth", "%"),
    ("Beta", "beta", ""),
    ("Dividend yield", "dividendYield", "%"),
]


def _fmt_fundamental(value, unit: str, key: str = "") -> str:
    if value is None:
        return "n/a"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)
    if unit == "$" or unit == "#":
        for div, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
            if abs(value) >= div:
                return f"{'$' if unit == '$' else ''}{value / div:,.2f}{suffix}"
        return f"{'$' if unit == '$' else ''}{value:,.0f}"
    if unit == "%":
        # yfinance already returns dividendYield in percent; the rest are fractions.
        if key == "dividendYield":
            return f"{value:.2f}%"
        return f"{value * 100:.1f}%" if abs(value) <= 5 else f"{value:.1f}%"
    if unit == "x":
        return f"{value:.1f}x"
    return f"{value:,.2f}"


@st.cache_data(ttl=3600, show_spinner=False)
def get_fx_rate(base: str, quote: str = "USD") -> float | None:
    """Spot FX rate to convert `base` into `quote`. None when unavailable."""
    base, quote = (base or "").upper(), (quote or "USD").upper()
    if not base or base == quote:
        return 1.0
    try:
        import yfinance as yf

        hist = yf.download(f"{base}{quote}=X", period="5d", interval="1d",
                           progress=False, auto_adjust=True)["Close"].dropna()
        if hist.ndim > 1:
            hist = hist.iloc[:, 0].dropna()
        if len(hist):
            return float(hist.iloc[-1])
    except Exception:
        pass
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def get_fundamentals(symbol: str) -> dict:
    """Valuation and financial metrics for one security, from Yahoo Finance.

    Where the company reports in a different currency from the one it trades in,
    the mixed-currency ratios are converted at spot so they are directly
    comparable with peers, and the conversion is recorded for disclosure.
    """
    try:
        import yfinance as yf

        info = yf.Ticker(symbol).info or {}
        if not info.get("currentPrice") and not info.get("marketCap"):
            return {}
        trade_ccy = (info.get("currency") or "USD").upper()
        fin_ccy = (info.get("financialCurrency") or trade_ccy).upper()
        mismatch = bool(fin_ccy and fin_ccy != trade_ccy)

        # Rate that turns a reporting-currency figure into a listing-currency one.
        fx = get_fx_rate(fin_ccy, trade_ccy) if mismatch else 1.0
        if fx is None:
            fx = 1.0
        converted = mismatch and fx != 1.0

        def money(key):
            """Statement figure expressed in the listing currency."""
            v = info.get(key)
            if not isinstance(v, (int, float)):
                return None
            return v * fx if converted else float(v)

        def ratio(numer, denom):
            if numer is None or not denom:
                return None
            return numer / denom

        market_cap = info.get("marketCap")
        market_cap = float(market_cap) if isinstance(market_cap, (int, float)) else None
        revenue, ebitda = money("totalRevenue"), money("ebitda")
        debt, cash = money("totalDebt"), money("totalCash")
        # Yahoo's own enterpriseValue mixes currencies for foreign issuers, so
        # rebuild it from the pieces whose units are known.
        ev = None
        if market_cap is not None:
            ev = market_cap + (debt or 0.0) - (cash or 0.0)

        out = {"symbol": symbol.upper(),
               "name": info.get("longName") or info.get("shortName") or symbol.upper(),
               "sector": info.get("sector", ""),
               "industry": info.get("industry", ""),
               "currency": trade_ccy,
               "financial_currency": fin_ccy,
               "currency_mismatch": mismatch,
               "fx_rate": fx,
               "fx_applied": converted,
               "metrics": {}, "raw": dict(info), "computed": {}}

        m = out["metrics"]
        m["Price"] = _fmt_fundamental(info.get("currentPrice"), "")
        m["Market cap"] = _fmt_fundamental(market_cap, "$")
        m["Enterprise value"] = _fmt_fundamental(ev, "$")
        m["Revenue (ttm)"] = _fmt_fundamental(revenue, "$")
        m["EBITDA"] = _fmt_fundamental(ebitda, "$")
        for label, key, unit in _NEUTRAL_FIELDS:
            m[label] = _fmt_fundamental(info.get(key), unit, key)
        # Derived from figures now known to be in one currency.
        m["Price/Sales"] = _fmt_fundamental(ratio(market_cap, revenue), "x")
        m["EV/Revenue"] = _fmt_fundamental(ratio(ev, revenue), "x")
        m["EV/EBITDA"] = _fmt_fundamental(ratio(ev, ebitda), "x")
        m["Free cash flow"] = _fmt_fundamental(money("freeCashflow"), "$")
        m["Operating cash flow"] = _fmt_fundamental(money("operatingCashflow"), "$")
        m["Total debt"] = _fmt_fundamental(debt, "$")
        m["Total cash"] = _fmt_fundamental(cash, "$")
        m["Net cash / (debt)"] = _fmt_fundamental(
            None if (cash is None or debt is None) else cash - debt, "$")
        m["Analyst target"] = _fmt_fundamental(info.get("targetMeanPrice"), "")
        m["Shares outstanding"] = _fmt_fundamental(info.get("sharesOutstanding"), "#")

        out["computed"] = {"market_cap": market_cap, "ev": ev, "revenue": revenue,
                           "ebitda": ebitda, "debt": debt, "cash": cash,
                           "fcf": money("freeCashflow")}
        return out
    except Exception:
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def get_comparables(symbol: str, peers: tuple) -> list[dict]:
    """Side-by-side valuation multiples, all normalised to the listing currency."""
    rows = []
    for sym in (symbol,) + tuple(peers):
        f = get_fundamentals(sym)
        if not f:
            continue
        rows.append({
            "symbol": f["symbol"],
            "name": f["name"],
            "is_subject": f["symbol"] == symbol.upper(),
            "sector": f.get("sector", ""),
            "industry": f.get("industry", ""),
            "currency": f.get("currency", "USD"),
            "converted_from": f["financial_currency"] if f.get("fx_applied") else "",
            "market_cap": f["metrics"].get("Market cap", "n/a"),
            "fwd_pe": f["metrics"].get("Forward P/E", "n/a"),
            "trail_pe": f["metrics"].get("Trailing P/E", "n/a"),
            "ev_ebitda": f["metrics"].get("EV/EBITDA", "n/a"),
            "ps": f["metrics"].get("Price/Sales", "n/a"),
            "rev_growth": f["metrics"].get("Revenue growth (yoy)", "n/a"),
            "op_margin": f["metrics"].get("Operating margin", "n/a"),
        })
    return rows


@st.cache_data(ttl=3600, show_spinner=False)
def get_sector_peers(symbol: str, count: int = 5) -> tuple:
    """Peers that genuinely sit in the same sector as `symbol`.

    Yahoo's "people also watch" list is behavioural, not fundamental, so it mixes
    in whatever else the crowd happens to hold. Anything from another sector is
    dropped, and industry matches are preferred over merely sharing a sector.
    """
    subject = get_fundamentals(symbol)
    if not subject:
        return tuple(get_peers(symbol, count)), ""
    sector, industry = subject.get("sector", ""), subject.get("industry", "")

    same_industry, same_sector = [], []
    for sym in get_peers(symbol, count + 5):
        f = get_fundamentals(sym)
        if not f or not sector or f.get("sector") != sector:
            continue
        (same_industry if f.get("industry") == industry else same_sector).append(sym)

    # Same industry is the real comparable set. Others in the sector are only
    # topped up when there are too few — a software name is a poor yardstick for
    # a foundry even though both sit under "Technology".
    picked = same_industry[:count]
    if len(picked) < 3:
        picked += [s for s in same_sector if s not in picked][:3 - len(picked)]
    return tuple(picked), sector


@st.cache_data(ttl=3600, show_spinner=False)
def get_peers(symbol: str, count: int = 5) -> list[str]:
    """Yahoo's 'people also watch' peers for a security. Empty list on failure."""
    try:
        import requests

        url = ("https://query2.finance.yahoo.com/v6/finance/"
               f"recommendationsbysymbol/{symbol}")
        r = requests.get(url, headers=UA, timeout=8)
        rows = r.json()["finance"]["result"][0]["recommendedSymbols"]
        return [row["symbol"] for row in rows[:count] if row.get("symbol")]
    except Exception:
        return []


@st.cache_data(ttl=3600, show_spinner=False)
def lookup_symbol(query: str):
    """Resolve free text ("apple", "2330.TW", "tsmc") to (symbol, name) via Yahoo.

    Returns (None, None) when nothing matches.
    """
    query = (query or "").strip()
    if not query:
        return None, None
    try:
        import yfinance as yf

        hits = yf.Search(query, max_results=5).quotes
        for h in hits:
            if h.get("symbol"):
                return h["symbol"], h.get("shortname") or h.get("longname") or h["symbol"]
    except Exception:
        pass
    # Fall back to treating the text as a ticker if it has price history.
    sym = query.upper()
    dates, _, live = get_history(sym, "1M")
    if live and dates:
        return sym, sym
    return None, None


def _fmt_time(entry) -> str:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return _time.strftime("%b %d, %H:%M", parsed)
    return entry.get("published", "")[:16]


def _entry_epoch(entry) -> float:
    """Publish time as a UNIX timestamp, or 0.0 when the feed omits one."""
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return 0.0
    try:
        return _calendar.timegm(parsed)      # feed times are UTC
    except Exception:
        return 0.0


def _age_label(epoch: float) -> str:
    """Human age used in the UI so staleness is visible at a glance."""
    if not epoch:
        return ""
    hours = max(0.0, (_time.time() - epoch) / 3600.0)
    if hours < 1:
        return f"{int(hours * 60)}m ago"
    if hours < 24:
        return f"{int(hours)}h ago"
    return f"{int(hours // 24)}d ago"


@st.cache_data(ttl=600, show_spinner=False)
def get_headlines():
    """Live headlines across CNBC / Seeking Alpha / Yahoo Finance. Returns (headlines, live)."""
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
                    epoch = _entry_epoch(e)
                    out.append({
                        "source": source,
                        "category": category,
                        "title": title,
                        "summary": _clean(e.get("summary", "")),
                        "time": _fmt_time(e),
                        "epoch": epoch,
                        "age": _age_label(epoch),
                        "sentiment": _sentiment(title),
                        "link": e.get("link", ""),
                    })
            except Exception:
                continue  # one dead feed shouldn't kill the rest
        if len(out) < 3:
            raise ValueError("feeds unavailable")

        # Several feeds mix today's stories with evergreen items months old, so
        # drop anything stale. If that leaves too little (quiet weekend, feed
        # outage), widen the window step by step rather than showing an empty page.
        dated = [i for i in out if i["epoch"]]
        undated = [i for i in out if not i["epoch"]]
        fresh = []
        for window in (MAX_AGE_HOURS, 48, 72, 168):
            cutoff = _time.time() - window * 3600
            fresh = [i for i in dated if i["epoch"] >= cutoff]
            if len(fresh) >= MIN_ARTICLES:
                break
        # Undated entries are kept only as a last resort.
        pool = fresh or (dated or undated)

        # Newest first within each source, then round-robin so no single feed
        # dominates the top of the list while the whole set stays current.
        by_source: dict[str, list] = {}
        for item in sorted(pool, key=lambda i: -i["epoch"]):
            by_source.setdefault(item["source"], []).append(item)
        interleaved = []
        while any(by_source.values()):
            for src in list(by_source):
                if by_source[src]:
                    interleaved.append(by_source[src].pop(0))
        return _dedupe(interleaved), True
    except Exception:
        return d.HEADLINES, False


_STOPWORDS = {"the", "a", "an", "and", "or", "of", "in", "on", "as", "to", "for",
              "with", "at", "by", "its", "is", "are", "after", "amid", "over"}


def _canonical_url(link: str) -> str:
    """Article URL stripped of tracking noise, for exact-duplicate detection.

    The same story arrives from several feeds with different query strings
    (?.tsrc=rss, utm_*), so the raw URL is not a reliable key on its own.
    """
    if not link:
        return ""
    link = link.split("#", 1)[0].split("?", 1)[0]
    return link.rstrip("/").lower()


def _title_tokens(title: str) -> set:
    """Comparable tokens for a headline, in Latin script or CJK.

    A word regex returns nothing at all for Chinese headlines, which used to
    make every 奇摩股市 story look unique — CJK is tokenised as character
    bigrams instead.
    """
    lower = title.lower()
    words = {w for w in re.findall(r"[a-z0-9]+", lower)
             if w not in _STOPWORDS and len(w) > 2}
    cjk = re.sub(r"[^一-鿿぀-ヿ]", "", title)
    words |= {cjk[i:i + 2] for i in range(len(cjk) - 1)}
    return words


def _dedupe(items: list[dict]) -> list[dict]:
    """Collapse duplicate coverage of the same story across feeds.

    Three passes, cheapest first: identical canonical URL, identical headline,
    then a token-overlap check for the same story written up differently.
    Keeps the first item and notes which other sources also carried it.
    """
    kept, by_url, by_title = [], {}, {}
    for item in items:
        url = _canonical_url(item.get("link", ""))
        title_key = re.sub(r"\s+", " ", item["title"]).strip().lower()

        dup_of = by_url.get(url) if url else None
        if dup_of is None:
            dup_of = by_title.get(title_key)
        if dup_of is None:
            tokens = _title_tokens(item["title"])
            if tokens:
                for k in kept:
                    shared = tokens & k["_words"]
                    if not shared:
                        continue
                    overlap = len(shared) / max(1, min(len(tokens), len(k["_words"])))
                    if overlap >= 0.6:
                        dup_of = k
                        break

        if dup_of is not None:
            if item["source"] != dup_of["source"] and item["source"] not in dup_of["also_in"]:
                dup_of["also_in"].append(item["source"])
            continue

        item["_words"] = _title_tokens(item["title"])
        item["also_in"] = []
        kept.append(item)
        if url:
            by_url[url] = item
        by_title[title_key] = item

    for k in kept:
        k.pop("_words", None)
    return kept


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
                    if not title:
                        continue
                    epoch = _entry_epoch(e)
                    items.append({
                        "source": source, "category": symbol.upper(), "title": title,
                        "summary": _clean(e.get("summary", "")), "time": _fmt_time(e),
                        "epoch": epoch, "age": _age_label(epoch),
                        "sentiment": _sentiment(title), "link": e.get("link", ""),
                    })
            except Exception:
                continue

    # Supplement with general headlines mentioning the topic. An empty symbol must
    # not be treated as a match, or every headline would qualify.
    headlines, _ = get_headlines()
    sym_l = symbol.lower().strip()
    words = [w.lower() for w in re.findall(r"[A-Za-z0-9]+", topic) if len(w) > 3]
    for h in headlines:
        blob = (h["title"] + " " + h.get("summary", "")).lower()
        if (words and any(w in blob for w in words)) or (sym_l and sym_l in blob):
            items.append(h)

    # Deeper pulls widen the pool, so the same story can arrive several ways.
    items = _dedupe(items)
    items.sort(key=lambda i: -i.get("epoch", 0))
    return items[:limit]


# Boilerplate lines that surround the article body on every site.
_NAV_MARKERS = ("skip to", "sign in", "create free account", "watchlist", "subscribe",
                "newsletter", "terms of service", "privacy policy", "all rights reserved",
                "follow us", "advertisement", "cookie", "©")


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_article_text(url: str, limit: int = 9000) -> str:
    """Full body text of one article, stripped of navigation boilerplate.

    Headlines and RSS summaries rarely contain the quote itself, so anything that
    needs to find who said what has to read the actual page.
    """
    if not url:
        return ""
    try:
        import requests

        r = requests.get(url, headers=UA, timeout=15)
        if r.status_code >= 400:
            return ""
        doc = re.sub(r"(?is)<(script|style|noscript|nav|header|footer)[^>]*>.*?</\1>",
                     " ", r.text)
        out = []
        for para in re.findall(r"(?is)<p[^>]*>(.*?)</p>", doc):
            text = html.unescape(re.sub(r"<[^>]+>", "", para)).strip()
            text = re.sub(r"\s+", " ", text)
            if len(text) < 60:
                continue
            low = text.lower()
            if any(m in low for m in _NAV_MARKERS):
                continue
            out.append(text)
        body = "\n".join(out)
        return body[:limit]
    except Exception:
        return ""


def fetch_many_texts(urls: list[str], limit: int = 9000) -> dict[str, str]:
    """Fetch several article bodies at once. Returns {url: text}, failures omitted."""
    import concurrent.futures as cf

    out: dict[str, str] = {}
    urls = [u for u in dict.fromkeys(urls) if u]
    if not urls:
        return out
    with cf.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch_article_text, u, limit): u for u in urls}
        for fut in cf.as_completed(futures, timeout=90):
            url = futures[fut]
            try:
                text = fut.result()
                if text:
                    out[url] = text
            except Exception:
                continue
    return out


@st.cache_data(ttl=900, show_spinner=False)
def search_news(query: str, limit: int = 20) -> list[dict]:
    """Fetch fresh coverage for a keyword or ticker beyond what's already pulled.

    Resolves the query to a ticker where possible and pulls that security's
    per-source feeds, so a search finds articles the general feeds never carried.
    """
    import feedparser
    import requests

    query = (query or "").strip()
    if not query:
        return []

    symbol, _name = lookup_symbol(query)
    feeds = []
    if symbol:
        feeds = [("Yahoo Finance", symbol, YF_TICKER_FEED.format(symbol=symbol)),
                 ("Seeking Alpha", symbol, SA_TICKER_FEED.format(symbol=symbol))]

    out = []
    for source, category, url in feeds:
        try:
            r = requests.get(url, headers=UA, timeout=10)
            for e in feedparser.parse(r.content).entries[:limit]:
                title = _clean(e.get("title", ""), 160)
                if not title:
                    continue
                epoch = _entry_epoch(e)
                out.append({
                    "source": source, "category": str(category).upper(), "title": title,
                    "summary": _clean(e.get("summary", "")), "time": _fmt_time(e),
                    "epoch": epoch, "age": _age_label(epoch),
                    "sentiment": _sentiment(title), "link": e.get("link", ""),
                })
        except Exception:
            continue

    out.sort(key=lambda i: -i["epoch"])
    return _dedupe(out)[:limit]


def articles_mentioning(term: str, articles: list[dict]) -> list[dict]:
    """Articles whose headline or summary mentions a person, firm or topic."""
    words = [w.lower() for w in re.findall(r"[A-Za-z0-9']+", term) if len(w) > 2]
    if not words:
        return []
    hits = []
    for a in articles:
        blob = (a.get("title", "") + " " + a.get("summary", "")).lower()
        if all(w in blob for w in words) or (len(words) > 1 and words[-1] in blob):
            hits.append(a)
    return hits


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
