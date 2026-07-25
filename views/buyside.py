import streamlit as st

from data import sample_data as d
from services import live_data

STANCE_COLOR = {"Bullish": "🟢", "Bearish": "🔴", "Neutral": "⚪"}


def render():
    st.title("Buyside Views")
    st.caption(
        "Perspectives from asset managers and hedge funds — the coverage gap this platform was "
        "built to close. Sourced from fund letters and 13F data on the Bloomberg Terminal, plus "
        "buyside contributors on Seeking Alpha."
    )

    # ------------------------------------------------------------- filters
    f1, f2, f3 = st.columns(3)
    stance = f1.selectbox("Stance", ["All", "Bullish", "Bearish", "Neutral"])
    firm_type = f2.selectbox("Firm type", ["All", "Asset Manager", "Hedge Fund"])
    topics = ["All"] + sorted({v["topic"] for v in d.BUYSIDE_VIEWS})
    topic = f3.selectbox("Topic", topics)

    views = [
        v for v in d.BUYSIDE_VIEWS
        if (stance == "All" or v["stance"] == stance)
        and (firm_type == "All" or v["firm_type"] == firm_type)
        and (topic == "All" or v["topic"] == topic)
    ]

    st.write(f"**{len(views)}** view(s) · ⚪ curated sample entries — live sourcing arrives with "
             "the Bloomberg Terminal integration (fund letters, 13F filings)")
    for v in views:
        with st.container(border=True):
            head = st.columns([4, 2])
            head[0].markdown(f"**{v['firm']}**  \n{v['firm_type']} · {v['channel']}")
            head[1].markdown(
                f"{STANCE_COLOR[v['stance']]} **{v['stance']}** on {v['topic']}  \n"
                f"Conviction: {v['conviction']} · {v['date']}"
            )
            st.write(v["view"])

    st.divider()

    # -------------------------------------- live buyside-adjacent analysis
    st.subheader("Latest independent analysis — Seeking Alpha")
    sa_items, sa_live = live_data.get_sa_analysis()
    if sa_live:
        st.caption("🟢 Live feed — long-form theses from independent and buyside-adjacent analysts")
        for item in sa_items:
            author = f" · {item['author']}" if item["author"] else ""
            st.markdown(f"- [{item['title']}]({item['link']})  \n  <small>{item['time']}{author}</small>",
                        unsafe_allow_html=True)
    else:
        st.caption("⚪ Feed unreachable right now — check back later.")

    st.divider()

    # ------------------------------------------- consensus vs. divergence
    st.subheader("Consensus vs. divergence")
    st.caption(
        "Cross-source synthesis: where the street agrees, where credible voices push back, "
        "and what would settle the argument."
    )
    for c in d.CONSENSUS:
        with st.expander(f"**{c['theme']}**", expanded=True):
            a, b = st.columns(2)
            a.markdown(f"**🤝 Consensus**\n\n{c['consensus']}")
            b.markdown(f"**⚡ Divergence**\n\n{c['divergence']}")
            st.markdown(f"**👁 What to watch:** {c['watch']}")
