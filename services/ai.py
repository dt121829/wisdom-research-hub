"""Claude API integration.

All AI features (dashboard outlook, chatbot, report generator) route through
this module. When no API key is configured the app falls back to canned demo
content so the interface remains fully navigable.
"""

import os

import streamlit as st

try:
    import anthropic
except ImportError:  # keeps the app importable even before deps are installed
    anthropic = None

MODEL = "claude-opus-5"

# Context injected into every AI call: live quotes + live headlines when the
# connectors are reachable, sample data otherwise. Buyside views are curated
# samples pending the Bloomberg Terminal integration.
def build_context() -> str:
    from datetime import datetime

    from data import sample_data as d
    from services import live_data

    indices, sectors, quotes_live = live_data.get_market_data()
    headlines, news_live = live_data.get_headlines()

    lines = []
    if quotes_live:
        lines.append(f"MARKET SNAPSHOT (live via Yahoo Finance, {datetime.now():%Y-%m-%d %H:%M}):")
    else:
        lines.append(f"MARKET SNAPSHOT (sample data as of {d.AS_OF.isoformat()}):")
    lines.append("; ".join(f"{i['name']} {i['value']} ({i['change']})" for i in indices))
    lines.append("Sector 1-day moves: " + "; ".join(f"{s['name']} {s['change']:+.1f}%" for s in sectors))
    lines.append("")
    lines.append("LATEST HEADLINES" + (" (live RSS from the sources)" if news_live else " (sample)") + ":")
    for h in headlines:
        lines.append(f"- [{h['source']}] {h['title']} — {h['summary']} (sentiment: {h['sentiment']})")
    lines.append("")
    lines.append("BUYSIDE VIEWS (asset managers / hedge funds — curated sample entries "
                 "pending Bloomberg Terminal integration):")
    for v in d.BUYSIDE_VIEWS:
        lines.append(
            f"- {v['firm']} ({v['firm_type']}, via {v['channel']}, {v['date']}) on {v['topic']}: "
            f"{v['stance']} / conviction {v['conviction']}. {v['view']}"
        )
    lines.append("")
    lines.append("CROSS-SOURCE CONSENSUS MAP:")
    for c in d.CONSENSUS:
        lines.append(f"- {c['theme']}: consensus = {c['consensus']} divergence = {c['divergence']}")
    return "\n".join(lines)


SYSTEM_PROMPT = """You are the research assistant of Wisdom Family Office. You help investment
staff synthesise market intelligence aggregated from five sources: Barron's, The Wall Street
Journal, CNBC, Seeking Alpha, and the firm's Bloomberg Terminal.

Ground every answer in the source material provided in the context block. Attribute claims to
their source (e.g. "per the Bloomberg 13F roundup..."). Distinguish clearly between sell-side
commentary and buyside views. When sources disagree, say so explicitly — surfacing divergence
is more valuable than a blended average. If the context does not cover a question, say what is
missing rather than inventing data. You provide research synthesis, not personalised investment
advice.

Formatting: output Markdown. Escape literal dollar signs as \\$ (the interface renders paired $
as LaTeX math)."""


def get_api_key() -> str | None:
    if st.session_state.get("api_key"):
        return st.session_state["api_key"]
    try:
        if "ANTHROPIC_API_KEY" in st.secrets:
            return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY")


def get_client():
    key = get_api_key()
    if key and anthropic is not None:
        return anthropic.Anthropic(api_key=key)
    return None


def live_mode() -> bool:
    return get_client() is not None


def stream_completion(messages: list[dict], system: str | None = None, max_tokens: int = 8000):
    """Yield text chunks from Claude. Caller guarantees a client exists."""
    client = get_client()
    full_system = (system or SYSTEM_PROMPT) + "\n\n<context>\n" + build_context() + "\n</context>"
    with client.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        system=full_system,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text
