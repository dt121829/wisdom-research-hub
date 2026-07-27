import streamlit as st

from services import insights, live_data, llm

STANCE_BADGE = {"Bullish": "🟢", "Bearish": "🔴", "Neutral": "⚪"}


def _gather_articles():
    """Everything the extractor is allowed to read, from the approved sources only."""
    headlines, _ = live_data.get_headlines()
    sa_items, sa_live = live_data.get_sa_analysis(count=10)
    articles = list(headlines)
    if sa_live:
        articles += [
            {"source": "Seeking Alpha", "category": "Analysis", "title": i["title"],
             "summary": f"Independent analysis{(' by ' + i['author']) if i['author'] else ''}.",
             "time": i["time"], "sentiment": "Neutral", "link": i["link"]}
            for i in sa_items
        ]
    return articles


def _render_view(v):
    with st.container(border=True):
        head = st.columns([3, 2])
        badge = "🏦" if v["is_buyside"] else "🏛"
        head[0].markdown(f"{badge} **{v['party']}**  \n<small>{v['party_type']}</small>",
                         unsafe_allow_html=True)
        head[1].markdown(
            f"{STANCE_BADGE[v['stance']]} **{v['stance']}** on {v['topic']}",
        )

        st.write(v["view"])

        if v["also_in"]:
            others = ", ".join(v["also_in"])
            if v["stance_conflict"]:
                st.warning(f"⚡ Cross-source check: also quoted in **{others}** — "
                           "and the stance attributed there differs. Worth reading both.")
            else:
                st.success(f"🔗 Cross-source check: the same party is also quoted in "
                           f"**{others}**, consistently.")

        src = f"{v['source']} · {v['headline']}"
        st.caption(f"[{src}]({v['link']})" if v.get("link") else src)


def render():
    st.title("Buyside Views")
    st.caption(
        "Attributed market views extracted by AI from live coverage across Barron's, WSJ, "
        "CNBC, Seeking Alpha and Yahoo Finance — then cross-checked to see whether the same "
        "party is saying the same thing elsewhere."
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
    col_a.caption(f"Reading {len(articles)} articles · {llm.provider_label()}")
    if col_b.button("↻ Re-extract", help="Clear the cache and analyse the latest articles"):
        insights.buyside_views.clear()
        live_data.get_headlines.clear()
        live_data.get_sa_analysis.clear()
        st.rerun()

    try:
        with st.spinner("Reading the coverage and extracting attributed views…"):
            views = insights.buyside_views(insights._key(articles, "buyside"), articles)
    except Exception as exc:
        st.error(f"Extraction failed: {exc}")
        return

    if not views:
        st.info("No attributed views found in the current batch of articles. "
                "Coverage today may be purely factual reporting — try again after the next refresh.")
        return

    # ------------------------------------------------------------- filters
    f1, f2, f3 = st.columns(3)
    only_buyside = f1.toggle("Buyside only", value=True,
                             help="Asset managers and hedge funds only, excluding banks, "
                                  "analysts, executives and policymakers")
    stance = f2.selectbox("Stance", ["All", "Bullish", "Bearish", "Neutral"])
    cross_only = f3.toggle("Multi-source only", value=False,
                           help="Show only parties quoted in more than one source")

    shown = [
        v for v in views
        if (not only_buyside or v["is_buyside"])
        and (stance == "All" or v["stance"] == stance)
        and (not cross_only or v["also_in"])
    ]

    multi = sum(1 for v in views if v["also_in"])
    st.write(f"**{len(shown)}** of {len(views)} extracted views · "
             f"{multi} appear in more than one source")

    if not shown:
        st.caption("Nothing matches these filters. Try turning off 'Buyside only' — "
                   "today's coverage may be dominated by banks and analysts.")

    for v in shown:
        _render_view(v)

    st.divider()

    # ------------------------------------------------ consensus / divergence
    st.subheader("Where the sources agree and disagree")
    bulls = [v for v in views if v["stance"] == "Bullish"]
    bears = [v for v in views if v["stance"] == "Bearish"]
    conflicts = [v for v in views if v["stance_conflict"]]

    m1, m2, m3 = st.columns(3)
    m1.metric("Bullish views", len(bulls))
    m2.metric("Bearish views", len(bears))
    m3.metric("Parties with conflicting quotes", len({v["party"] for v in conflicts}))

    if conflicts:
        st.markdown("**⚡ Parties quoted differently in different sources**")
        for party in sorted({v["party"] for v in conflicts}):
            entries = [v for v in views if v["party"] == party]
            detail = " · ".join(f"{e['source']}: {e['stance']}" for e in entries)
            st.markdown(f"- **{party}** — {detail}")
    else:
        st.caption("No contradictions detected between sources in the current batch.")
