"""AI analysis over the selected sources.

Products, all cached so a rerun never re-bills the model:
  market_outlook()    – dashboard synthesis (topic bullets + coming events)
  buyside_pipeline()  – reads full articles for investor quotes, chases the same
                        topics through the rest of the coverage, then compares the
                        views against market data

Everything here reads from services.live_data, which is restricted to the selected
sources (Seeking Alpha, Yahoo Finance, CNBC, SumZero). The outlook may supplement
from wider knowledge for well-known scheduled events, and labels every such point.
The buyside pipeline never does: every quote it shows is verbatim from an article
it actually opened.
"""

import hashlib
import re
from datetime import datetime

import streamlit as st

from services import llm

EXTERNAL_TAG = "⚠️ *external — not from selected sources*"

SOURCE_RULE = (
    "The firm's selected sources are Seeking Alpha, Yahoo Finance, Yahoo 奇摩股市 "
    "(Taiwan), CNBC, SumZero and WhaleWisdom. "
    "Ground your work in the article material supplied in the prompt, which comes from "
    "these sources, and attribute claims to their source. Only when the supplied material "
    "is missing information the task genuinely needs may you draw on wider knowledge — and "
    f"every such point MUST end with the exact label: {EXTERNAL_TAG} . "
    "Never present outside material as if it came from the selected sources."
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
    """Number the articles so the model can cite one precisely."""
    return "\n".join(
        f"[{n}] {i['source']} — {i['title']} — {i.get('summary', '')}"
        for n, i in enumerate(items, 1)
    )


# ------------------------------------------------------------ market outlook

@st.cache_data(ttl=1800, show_spinner=False)
def market_outlook(cache_key: str, _articles: list, _snapshot: str,
                   _calendar: str = "") -> dict:
    """Return {'summary': markdown, 'sources': [article, ...]}."""
    today = datetime.now().strftime("%A, %B %d, %Y")
    calendar_block = (f"\nSCHEDULED EVENTS — verified calendar data (Federal Reserve "
                      f"for FOMC, Yahoo Finance for earnings):\n{_calendar}\n"
                      if _calendar else "")
    prompt = f"""Today is {today}.

Today's market snapshot:
{_snapshot}

NUMBERED SOURCE ARTICLES from the selected sources — cite these by their number:
{_format_articles(_articles)}
{calendar_block}

Write a market outlook for investment staff as concise bullet points grouped under
bold topic headings. Use exactly this structure (skip a topic only if there is truly
nothing to say about it; add one extra topic if the coverage demands it):

**Macro**
**US Market**
**Taiwan Market**
**Asia Market**
**Rest of the World**

Geography rules — put each story where it actually belongs:
- **Taiwan Market** is for Taiwan only: TAIEX, TSMC, Taiwanese companies, NT dollar,
  Taiwan policy. A story about Korea, Japan or China belongs in **Asia Market**, even
  when it moves Taiwanese stocks. If a foreign story matters *because of* its read-across
  to Taiwan, you may mention it in Taiwan Market only by stating that read-across
  explicitly — otherwise leave it in Asia.
- **Asia Market** covers Korea (SK Hynix, Samsung, Kospi), Japan, China, Hong Kong,
  India and South-East Asia.
- **Rest of the World** covers Europe, the UK, Latin America, the Middle East, Africa,
  Canada and Australia.
- **Macro** is for cross-border themes: rates, inflation, currencies, oil, trade policy.

- 1-3 bullets per topic, each a single tight sentence.
- CITE BY NUMBER: end each bullet with the source name and the article's number,
  e.g. [CNBC 4] or [Seeking Alpha 11]. The number must be the article the claim came
  from — it becomes a clickable link straight to that article. Where sources disagree,
  say so in the bullet and cite both.
- Keep the whole outlook under 220 words.

Then add a final section:

**📅 Major events — next 5 days**
- 8-14 dated bullets, format "Wed Jul 30 — event — why it matters (a few words)".
- Group them day by day in date order, starting with today.
- Cover ALL of: central bank decisions and speeches (FOMC, ECB, BoJ, PBoC), the
  scheduled macro releases (CPI, PCE, payrolls, GDP, PMI, jobless claims,
  confidence), major earnings, and any scheduled political or policy event the
  articles flag (tariff deadlines, summits, OPEC meetings, elections).
- The SCHEDULED EVENTS block above is verified calendar data pulled from the Federal
  Reserve and Yahoo Finance. Every item in it that falls in the next five days MUST
  appear in your list, using its exact date. Anything marked FOMC goes FIRST on its
  day — a rate decision outranks everything else on the calendar.
- Do NOT write "(confirmed)", "(confirmed earnings)" or similar tags. Anything in the
  block is confirmed by definition; only items you add yourself are uncertain, and
  those carry the external label instead.
- Do NOT list an earnings date that is not in the block above. If a company's date is
  not there, leave it out rather than guessing it.
- The block already contains the US macro releases whose dates follow a fixed rule
  (jobless claims, payrolls, ISM, PCE). Use them as given and do NOT label them
  external — they are calculated, not recalled.
- You may add a further event only if you know its ACTUAL date. Give that date and
  the external label. If you are unsure of the date, leave the event out entirely —
  never write "date TBC", "this week", or an event with no specific day.
- For events the articles mention, cite the article number.
- Name companies in full with their ticker: "Visa (V) reports earnings".
- Do not name the Fed chair or any other office-holder; give the event, not the person.
- NEVER write a note about what the articles do or do not cover. No meta-commentary
  about the source material — just give the calendar."""

    from services import reports  # local import: avoids a circular import at load

    # Reasoning tokens come out of the same budget as the answer, so this needs
    # headroom: too small and the model reasons until nothing is left to say.
    summary = llm.complete(prompt, ANALYST_SYSTEM, max_tokens=16000,
                           reasoning_effort="low")
    summary = reports.link_citations(summary, _articles)
    return {"summary": summary, "sources": _articles}


# -------------------------------------------------------------- buyside views

PARTY_TYPES = ["Asset Manager", "Hedge Fund", "Platform Contributor",
               "Bank / Broker", "Sell-side Analyst", "Media Commentator",
               "Company Executive", "Policymaker", "Other"]

# What the desk means by "buyside": people who actually run outside capital, plus
# the independent research platforms the firm subscribes to. A broker, a bank
# analyst and a TV commentator are all sell-side or media, however good the call.
BUYSIDE_TYPES = {"Asset Manager", "Hedge Fund", "Platform Contributor"}

BUYSIDE_DEFINITION = """A view counts as BUYSIDE only when the speaker is one of:
  - an asset management firm (mutual funds, pensions, endowments, family offices,
    sovereign funds, long-only and multi-asset managers) → "Asset Manager"
  - a hedge fund or other private investment fund running outside capital
    (including private equity and credit funds) → "Hedge Fund"
  - a contributor or aggregated dataset on the firm's selected research platforms,
    i.e. Seeking Alpha contributors, SumZero members, WhaleWisdom 13F position
    data → "Platform Contributor"

These are explicitly NOT buyside, no matter how prominent the speaker:
  - television and media personalities, network hosts and columnists (for example
    a CNBC host or a newspaper columnist) → "Media Commentator"
  - retail brokerages and trading platforms and their in-house market analysts
    (for example eToro, Robinhood, IG, Interactive Brokers) → "Bank / Broker"
  - investment-bank and broker research analysts (Goldman, Jefferies, UBS,
    Standard Chartered and the like) → "Bank / Broker" for the firm, or
    "Sell-side Analyst" for a named covering analyst
  - company executives talking about their own business → "Company Executive"
  - central bankers, ministers and regulators → "Policymaker"

Classify by WHO EMPLOYS the speaker and whether that employer invests outside
capital — not by how the comment sounds."""

QUOTE_SYSTEM = (
    "You read financial news articles and pull out what named investors actually said. "
    "Work ONLY from the article text supplied. Every quote you return must appear in "
    "that text — copy it verbatim, never paraphrase into quotation marks and never "
    "invent a speaker. If an article contains no investor comment, return nothing for "
    "it. Be strict about who counts as buyside: classify by the speaker's employer, "
    "not by how authoritative they sound. Precision matters far more than volume."
)

COMPARE_SYSTEM = (
    "You are the research analyst of Wisdom Family Office, comparing what named "
    "institutional investors are saying. Work only from the quotes and market data "
    "supplied — every claim must trace to one of them. Never invent a speaker, a quote "
    "or a figure. Write in clean Markdown and escape literal dollar signs as \\$."
)


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + "…"


# Firms the model has repeatedly mislabelled as buyside. Retail brokers and news
# networks employ people who sound like investors but do not run outside capital,
# so the classification is corrected deterministically rather than left to a prompt.
_NOT_BUYSIDE_FIRMS = {
    "etoro": "Bank / Broker", "robinhood": "Bank / Broker", "ig group": "Bank / Broker",
    "interactive brokers": "Bank / Broker", "charles schwab": "Bank / Broker",
    "webull": "Bank / Broker", "plus500": "Bank / Broker", "saxo": "Bank / Broker",
    "cnbc": "Media Commentator", "bloomberg": "Media Commentator",
    "fox business": "Media Commentator", "yahoo finance": "Media Commentator",
    "the street": "Media Commentator", "thestreet": "Media Commentator",
    "marketwatch": "Media Commentator", "barron": "Media Commentator",
    "mad money": "Media Commentator", "wall street journal": "Media Commentator",
}

# People who front market programmes rather than manage money.
_MEDIA_PEOPLE = ("jim cramer", "cramer")


def _correct_party_type(person: str, firm: str, party_type: str) -> str:
    """Override the model where a firm or person is plainly not buyside."""
    haystack = f"{firm} {person}".lower()
    for needle, corrected in _NOT_BUYSIDE_FIRMS.items():
        if needle in haystack:
            return corrected
    if any(name in person.lower() for name in _MEDIA_PEOPLE):
        return "Media Commentator"
    return party_type


# ---------------------------------------------------- stage 1: find the quotes

def find_quotes(_articles: list[dict], _texts: dict[str, str]) -> list[dict]:
    """Read full article bodies and pull out verbatim quotes from investors."""
    blocks, indexed = [], []
    for a in _articles:
        text = _texts.get(a.get("link", ""))
        if not text:
            continue
        indexed.append(a)
        blocks.append(f"### ARTICLE {len(indexed)} — [{a['source']}] {a['title']}\n"
                      f"{_clip(text, 5000)}")
    if not blocks:
        return []

    prompt = f"""Below are full article texts from the firm's selected sources.

{chr(10).join(blocks)}

For every article, find comments attributed to a NAMED person that express a view on
MARKETS, INVESTMENTS OR THE ECONOMY — what to own, what something is worth, where
prices, rates, demand or policy are heading, or how to position.

Priority order: buyside voices first, then bank/broker strategists and analysts, then
company executives and policymakers commenting on market or economic conditions.

{BUYSIDE_DEFINITION}

Rules:
- "quote" MUST be text copied verbatim from the article. Do not paraphrase.
- Give the person's name and their firm exactly as the article states them.
- ALWAYS fill "role" with the person's job title as the article gives it — "chief
  investment officer", "portfolio manager", "head of equity strategy", "CEO". The desk
  needs to know their seniority to weigh the view. Only leave it empty when the article
  genuinely gives no title.
- EXCLUDE comments that are not market views: litigation and legal statements,
  product launches, HR or personnel announcements, corporate mission statements,
  and general commentary with no investment implication.
- If the article contains no such comment, skip that article entirely.

Return JSON:
{{"quotes": [
  {{"article": <the ARTICLE number the quote came from>,
    "person": "full name as written",
    "firm": "their firm as written",
    "role": "their role if the article states one, else ''",
    "party_type": one of {PARTY_TYPES},
    "topic": "what the comment is about, a few words",
    "stance": "Bullish" or "Bearish" or "Neutral",
    "quote": "the verbatim sentence(s) they are quoted saying"}}
]}}"""

    data = llm.complete_json(prompt, QUOTE_SYSTEM, max_tokens=14000,
                             reasoning_effort="low")
    raw = data.get("quotes", []) if isinstance(data, dict) else (data or [])

    out = []
    for q in raw:
        if not isinstance(q, dict) or not q.get("person") or not q.get("quote"):
            continue
        try:
            article = indexed[int(q.get("article", 0)) - 1]
        except (ValueError, TypeError, IndexError):
            continue
        # Guard against paraphrase: the quote must really be in the article text.
        body = _texts.get(article.get("link", ""), "")
        probe = re.sub(r"\W+", " ", str(q["quote"])[:60]).strip().lower()
        haystack = re.sub(r"\W+", " ", body).lower()
        if probe and probe not in haystack:
            continue
        q["firm"] = str(q.get("firm") or "").strip()
        q["person"] = str(q["person"]).strip()
        q["role"] = str(q.get("role") or "").strip()
        q["party_type"] = q.get("party_type") if q.get("party_type") in PARTY_TYPES else "Other"
        q["party_type"] = _correct_party_type(q["person"], q["firm"], q["party_type"])
        q["stance"] = q.get("stance") if q.get("stance") in ("Bullish", "Bearish", "Neutral") else "Neutral"
        q["is_buyside"] = q["party_type"] in BUYSIDE_TYPES
        q["source"] = article["source"]
        q["headline"] = article["title"]
        q["link"] = article.get("link", "")
        out.append(q)
    return out


# --------------------------------------------- stage 3: compare the viewpoints

def compare_views(_quotes: list[dict], _market_note: str, topic: str = "") -> str:
    """Group the collected quotes into a compared, evidence-backed narrative."""
    if not _quotes:
        return ""
    focus = (f"\nThe desk is specifically asking about: **{topic}**. Lead with the "
             "topics that bear on that question, and say plainly if the coverage "
             "carries little on it.\n" if topic else "")
    lines = []
    for n, q in enumerate(_quotes, 1):
        who = f"{q['person']} ({q['role']}, {q['firm']})" if q["role"] else \
              f"{q['person']} ({q['firm']})"
        lines.append(f"[{n}] {who} — {q['party_type']} — on {q['topic']} — "
                     f"{q['stance']} — \"{q['quote']}\" — source: {q['source']}, "
                     f"headline: {q['headline']}")

    prompt = f"""Quotes gathered from the firm's selected sources:
{chr(10).join(lines)}

Supporting market data (Yahoo Finance, as of now):
{_market_note}
{focus}
Write a comparison of what these investors are saying, for investment staff.
BULLET POINTS ONLY — no paragraphs anywhere.

For each topic where two or more people commented, use exactly this shape:

### <Topic name>
- **<Person>** (<Role>, <Firm>) — *<Stance>*: their view in one short line [n]
- **<Person>** (<Role>, <Firm>) — *<Stance>*: their view in one short line [n]
  (give the role wherever the quote list supplies one; drop it only when it is empty)
- **⚔️ The split:** one line naming what precisely they disagree about
- **📊 Market check:** one line using the market data above to say which side the
  price action currently favours

Then finish with:

### Where they agree
- one line per point of agreement, naming the people [n]

### Where they disagree
- one line per disagreement, naming the people on each side [n]

Rules:
- Every bullet is ONE line. Never write a paragraph.
- Cite with the quote number in brackets, e.g. [3], on every bullet reporting a view.
- Use ONLY the quotes and market data above. Do not add outside facts or figures.
- Order topics with the most buyside participation first.
- If a topic has only one speaker, put it in a final "### Single voices" section as
  one bullet each — do not invent an opposing view.
- Under 400 words total."""

    return llm.complete(prompt, COMPARE_SYSTEM, max_tokens=12000,
                        reasoning_effort="low")


@st.cache_data(ttl=86400, show_spinner=False)
def url_is_live(url: str) -> bool:
    """True when the URL actually resolves — used to reject invented citations.

    A model asked to recall where a view was published will sometimes produce a
    plausible-looking URL that does not exist, so every external citation is
    checked against the real web before the desk is shown it.
    """
    if not url or not url.lower().startswith(("http://", "https://")):
        return False
    import requests

    from services.live_data import UA

    # HEAD is cheap but widely mishandled — some hosts refuse it, others answer
    # with a redirect loop — so any HEAD problem falls through to a real GET.
    try:
        r = requests.head(url, headers=UA, timeout=6, allow_redirects=True)
        if r.status_code < 400:
            return True
    except Exception:
        pass
    try:
        r = requests.get(url, headers=UA, timeout=10, allow_redirects=True, stream=True)
        r.close()
        return r.status_code < 400
    except Exception:
        return False


@st.cache_data(ttl=1800, show_spinner=False)
def buyside_pipeline(cache_key: str, _articles: list, _market_note: str,
                     scan_count: int = 14, follow_count: int = 10,
                     topic: str = "") -> dict:
    """Read articles → find investor quotes → chase more on the same topics → compare.

    When `topic` is given, coverage matching it is pulled in and read first, and the
    comparison is framed around that question.

    Returns {"quotes": [...], "comparison": markdown, "scanned": n, "followed": n}.
    """
    from services import live_data

    pool = list(_articles)
    if topic:
        # Put anything already pulled that mentions the topic at the front, then
        # go and fetch more coverage on it from the per-security feeds.
        matches = live_data.articles_mentioning(topic, pool)
        extra = live_data.search_news(topic, limit=20)
        known = {a.get("link") for a in matches}
        matches += [a for a in extra if a.get("link") and a["link"] not in known]
        rest = [a for a in pool if a not in matches]
        pool = matches + rest

    # Stage 1 — read the most recent articles in full and pull out real quotes.
    first = [a for a in pool if a.get("link")][:scan_count]
    _articles = pool
    texts = live_data.fetch_many_texts([a["link"] for a in first])
    quotes = find_quotes(first, texts)

    # Stage 2 — for each investor and topic found, look through the rest of the
    # corpus for more voices on the same subject, then read those in full too.
    # Buyside firms and the topics they raised are chased first: more buyside
    # perspective on the same question is the point of the page.
    seen_links = {a["link"] for a in first}
    rest = [a for a in _articles if a.get("link") and a["link"] not in seen_links]
    buyside_terms, other_terms = [], []
    for q in quotes:
        bucket = buyside_terms if q["is_buyside"] else other_terms
        if q["firm"]:
            bucket.append(q["firm"])
        bucket.append(q["topic"])
    terms = list(dict.fromkeys(buyside_terms + other_terms))

    follow: list[dict] = []
    for term in terms[:14]:
        for hit in live_data.articles_mentioning(term, rest):
            if hit["link"] not in seen_links:
                seen_links.add(hit["link"])
                follow.append(hit)
    # Top up with the freshest unread coverage so a narrow first pass still widens.
    for a in rest:
        if len(follow) >= follow_count:
            break
        if a["link"] not in seen_links:
            seen_links.add(a["link"])
            follow.append(a)
    follow = follow[:follow_count]

    if follow:
        more_texts = live_data.fetch_many_texts([a["link"] for a in follow])
        quotes += find_quotes(follow, more_texts)

    # De-duplicate: the same person saying the same thing in two outlets.
    unique, keys = [], set()
    for q in quotes:
        key = (q["person"].lower(), q["quote"][:80].lower())
        if key not in keys:
            keys.add(key)
            unique.append(q)

    # Buyside voices first — that is what the page is for.
    unique.sort(key=lambda q: (not q["is_buyside"], q["person"]))

    comparison = compare_views(unique, _market_note, topic) if unique else ""
    if comparison:
        # Turn the [3] quote markers into links to the article each came from.
        def _num_link(match):
            idx = int(match.group(1))
            if 1 <= idx <= len(unique) and unique[idx - 1]["link"]:
                return f"[[{idx}]]({unique[idx - 1]['link']})"
            return match.group(0)

        comparison = re.sub(r"\[(\d{1,2})\]", _num_link, comparison)

    return {"quotes": unique, "comparison": comparison,
            "scanned": len(first), "followed": len(follow)}
