"""AI analysis over the approved sources.

Three products, all cached so a rerun never re-bills the model:
  market_outlook()  – dashboard synthesis plus the articles it drew on
  news_digest()     – short summary under the headline list
  buyside_views()   – named parties expressing views, cross-checked across sources

Everything here reads only from services.live_data, which is restricted to
Barron's, WSJ, CNBC, Seeking Alpha and Yahoo Finance.
"""

import hashlib
import re

import streamlit as st

from services import llm

SOURCE_RULE = (
    "You may use ONLY the article material supplied in the prompt. It comes from "
    "Barron's, The Wall Street Journal, CNBC, Seeking Alpha and Yahoo Finance. "
    "Never introduce facts, figures, or opinions from outside it, and never rely on "
    "your own prior knowledge of markets. If the material does not support a claim, "
    "leave the claim out."
)

ANALYST_SYSTEM = (
    "You are the research analyst of Wisdom Family Office, synthesising market "
    "intelligence for investment staff. " + SOURCE_RULE +
    " Attribute claims to their source. Where sources disagree, surface the "
    "disagreement rather than averaging it away. Write in clean Markdown and escape "
    "literal dollar signs as \\$."
)


def _key(items: list[dict], *extra: str) -> str:
    """Stable hash of the article set, so the cache turns over when the news does."""
    blob = "|".join(i.get("title", "") for i in items) + "|".join(extra)
    return hashlib.sha256(blob.encode("utf-8", "ignore")).hexdigest()[:16]


def _format_articles(items: list[dict]) -> str:
    return "\n".join(
        f"[{i['source']}] {i['title']} — {i.get('summary', '')}" for i in items
    )


# ------------------------------------------------------------ market outlook

@st.cache_data(ttl=1800, show_spinner=False)
def market_outlook(cache_key: str, _articles: list, _snapshot: str) -> dict:
    """Return {'summary': markdown, 'sources': [article, ...]}."""
    prompt = f"""Today's market snapshot:
{_snapshot}

Article material from the approved sources:
{_format_articles(_articles)}

Write a market outlook of 180-240 words for investment staff. Structure it as:
- One opening sentence giving the overall tone of the market right now.
- Two or three sentences on the themes the sources agree on.
- One or two sentences on the most important disagreement or tension between sources.
- A closing sentence on what to watch next.

Cite sources inline in brackets, e.g. [WSJ], [CNBC]. Do not use headings."""

    summary = llm.complete(prompt, ANALYST_SYSTEM, max_tokens=1200)
    return {"summary": summary, "sources": _articles}


# --------------------------------------------------------------- news digest

@st.cache_data(ttl=1800, show_spinner=False)
def news_digest(cache_key: str, _articles: list) -> str:
    prompt = f"""Article material from the approved sources:
{_format_articles(_articles)}

In 60-90 words, tell an investment professional what these headlines collectively
mean today. Identify the dominant thread running through them, and note anything
that looks like an outlier worth a second look. Plain prose, no bullet points,
no headings. Cite sources inline in brackets."""
    return llm.complete(prompt, ANALYST_SYSTEM, max_tokens=600)


# -------------------------------------------------------------- buyside views

PARTY_TYPES = ["Asset Manager", "Hedge Fund", "Bank / Broker", "Analyst",
               "Company Executive", "Policymaker", "Other"]

BUYSIDE_TYPES = {"Asset Manager", "Hedge Fund"}

EXTRACTION_SYSTEM = (
    "You extract attributed market views from news articles for an investment "
    "research desk. " + SOURCE_RULE +
    " Extract only views that are genuinely attributed to a named party in the "
    "material. Never invent a party, a quote, or a stance. If an article states no "
    "attributed view, skip it entirely. Accuracy matters far more than volume."
)


@st.cache_data(ttl=1800, show_spinner=False)
def buyside_views(cache_key: str, _articles: list) -> list[dict]:
    """Extract attributed views, then flag parties appearing in more than one source."""
    prompt = f"""Article material from the approved sources:
{_format_articles(_articles)}

Identify every market view that is explicitly attributed to a named party — an asset
manager, hedge fund, bank, analyst, company executive, or policymaker.

Return JSON of exactly this shape:
{{"views": [
  {{"party": "name of the firm or person",
    "party_type": one of {PARTY_TYPES},
    "stance": "Bullish" or "Bearish" or "Neutral",
    "topic": "what the view is about, a few words",
    "view": "one or two sentences stating their view, grounded in the article",
    "source": "which source it came from",
    "headline": "the headline it came from"}}
]}}

Return an empty list if the material contains no attributed views."""

    data = llm.complete_json(prompt, EXTRACTION_SYSTEM, max_tokens=4000)
    views = data.get("views", []) if isinstance(data, dict) else (data or [])

    cleaned = []
    for v in views:
        if not isinstance(v, dict) or not v.get("party") or not v.get("view"):
            continue
        v["party_type"] = v.get("party_type") if v.get("party_type") in PARTY_TYPES else "Other"
        v["stance"] = v.get("stance") if v.get("stance") in ("Bullish", "Bearish", "Neutral") else "Neutral"
        v["is_buyside"] = v["party_type"] in BUYSIDE_TYPES
        # Link back to the originating article where we can match the headline.
        v["link"] = next((a.get("link", "") for a in _articles
                          if a.get("title") == v.get("headline")), "")
        cleaned.append(v)

    return _cross_reference(cleaned)


_SUFFIXES = ("inc", "llc", "ltd", "plc", "group", "corp", "corporation", "co",
             "capital", "management", "partners", "associates", "asset", "advisors",
             "advisers", "investments", "securities", "the")


def _normalise(name: str) -> str:
    words = re.sub(r"[^a-z0-9 ]", " ", name.lower()).split()
    core = [w for w in words if w not in _SUFFIXES]
    return " ".join(core or words)


def _same_party(a: str, b: str) -> bool:
    """Match on leading whole words.

    Catches "UBS" vs "UBS Global Wealth" and "Goldman Sachs" vs "Goldman", while
    a plain substring test would wrongly pair "Ark" with "Clark".
    """
    if not a or not b:
        return False
    if a == b:
        return True
    wa, wb = a.split(), b.split()
    shorter, longer = (wa, wb) if len(wa) <= len(wb) else (wb, wa)
    return bool(shorter) and longer[:len(shorter)] == shorter


def _cross_reference(views: list[dict]) -> list[dict]:
    """Annotate each view with the other sources quoting the same party."""
    for v in views:
        v["_norm"] = _normalise(v["party"])

    for v in views:
        others = {
            o["source"] for o in views
            if o is not v and _same_party(v["_norm"], o["_norm"])
            and o["source"] != v["source"]
        }
        agreeing = {
            o["stance"] for o in views
            if o is not v and _same_party(v["_norm"], o["_norm"])
        }
        v["also_in"] = sorted(others)
        # More than one distinct stance for the same party is worth flagging.
        v["stance_conflict"] = len(agreeing | {v["stance"]}) > 1

    for v in views:
        v.pop("_norm", None)

    # Parties seen in several sources are the most useful, so surface them first.
    return sorted(views, key=lambda v: (-len(v["also_in"]), not v["is_buyside"], v["party"]))
