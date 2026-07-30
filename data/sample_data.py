"""Offline fallback dataset.

Used only when the live connectors are unreachable, so the interface stays navigable
without a network. In normal operation every figure and headline shown in the app comes
from the selected sources: Seeking Alpha, Yahoo Finance, CNBC and SumZero.

All figures below are illustrative, not real quotes.
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
        "source": "Yahoo Finance",
        "title": "Fed officials signal patience on cuts as core inflation stays sticky at 2.8%",
        "summary": "Economists now see the first cut in December rather than September; "
                   "rates desks flag the front end as most exposed to repricing.",
        "time": "07:40 ET", "sentiment": "Neutral", "category": "Macro", "link": "",
    },
    {
        "source": "CNBC",
        "title": "AI capex supercycle shows no sign of slowing as hyperscalers guide higher",
        "summary": "Combined 2026 capex guidance from the four largest cloud providers now tops "
                   "\\$420bn, with most of the increase earmarked for AI infrastructure.",
        "time": "06:55 ET", "sentiment": "Positive", "category": "Technology", "link": "",
    },
    {
        "source": "CNBC",
        "title": "TSMC July sales beat expectations; N2 ramp on track for Q4 volume production",
        "summary": "Monthly revenue rose 31% y/y. Management reiterated that 2nm demand is "
                   "'stronger than 3nm at the same stage'.",
        "time": "05:20 ET", "sentiment": "Positive", "category": "Semiconductors", "link": "",
    },
    {
        "source": "Seeking Alpha",
        "title": "Contributor consensus on TSM: premium justified, but watch FX and tariff risk",
        "summary": "14 of 18 recent contributor notes rate TSM Buy or Strong Buy; bears focus on "
                   "NT\\$ appreciation compressing gross margin and US tariff uncertainty.",
        "time": "Today", "sentiment": "Positive", "category": "Semiconductors", "link": "",
    },
    {
        "source": "Seeking Alpha",
        "title": "The case for staying overweight quality large-caps into year-end",
        "summary": "Contributors argue earnings breadth is improving beyond the Mag 7, but "
                   "valuation dispersion argues for selectivity over index exposure.",
        "time": "Today", "sentiment": "Neutral", "category": "Strategy", "link": "",
    },
    {
        "source": "Yahoo Finance",
        "title": "Dollar softens as markets price higher odds of a Q4 policy pivot",
        "summary": "The DXY fell to a four-month low; EM and Asian currencies rallied, "
                   "with the NT\\$ among the strongest performers.",
        "time": "Yesterday", "sentiment": "Neutral", "category": "Macro", "link": "",
    },
]

# Shown on the dashboard when no AI provider is connected.
DEMO_OUTLOOK = (
    "**Sample synthesis (demo mode).** Across the selected sources the tone this week is "
    "cautiously constructive. CNBC coverage emphasises broadening earnings "
    "breadth and a softer dollar, while Seeking Alpha contributors are more divided on whether "
    "the AI infrastructure trade still offers value at current multiples. The clearest "
    "cross-source divergence is the timing of the first Fed cut. Connect Copilot in the sidebar "
    "to generate this synthesis live from the latest articles."
)
