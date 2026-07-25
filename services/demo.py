"""Canned chatbot replies for demo mode (no API key configured)."""

_FALLBACK = (
    "**Demo mode.** I can answer a few sample questions about the current dataset — try asking "
    "about *TSMC*, *the Fed*, *buyside positioning*, or *where sources disagree*. "
    "To chat freely, add an Anthropic API key in the sidebar."
)

_CANNED = {
    "tsmc": (
        "**TSMC across our sources (sample data):** CNBC reports July revenue up 31% y/y with the "
        "N2 ramp on track. On Seeking Alpha, 14 of 18 recent notes rate TSM Buy/Strong Buy. The "
        "buyside is even more constructive: a growth manager sets fair value at NT\\$1,450 on N2 "
        "pricing power, and a multi-strategy fund is long TSM against a short basket of "
        "speculative AI names, hedging Taiwan-strait risk via FX options. Main bear points: NT\\$ "
        "strength compressing margins, and tariff uncertainty."
    ),
    "fed": (
        "**Fed path (sample data):** Bloomberg Intelligence economists moved their first-cut call "
        "from September to December, citing core inflation sticky at 2.8%. Notably, buyside "
        "letters had already migrated to December — the sell-side/buyside gap on cut timing has "
        "now closed, which itself was a useful positioning signal while it lasted. Fixed-income "
        "managers favour the 3–7y belly of the curve."
    ),
    "buyside": (
        "**Buyside positioning snapshot (sample data):** Q2 13F filings show hedge funds adding "
        "semiconductors and defensives while trimming consumer cyclicals. Asset managers are "
        "overweight the AI supply chain and Asia ex-Japan on a softer dollar. Hedge funds express "
        "the AI theme through relative-value structures (long infrastructure vs. short concept "
        "names) rather than outright longs, and quant desks flag momentum crowding at the 96th "
        "percentile."
    ),
    "disagree": (
        "**Where sources diverge (sample data):** (1) AI capex — media coverage is upbeat on the "
        "\\$420bn hyperscaler spend, but an event-driven fund argues debt-funded capex and 2027 "
        "depreciation will force a margin re-rating. (2) Taiwan risk — private-bank outlooks "
        "treat it as a reason to trim; hedge funds instead hedge it with FX options and keep "
        "exposure. (3) Until recently, cut timing — sell-side said September, buyside December."
    ),
}


def demo_chat_reply(user_text: str) -> str:
    t = user_text.lower()
    if "tsm" in t or "taiwan semi" in t or "台積" in t:
        return _CANNED["tsmc"]
    if "fed" in t or "rate" in t or "cut" in t or "利率" in t:
        return _CANNED["fed"]
    if "buyside" in t or "hedge" in t or "position" in t or "13f" in t or "買方" in t:
        return _CANNED["buyside"]
    if "disagree" in t or "diverge" in t or "consensus" in t or "分歧" in t:
        return _CANNED["disagree"]
    return _FALLBACK
