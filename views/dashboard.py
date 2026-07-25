from datetime import datetime

import plotly.graph_objects as go
import streamlit as st

from data import sample_data as d
from services import ai, charts, live_data

SENTIMENT_BADGE = {"Positive": "🟢", "Negative": "🔴", "Neutral": "⚪"}


def render():
    st.title("Market Dashboard")

    indices, sectors, quotes_live = live_data.get_market_data()
    trend_dates, trend_values, trend_live = live_data.get_sp500_trend()
    headlines, news_live = live_data.get_headlines()

    if quotes_live or news_live:
        status = f"🟢 Live data · quotes via Yahoo Finance, headlines via source RSS · refreshed {datetime.now():%H:%M}"
    else:
        status = f"⚪ Offline — showing bundled sample data (as of {d.AS_OF.strftime('%B %d, %Y')})"
    st.caption(f"Barron's · WSJ · CNBC · Seeking Alpha · Bloomberg Terminal — {status}")

    # ------------------------------------------------------------- indices
    cols = st.columns(len(indices))
    for col, idx in zip(cols, indices):
        col.metric(idx["name"], idx["value"], idx["change"])

    st.divider()

    # ---------------------------------------------------- AI market outlook
    st.subheader("AI Market Outlook")
    if ai.live_mode():
        if st.button("Generate today's outlook", type="primary"):
            prompt = [{
                "role": "user",
                "content": "Write a concise market outlook paragraph (150-200 words) synthesising "
                           "today's headlines and buyside views from the context. Lead with the "
                           "overall tone, then the single most important cross-source divergence.",
            }]
            st.write_stream(ai.stream_completion(prompt, max_tokens=2000))
        else:
            st.info("Live AI connected — click to generate a fresh synthesis of today's ingested content.")
    else:
        st.markdown(d.DEMO_OUTLOOK)

    st.divider()

    # ------------------------------------------------------------- charts
    left, right = st.columns(2)

    with left:
        st.subheader("S&P 500 — last 10 sessions")
        if not trend_live:
            st.caption("⚪ sample data")
        fig = go.Figure(go.Scatter(
            x=trend_dates, y=trend_values,
            mode="lines+markers",
            line=dict(color=charts.SERIES_1, width=2),
            marker=dict(size=6, color=charts.SERIES_1),
            hovertemplate="%{x}<br>%{y:,.0f}<extra></extra>",
        ))
        charts.base_layout(fig)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    with right:
        st.subheader("Sector performance — 1 day")
        if not quotes_live:
            st.caption("⚪ sample data")
        s_sorted = sorted(sectors, key=lambda s: s["change"])
        fig = go.Figure(go.Bar(
            x=[s["change"] for s in s_sorted],
            y=[s["name"] for s in s_sorted],
            orientation="h",
            marker=dict(
                color=[charts.POS if s["change"] >= 0 else charts.NEG for s in s_sorted],
                line=dict(width=0),
            ),
            hovertemplate="%{y}: %{x:+.1f}%<extra></extra>",
        ))
        charts.base_layout(fig, height=360)
        fig.update_xaxes(ticksuffix="%")
        fig.update_layout(bargap=0.35)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    st.divider()

    # ----------------------------------------------------------- headlines
    head_l, head_r = st.columns([4, 1])
    head_l.subheader("Latest across sources")
    if head_r.button("↻ Refresh", help="Clear the cache and re-pull all feeds"):
        live_data.get_headlines.clear()
        live_data.get_market_data.clear()
        live_data.get_sp500_trend.clear()
        st.rerun()

    src_filter = st.multiselect(
        "Filter by source",
        options=sorted({h["source"] for h in headlines}),
        placeholder="All sources",
    )
    for h in headlines:
        if src_filter and h["source"] not in src_filter:
            continue
        with st.container(border=True):
            top = st.columns([5, 1])
            title = f"[{h['title']}]({h['link']})" if h.get("link") else f"**{h['title']}**"
            top[0].markdown(title)
            top[1].caption(f"{SENTIMENT_BADGE[h['sentiment']]} {h['sentiment']}")
            st.caption(f"{h['source']} · {h['category']} · {h['time']}")
            if h["summary"]:
                st.write(h["summary"])
