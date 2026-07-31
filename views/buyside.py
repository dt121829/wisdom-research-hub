import streamlit as st

from services import insights, live_data, llm

STANCE_BADGE = {"Bullish": "🟢", "Bearish": "🔴", "Neutral": "⚪"}


def _gather_articles():
    """Everything the reader is allowed to open, from the selected sources only."""
    headlines, _ = live_data.get_headlines()
    sa_items, sa_live = live_data.get_sa_analysis(count=12)
    articles = list(headlines)
    if sa_live:
        known = {a.get("link") for a in articles}
        articles += [
            {"source": "Seeking Alpha", "category": "Analysis", "title": i["title"],
             "summary": f"Independent analysis{(' by ' + i['author']) if i['author'] else ''}.",
             "time": i["time"], "sentiment": "Neutral", "link": i["link"]}
            for i in sa_items if i["link"] not in known
        ]
    return articles


def _market_note():
    """Price context the comparison stage uses to test the claims against the tape."""
    indices, sectors, _live = live_data.get_market_data()
    top = sorted(sectors, key=lambda s: -s["change"])[:4]
    bottom = sorted(sectors, key=lambda s: s["change"])[:4]
    return (
        "Indices today: "
        + "; ".join(f"{i['name']} {i['value']} ({i['change']})" for i in indices)
        + ". Best sectors today: "
        + ", ".join(f"{s['name']} {s['change']:+.1f}%" for s in top)
        + ". Worst sectors today: "
        + ", ".join(f"{s['name']} {s['change']:+.1f}%" for s in bottom)
    )


def _render_quote(n, q):
    with st.container(border=True):
        head = st.columns([3, 2])
        badge = "🏦" if q["is_buyside"] else "🏛"
        who = f"**{q['person']}**"
        if q.get("role"):
            who += f"  \n<small>{q['role']}, {q['firm']}</small>"
        elif q.get("firm"):
            who += f"  \n<small>{q['firm']}</small>"
        head[0].markdown(f"{badge} {who}", unsafe_allow_html=True)
        head[1].markdown(f"{STANCE_BADGE[q['stance']]} **{q['stance']}** on {q['topic']}")

        st.markdown(f"> {q['quote']}")

        src = f"[{n}] {q['source']} · {q['headline']}"
        st.caption(f"[{src}]({q['link']})" if q.get("link") else src)


def render():
    st.title("Buyside Views")
    st.caption(
        "Reads the full text of live articles across the selected sources, pulls out what "
        "named investors actually said, searches the rest of the coverage for more voices "
        "on the same topics, and compares them against the day's market data. Every quote "
        "is verbatim and links to the article it came from."
    )
    st.caption(
        "🏦 **Buyside** here means asset management firms, hedge funds, and contributors "
        "on the firm's research platforms (Seeking Alpha, SumZero, WhaleWisdom) — and the "
        "comparison below is built from those voices only. Bank and broker analysts, "
        "retail trading platforms such as eToro, and media commentators such as network "
        "hosts are captured for context but shown separately under 🏛 *Other market "
        "voices*, never in the buyside comparison."
    )

    if not llm.live():
        st.info(
            "**Copilot not connected.** This page reads live articles and extracts who is "
            "saying what, so it needs an AI provider. Add your Azure OpenAI details in the "
            "sidebar to switch it on."
        )
        return

    articles = _gather_articles()
    if not articles:
        st.warning("No articles available from the sources right now. Try again shortly.")
        return

    col_a, col_b = st.columns([4, 1])
    col_a.caption(f"{len(articles)} articles available · {llm.provider_label()}")
    if col_b.button("↻ Re-read", help="Re-pull the feeds and read the latest articles again"):
        insights.buyside_pipeline.clear()
        live_data.get_headlines.clear()
        live_data.get_sa_analysis.clear()
        live_data.fetch_article_text.clear()
        st.rerun()

    s_col, d_col = st.columns([2, 3])
    topic = s_col.text_input(
        "Search a topic, company or investor",
        placeholder="e.g. TSMC, memory prices, Fed policy",
        help="Pulls additional coverage on this subject from the selected sources, "
             "reads it, and frames the comparison around it.",
    ).strip()
    depth = d_col.select_slider(
        "How much coverage to read",
        options=["Quick (14 articles)", "Standard (24)", "Deep (40)"],
        value="Standard (24)",
        help="Each article is opened and read in full, so deeper takes longer.",
    )
    scan, follow = {"Quick (14 articles)": (10, 4),
                    "Standard (24)": (14, 10),
                    "Deep (40)": (24, 16)}[depth]

    if topic:
        st.caption(f"🔎 Searching the selected sources for coverage of **{topic}** and "
                   "reading what it finds.")

    try:
        spinner = (f"Searching for “{topic}” and reading up to {scan + follow} articles…"
                   if topic else
                   f"Reading up to {scan + follow} articles in full and comparing views…")
        with st.spinner(spinner):
            result = insights.buyside_pipeline(
                insights._key(articles, "pipeline", depth, topic), articles,
                _market_note(), scan_count=scan, follow_count=follow, topic=topic,
            )
    except Exception as exc:
        st.error(f"Extraction failed: {exc}")
        return

    quotes = result["quotes"]
    if not quotes:
        if topic:
            st.info(f"No investor comments on **{topic}** in the coverage available. "
                    "Try a broader term, a ticker, or 'Deep' to read more articles.")
        else:
            st.info("No investor comments found in the articles read this time. Today's "
                    "coverage may be purely factual — try 'Deep' or hit ↻ Re-read.")
        return

    scope = result.get("comparison_scope", "buyside")
    other = result.get("other", [])
    st.caption(f"Read {result['scanned']} articles, then followed up on "
               f"{result['followed']} more · {result.get('buyside_count', 0)} buyside "
               f"voice(s), {result.get('other_count', 0)} other market voice(s)")

    # ------------------------------------------------------- the comparison
    if result["comparison"]:
        if scope == "buyside":
            st.subheader("How buyside views compare")
        else:
            st.subheader("How the views compare")
            st.info(f"Only {result.get('buyside_count', 0)} buyside voice(s) surfaced in "
                    "today's coverage — too few to compare on their own, so this compares "
                    "all attributed market voices. Try **Deep**, or search a specific "
                    "topic, to surface more buyside commentary.")
        st.markdown(result["comparison"])
        st.caption("Numbers in brackets link to the article each quote came from. "
                   "Market data: Yahoo Finance.")
        st.divider()

    # ------------------------------------------------------------ the quotes
    # `quotes` is the compared set: buyside-only in the normal case. The stance
    # filter narrows within it; non-buyside voices live in their own section below.
    st.subheader("What buyside investors said" if scope == "buyside"
                 else "What each investor said")
    stance = st.selectbox("Stance", ["All", "Bullish", "Bearish", "Neutral"])
    shown = [(n, q) for n, q in enumerate(quotes, 1)
             if stance == "All" or q["stance"] == stance]
    st.write(f"**{len(shown)}** of {len(quotes)} shown")
    for n, q in shown:
        _render_quote(n, q)

    # ------------------------------- non-buyside context (kept out of the headline)
    if scope == "buyside" and other:
        st.divider()
        with st.expander(f"🏛 Other market voices — NOT buyside ({len(other)}): banks, "
                         "brokers, media, executives, policymakers", expanded=False):
            st.caption("Shown for context only. By the firm's definition these are not "
                       "buyside, so they are excluded from the comparison above.")
            for n, q in enumerate(other, len(quotes) + 1):
                _render_quote(n, q)

    # ----------------------------------------------------- cited sources
    st.divider()
    st.subheader("Cited sources")
    seen = set()
    for q in quotes + other:
        key = (q["source"], q["headline"])
        if key in seen:
            continue
        seen.add(key)
        line = f"**{q['source']}** · {q['headline']}"
        st.markdown(f"- [{line}]({q['link']})" if q.get("link") else f"- {line}")
    st.caption("Every quote above is verbatim from one of these articles. Nothing on this "
               "page is recalled from the model's own memory.")
