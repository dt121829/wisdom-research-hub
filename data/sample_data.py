"""Sample dataset used for the demo.

In production these records are produced by the ingestion pipeline
(see the Sources & Methodology page): RSS/API pulls from CNBC, Seeking Alpha,
Barron's and WSJ, plus exports from the firm's Bloomberg Terminal.
All figures below are illustrative sample data, not live market quotes.
"""

from datetime import date, timedelta

AS_OF = date(2026, 7, 24)

# ---------------------------------------------------------------- indices ---
INDICES = [
    {"name": "S&P 500",   "value": "6,412.18", "change": "+0.42%", "delta": 0.42},
    {"name": "Nasdaq",    "value": "21,036.55", "change": "+0.71%", "delta": 0.71},
    {"name": "Dow Jones", "value": "45,180.30", "change": "-0.12%", "delta": -0.12},
    {"name": "TAIEX",     "value": "24,890.44", "change": "+1.05%", "delta": 1.05},
    {"name": "US 10Y",    "value": "4.18%",    "change": "-3 bps", "delta": -0.03},
    {"name": "VIX",       "value": "14.6",     "change": "-0.8",   "delta": -0.8},
]

# S&P 500, last 10 trading days (sample)
SP500_TREND = {
    "dates": [(AS_OF - timedelta(days=d)).isoformat() for d in (13, 12, 11, 10, 9, 6, 5, 4, 3, 2)],
    "values": [6301, 6318, 6290, 6335, 6352, 6344, 6371, 6389, 6385, 6412],
}

# --------------------------------------------------------------- sectors ----
SECTORS = [
    {"name": "Semiconductors",  "change": 1.8},
    {"name": "Technology",      "change": 1.1},
    {"name": "Comm. Services",  "change": 0.7},
    {"name": "Industrials",     "change": 0.4},
    {"name": "Financials",      "change": 0.2},
    {"name": "Health Care",     "change": -0.3},
    {"name": "Utilities",       "change": -0.5},
    {"name": "Energy",          "change": -0.9},
    {"name": "Real Estate",     "change": -1.2},
]

# -------------------------------------------------------------- headlines ---
HEADLINES = [
    {
        "source": "Bloomberg Terminal",
        "title": "Fed officials signal patience on cuts as core inflation stays sticky at 2.8%",
        "summary": "BI economists now see the first cut in December rather than September; "
                   "rates desks flag the front end as most exposed to repricing.",
        "time": "07:40 ET", "sentiment": "Neutral", "category": "Macro",
    },
    {
        "source": "WSJ",
        "title": "AI capex supercycle shows no sign of slowing as hyperscalers guide higher",
        "summary": "Combined 2026 capex guidance from the four largest cloud providers now tops "
                   "\\$420bn, with most of the increase earmarked for AI infrastructure.",
        "time": "06:55 ET", "sentiment": "Positive", "category": "Technology",
    },
    {
        "source": "CNBC",
        "title": "TSMC July sales beat expectations; N2 ramp on track for Q4 volume production",
        "summary": "Monthly revenue rose 31% y/y. Management reiterated that 2nm demand is "
                   "'stronger than 3nm at the same stage'.",
        "time": "05:20 ET", "sentiment": "Positive", "category": "Semiconductors",
    },
    {
        "source": "Seeking Alpha",
        "title": "Contributor consensus on TSM: premium justified, but watch FX and tariff risk",
        "summary": "14 of 18 recent contributor notes rate TSM Buy or Strong Buy; bears focus on "
                   "NT\\$ appreciation compressing gross margin and US tariff uncertainty.",
        "time": "Today", "sentiment": "Positive", "category": "Semiconductors",
    },
    {
        "source": "Barron's",
        "title": "The case for staying overweight quality large-caps into year-end",
        "summary": "Strategists argue earnings breadth is improving beyond the Mag 7, but "
                   "valuation dispersion argues for selectivity over index exposure.",
        "time": "Today", "sentiment": "Neutral", "category": "Strategy",
    },
    {
        "source": "Bloomberg Terminal",
        "title": "13F roundup: hedge funds added semis and defensives, trimmed consumer cyclicals",
        "summary": "Q2 filings show net adds concentrated in AI infrastructure names; "
                   "consumer discretionary saw the largest net reduction since 2022.",
        "time": "Yesterday", "sentiment": "Neutral", "category": "Positioning",
    },
    {
        "source": "WSJ",
        "title": "Dollar softens as markets price higher odds of a Q4 policy pivot",
        "summary": "The DXY fell to a four-month low; EM and Asian currencies rallied, "
                   "with the NT\\$ among the strongest performers.",
        "time": "Yesterday", "sentiment": "Neutral", "category": "Macro",
    },
]

# ---------------------------------------------------------- buyside views ---
BUYSIDE_VIEWS = [
    {
        "firm": "Bridgewater-style Global Macro Fund", "firm_type": "Hedge Fund",
        "channel": "Bloomberg Terminal — fund letter",
        "topic": "US Equities", "stance": "Neutral", "conviction": "Medium",
        "date": "2026-07-22",
        "view": "Equity risk premium is thin but not stretched. We are neutral US equities, "
                "long duration as a hedge, and prefer earning carry in quality credit. The "
                "asymmetry favours defensives if growth data softens into Q4.",
    },
    {
        "firm": "Sequoia-style Growth Manager", "firm_type": "Asset Manager",
        "channel": "Seeking Alpha — published note",
        "topic": "Taiwan Semiconductor (TSM)", "stance": "Bullish", "conviction": "High",
        "date": "2026-07-21",
        "view": "TSM remains the single most important AI infrastructure asset. N2 pricing "
                "power plus CoWoS capacity doubling in 2026 supports 25%+ revenue CAGR "
                "through 2028. We added on the July pullback; fair value NT\\$1,450.",
    },
    {
        "firm": "Elliott-style Activist / Event Fund", "firm_type": "Hedge Fund",
        "channel": "Bloomberg Terminal — 13F + call notes",
        "topic": "US Mega-cap Tech", "stance": "Bearish", "conviction": "Medium",
        "date": "2026-07-18",
        "view": "AI capex is being funded increasingly from debt rather than free cash flow. "
                "We see 2027 depreciation guidance as the catalyst that forces the market to "
                "re-underwrite hyperscaler margins. Trimming into strength.",
    },
    {
        "firm": "PIMCO-style Fixed Income House", "firm_type": "Asset Manager",
        "channel": "Bloomberg Terminal — strategy piece",
        "topic": "Rates & Credit", "stance": "Bullish", "conviction": "High",
        "date": "2026-07-20",
        "view": "The belly of the curve (3–7y) offers the best risk-adjusted carry in a "
                "decade. We expect two cuts by mid-2027 and favour IG credit over HY, "
                "where spreads no longer compensate for late-cycle default risk.",
    },
    {
        "firm": "Third Point-style Multi-strategy", "firm_type": "Hedge Fund",
        "channel": "Seeking Alpha — interview summary",
        "topic": "Taiwan Semiconductor (TSM)", "stance": "Bullish", "conviction": "Medium",
        "date": "2026-07-15",
        "view": "Long TSM against a basket of AI 'concept' names with no earnings support. "
                "The valuation gap between the picks-and-shovels layer and speculative AI "
                "names is the widest since 2021. Hedged for Taiwan-strait tail risk via FX options.",
    },
    {
        "firm": "Wellington-style Core Manager", "firm_type": "Asset Manager",
        "channel": "Bloomberg Terminal — quarterly outlook",
        "topic": "Asia ex-Japan", "stance": "Bullish", "conviction": "Medium",
        "date": "2026-07-19",
        "view": "A softer dollar historically precedes 12 months of Asia outperformance. "
                "Taiwan and Korea screen best on earnings revisions; India best on structural "
                "growth but is priced for perfection.",
    },
    {
        "firm": "Man Group-style Quant Fund", "firm_type": "Hedge Fund",
        "channel": "Bloomberg Terminal — factor commentary",
        "topic": "US Equities", "stance": "Neutral", "conviction": "Low",
        "date": "2026-07-23",
        "view": "Momentum crowding in AI infrastructure is at the 96th percentile. Our "
                "models stay long but with tightened stops; a 2-sigma factor unwind would "
                "hit semis hardest given positioning.",
    },
]

# Cross-source synthesis: where the street agrees and disagrees.
CONSENSUS = [
    {
        "theme": "AI infrastructure / semiconductors",
        "consensus": "Constructive — demand visibility through 2027 is the strongest of any sector.",
        "divergence": "Event-driven funds warn that debt-funded capex and rising depreciation "
                      "will compress hyperscaler margins in 2027; quants flag extreme momentum crowding.",
        "watch": "Hyperscaler capex guidance, CoWoS capacity adds, 2027 depreciation schedules.",
    },
    {
        "theme": "US rates path",
        "consensus": "First cut now expected in Q4 2026; belly of the curve favoured.",
        "divergence": "Sell-side (private bank outlooks) still leans September; buyside letters "
                      "have moved to December. The gap itself is a positioning signal.",
        "watch": "Core PCE prints, labour market revisions, Fed communication in September.",
    },
    {
        "theme": "Asia / Taiwan equities",
        "consensus": "Overweight on softer USD, earnings revisions, and the AI supply chain.",
        "divergence": "Macro funds hedge Taiwan-strait tail risk via FX options rather than "
                      "reducing exposure — a nuance private-bank outlooks rarely carry.",
        "watch": "NT\\$ strength vs. exporter margins, tariff headlines, TAIEX foreign flows.",
    },
]

# One-paragraph AI market outlook shown on the dashboard in demo mode.
DEMO_OUTLOOK = (
    "**Sample synthesis (demo mode).** Across the five monitored sources, the tone this week is "
    "cautiously constructive. Sell-side coverage (Barron's, WSJ) emphasises broadening earnings "
    "breadth and a softer dollar, while buyside voices are more nuanced: asset managers remain "
    "overweight the AI supply chain — TSMC in particular — but hedge funds are hedging the theme "
    "through relative-value structures rather than outright longs, and quant desks flag momentum "
    "crowding at the 96th percentile. The clearest cross-source divergence is the timing of the "
    "first Fed cut (sell-side: September; buyside: December). Connect an Anthropic API key in the "
    "sidebar to generate this synthesis live from the latest ingested content."
)
