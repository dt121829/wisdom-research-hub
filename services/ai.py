"""Shared context and system prompt for the conversational and report features.

Model access goes through services.llm, so this module is provider-agnostic.
"""

from datetime import datetime

import streamlit as st  # noqa: F401  (kept for callers that expect st to be loaded)

from services import llm

SOURCES = ["Seeking Alpha", "Yahoo Finance", "Yahoo 奇摩股市", "CNBC",
           "SumZero", "WhaleWisdom"]

SYSTEM_PROMPT = f"""You are the research assistant of Wisdom Family Office. You help
investment staff synthesise market intelligence aggregated from the firm's selected
sources: {', '.join(SOURCES)}.

Ground your answers in the material in the context block below — it comes from the
selected sources. Attribute claims to their source (e.g. "per CNBC..."). Only when the
context is missing information the user genuinely needs may you supplement from wider
knowledge, and every such point MUST end with the exact label:
⚠️ *external — not from selected sources*
Never present outside material as if it came from the selected sources.

Distinguish clearly between buyside voices (asset managers, hedge funds) and sell-side
or media commentary. When sources disagree, say so explicitly — surfacing divergence is
more valuable than a blended average. You provide research synthesis, not personalised
investment advice.

Formatting: output Markdown. Escape literal dollar signs as \\$ (the interface renders
paired $ as LaTeX math)."""


def build_context() -> str:
    """Assemble the live source material handed to the model on every call."""
    from services import live_data

    indices, sectors, quotes_live = live_data.get_market_data()
    headlines, news_live = live_data.get_headlines()

    lines = []
    if quotes_live:
        lines.append(f"MARKET SNAPSHOT (Yahoo Finance, {datetime.now():%Y-%m-%d %H:%M}):")
    else:
        lines.append("MARKET SNAPSHOT (sample data — live quotes unavailable):")
    lines.append("; ".join(f"{i['name']} {i['value']} ({i['change']})" for i in indices))
    lines.append("Sector 1-day moves: "
                 + "; ".join(f"{s['name']} {s['change']:+.1f}%" for s in sectors))
    lines.append("")
    lines.append("ARTICLE MATERIAL"
                 + (" (live RSS from the approved sources):" if news_live else " (sample):"))
    for h in headlines:
        lines.append(f"- [{h['source']}] {h['title']} — {h['summary']} "
                     f"(sentiment: {h['sentiment']})")

    sa_items, sa_live = live_data.get_sa_analysis()
    if sa_live:
        lines.append("")
        lines.append("SEEKING ALPHA — LATEST INDEPENDENT ANALYSIS:")
        for item in sa_items:
            author = f" by {item['author']}" if item["author"] else ""
            lines.append(f"- {item['title']}{author}")

    return "\n".join(lines)


def live_mode() -> bool:
    return llm.live()


def provider_label() -> str:
    return llm.provider_label()


def stream_completion(messages: list[dict], system: str | None = None,
                      max_tokens: int = 8000, reasoning_effort: str | None = None):
    """Stream a completion with the live source material attached."""
    full_system = ((system or SYSTEM_PROMPT)
                   + "\n\n<context>\n" + build_context() + "\n</context>")
    return llm.stream(messages, full_system, max_tokens=max_tokens,
                      reasoning_effort=reasoning_effort)
