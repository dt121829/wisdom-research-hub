from datetime import datetime

import plotly.graph_objects as go
import streamlit as st

from data import sample_data as d
from services import charts, insights, live_data, llm

SENTIMENT_BADGE = {"Positive": "🟢", "Negative": "🔴", "Neutral": "⚪", "Mixed": "🟡"}

INDEX_CHOICES = {name: sym for name, sym, _ in live_data.INDEX_SYMBOLS}
INDEX_KIND = {name: kind for name, _, kind in live_data.INDEX_SYMBOLS}


_METRIC_CSS = """
<style>
/* Keep Streamlit's native metric styling, and lay a transparent button over the
   whole tile so clicking the value (or anywhere on it) toggles the change unit. */
div[class*="st-key-tile-"] { position: relative; }
/* Streamlit gives the button its own element container keyed on the button's key,
   so that is the element to stretch over the tile — not the inner stButton div. */
div[class*="st-key-tile_btn_"] {
    position: absolute !important; inset: 0 !important;
    /* Streamlit sets an explicit width on the element container, which beats
       left/right — so the fill has to be stated outright. */
    width: 100% !important; height: 100% !important;
    margin: 0 !important; padding: 0 !important; z-index: 2;
}
div[class*="st-key-tile_btn_"] div[data-testid="stButton"],
div[class*="st-key-tile_btn_"] div[data-testid="stButton"] > div {
    height: 100% !important; width: 100% !important; margin: 0 !important;
}
div[class*="st-key-tile_btn_"] button {
    width: 100% !important; height: 100% !important;
    opacity: 0; padding: 0 !important; margin: 0 !important;
    border: none !important; background: transparent !important; cursor: pointer;
}
div[class*="st-key-tile-"]:hover div[data-testid="stMetric"] {
    background: rgba(42,120,214,0.06); border-radius: 6px;
}
</style>
"""


def _metric_row(indices):
    """Native index tiles that are clickable: any tile flips % ⇄ points."""
    st.markdown(_METRIC_CSS, unsafe_allow_html=True)
    alt = st.session_state.get("metric_mode_alt", False)

    cols = st.columns(len(indices))
    for n, (col, idx) in enumerate(zip(cols, indices)):
        shown = idx.get("change_alt") if alt and idx.get("change_alt") else idx["change"]
        with col:
            with st.container(key=f"tile-{n}"):
                st.metric(idx["name"], idx["value"], shown)
                # No help text: the tooltip icon would sit inside the overlay and
                # steal the click. The caption below the row explains the toggle.
                if st.button(" ", key=f"tile_btn_{n}"):
                    st.session_state["metric_mode_alt"] = not alt
                    st.rerun()

    st.caption("Showing point / value change — click any tile for %" if alt
               else "Showing % change — click any tile for points / values")


def _bar_panel(rows, highlight: str | None, avg_note: str):
    """Horizontal return bars with an average line. Shared by all right-panel modes."""
    import plotly.graph_objects as go

    rows = sorted(rows, key=lambda r: r["change"])
    fig = go.Figure(go.Bar(
        x=[r["change"] for r in rows], y=[r["name"] for r in rows],
        orientation="h",
        marker=dict(color=[charts.SERIES_1 if r["name"] == highlight
                           else (charts.POS if r["change"] >= 0 else charts.NEG)
                           for r in rows],
                    line=dict(width=0)),
        hovertemplate="%{y}: %{x:+.1f}%<extra></extra>",
    ))
    charts.base_layout(fig, height=430)
    fig.update_xaxes(ticksuffix="%")
    fig.update_layout(bargap=0.35)
    avg = sum(r["change"] for r in rows) / len(rows)
    fig.add_vline(x=avg, line_dash="dash", line_color=charts.INK_MUTED,
                  annotation_text=f"Avg {avg:+.1f}%", annotation_position="bottom",
                  annotation_font=dict(size=11, color=charts.INK_SECONDARY))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption(avg_note)


def _snapshot_line(indices, sectors) -> str:
    top = sorted(sectors, key=lambda s: -s["change"])[:3]
    bottom = sorted(sectors, key=lambda s: s["change"])[:3]
    return (
        "; ".join(f"{i['name']} {i['value']} ({i['change']})" for i in indices)
        + ". Leading sectors: " + ", ".join(f"{s['name']} {s['change']:+.1f}%" for s in top)
        + ". Lagging: " + ", ".join(f"{s['name']} {s['change']:+.1f}%" for s in bottom)
    )


def render():
    st.title("Market Dashboard")

    indices, sectors_1d, quotes_live = live_data.get_market_data()
    headlines, news_live = live_data.get_headlines()

    if quotes_live or news_live:
        status = ("🟢 Live · quotes and news from the selected sources · "
                  f"refreshed {datetime.now():%H:%M}")
    else:
        status = f"⚪ Offline — bundled sample data (as of {d.AS_OF.strftime('%B %d, %Y')})"
    st.caption(f"{live_data.SOURCES_LABEL} — {status}")

    _metric_row(indices)

    st.divider()

    # ---------------------------------------------------- AI market outlook
    out_l, out_r = st.columns([4, 1])
    out_l.subheader("AI Market Outlook")
    if out_r.button("↻ Re-fetch", key="refresh_outlook",
                    help="Re-pull the feeds and rebuild the outlook from the latest news"):
        live_data.get_headlines.clear()
        insights.market_outlook.clear()
        st.rerun()

    if llm.live():
        try:
            # The freshest slice is enough for a same-day read, and keeps the
            # citation numbering short enough for the model to keep straight.
            for_outlook = headlines[:60]
            # FOMC first: a rate decision outranks anything else on the calendar.
            rows = [(r["date"], r["label"])
                    for r in live_data.upcoming_fomc(days=7)]
            rows += [(r["date"], f"{r['name']} ({r['symbol']}) reports earnings")
                     for r in live_data.get_earnings_calendar(days=7)]
            rows += [(r["date"], r["label"])
                     for r in live_data.macro_calendar(days=7)]
            calendar_text = "\n".join(f"{d} — {label}"
                                      for d, label in sorted(rows))
            key = insights._key(for_outlook, "outlook", calendar_text)
            with st.spinner("Synthesising across sources…"):
                result = insights.market_outlook(key, for_outlook,
                                                 _snapshot_line(indices, sectors_1d),
                                                 calendar_text)
            st.markdown(result["summary"])
            st.caption(f"Generated by {llm.provider_label()} from the {len(for_outlook)} "
                       f"freshest of {len(headlines)} articles pulled this cycle · "
                       "earnings dates from Yahoo Finance · citations link to their article.")
        except Exception as exc:
            st.error(f"Could not generate the outlook: {exc}")
            st.markdown(d.DEMO_OUTLOOK)
    else:
        st.markdown(d.DEMO_OUTLOOK)

    with st.expander(f"Sources used ({len(headlines)} articles)", expanded=False):
        for a in headlines:
            label = a["title"] if len(a["title"]) <= 90 else a["title"][:88] + "…"
            if a.get("link"):
                st.markdown(f"- **{a['source']}** · [{label}]({a['link']})")
            else:
                st.markdown(f"- **{a['source']}** · {label}")

    st.divider()

    # ------------------------------------------------------------- charts
    left, right = st.columns(2)

    with left:
        pc_l, pc_r = st.columns([3, 1])
        pc_l.subheader("Price chart")
        if pc_r.button("↻ Prices", key="refresh_prices",
                       help="Re-pull quotes and price history for this chart"):
            for fn in (live_data.get_market_data, live_data.get_history,
                       live_data.get_sector_performance, live_data.get_group_performance,
                       live_data.get_curve):
                fn.clear()
            st.rerun()

        c1, c2 = st.columns([1, 1])
        picked_name = c1.selectbox("Index", list(INDEX_CHOICES), key="chart_index")
        query = c2.text_input("Search any index or security", key="chart_search",
                              placeholder="e.g. TSM, 2330.TW, apple")

        timeframe = st.segmented_control(
            "Timeframe", list(live_data.TIMEFRAMES), default="3M", key="chart_tf",
        ) or "3M"

        symbol, shown_name, is_search = INDEX_CHOICES[picked_name], picked_name, False
        if query.strip():
            found_sym, found_name = live_data.lookup_symbol(query)
            if found_sym:
                symbol, shown_name, is_search = found_sym, found_name, True
                st.caption(f"Showing search result **{found_name}** ({found_sym}) — "
                           "clear the box to use the dropdown.")
            else:
                st.warning(f"No security found for “{query}” — showing {picked_name}.")

        dates, values, hist_live = live_data.get_history(symbol, timeframe)
        bench_return = None
        if len(values) >= 2 and values[0]:
            bench_return = (values[-1] / values[0] - 1) * 100

        if not values:
            st.info("No price history available for this selection right now.")
        else:
            if not hist_live:
                st.caption("⚪ sample data")
            fig = go.Figure(go.Scatter(
                x=dates, y=values, mode="lines",
                line=dict(color=charts.SERIES_1, width=2),
                hovertemplate="%{x}<br>%{y:,.2f}<extra></extra>",
            ))
            charts.base_layout(fig, height=340)
            fig.update_xaxes(rangeslider_visible=True, rangeslider_thickness=0.08)
            fig.update_yaxes(autorange=True, fixedrange=False)
            title = f"{shown_name} — {timeframe}"
            if bench_return is not None:
                title += f" ({bench_return:+.1f}%)"
            fig.update_layout(title=dict(text=title, font=dict(size=14, color=charts.INK)),
                              margin=dict(l=8, r=8, t=40, b=8))
            st.plotly_chart(fig, width="stretch",
                            config={"displayModeBar": True, "scrollZoom": True,
                                    "modeBarButtonsToRemove": ["lasso2d", "select2d"]})
            st.caption("Drag to zoom, use the slider below the chart, or scroll to zoom in and out.")

    with right:
        kind = INDEX_KIND.get(picked_name, "index") if not is_search else "search"

        if is_search:
            peer_syms = live_data.get_peers(symbol)
            rows = []
            for sym in [symbol] + peer_syms:
                p_dates, p_values, p_live = live_data.get_history(sym, timeframe)
                if p_live and len(p_values) >= 2 and p_values[0]:
                    rows.append({"name": sym,
                                 "change": round((p_values[-1] / p_values[0] - 1) * 100, 2)})
            if len(rows) > 1:
                st.subheader(f"Peer performance — {timeframe}")
                _bar_panel(rows, symbol,
                           f"**{symbol}** (blue) vs Yahoo Finance's peer set; dashed line "
                           "is the group average. Clear the search box for the index views.")
            else:
                st.subheader(f"Sector performance — {timeframe}")
                sectors, _live = live_data.get_sector_performance(timeframe)
                _bar_panel(sectors, None,
                           f"No peer set available for **{shown_name}** — showing US "
                           "sector ETFs instead; dashed line is the sector average.")

        elif kind == "yield":
            st.subheader("US Treasury yield curve")
            rows, live = live_data.get_curve(tuple(live_data.YIELD_CURVE_POINTS),
                                             timeframe, anchor_rrp=True)
            if not rows:
                st.info("Yield-curve data unavailable right now.")
            else:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=[r["label"] for r in rows], y=[r["then"] for r in rows],
                    mode="lines+markers", name=f"{timeframe} ago",
                    line=dict(color=charts.BASELINE, width=2, dash="dash"),
                    marker=dict(size=7, color=charts.BASELINE),
                    hovertemplate="%{x}: %{y:.2f}%<extra>" + f"{timeframe} ago</extra>",
                ))
                fig.add_trace(go.Scatter(
                    x=[r["label"] for r in rows], y=[r["now"] for r in rows],
                    mode="lines+markers", name="Today",
                    line=dict(color=charts.SERIES_1, width=2.5),
                    marker=dict(size=8, color=charts.SERIES_1),
                    hovertemplate="%{x}: %{y:.2f}%<extra>Today</extra>",
                ))
                charts.base_layout(fig, height=430)
                fig.update_yaxes(ticksuffix="%")
                fig.update_layout(showlegend=True,
                                  legend=dict(orientation="h", y=1.08, x=0))
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
                avg_shift = sum(r["now"] - r["then"] for r in rows) / len(rows) * 100
                span = f"{rows[0]['label']}–{rows[-1]['label']}"
                anchored = rows[0]["label"] == "O/N RRP"
                st.caption(
                    f"Treasury curve today vs {timeframe} ago ({span}). Average shift "
                    f"across the curve: {avg_shift:+.0f} bps."
                    + (" The curve is anchored at the overnight reverse-repo award "
                       "rate (New York Fed), the floor the rest of the curve prices "
                       "off." if anchored else ""))

        elif kind == "level":
            st.subheader("VIX term structure")
            rows, live = live_data.get_curve(tuple(live_data.VIX_TERM_POINTS), timeframe)
            if not rows:
                st.info("Volatility term-structure data unavailable right now.")
            else:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=[r["label"] for r in rows], y=[r["then"] for r in rows],
                    mode="lines+markers", name=f"{timeframe} ago",
                    line=dict(color=charts.BASELINE, width=2, dash="dash"),
                    marker=dict(size=7, color=charts.BASELINE),
                    hovertemplate="%{x}: %{y:.1f}<extra>" + f"{timeframe} ago</extra>",
                ))
                fig.add_trace(go.Scatter(
                    x=[r["label"] for r in rows], y=[r["now"] for r in rows],
                    mode="lines+markers", name="Today",
                    line=dict(color=charts.SERIES_1, width=2.5),
                    marker=dict(size=8, color=charts.SERIES_1),
                    hovertemplate="%{x}: %{y:.1f}<extra>Today</extra>",
                ))
                charts.base_layout(fig, height=430)
                fig.update_layout(showlegend=True,
                                  legend=dict(orientation="h", y=1.08, x=0))
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
                avg_shift = sum(r["now"] - r["then"] for r in rows) / len(rows)
                st.caption("Implied-volatility term structure today vs "
                           f"{timeframe} ago. Average shift: {avg_shift:+.1f} vol points.")

        elif picked_name == "TAIEX":
            st.subheader(f"TAIEX heavyweights — {timeframe}")
            rows, live = live_data.get_group_performance(
                tuple(live_data.TAIEX_CONSTITUENTS), timeframe)
            if not rows:
                st.info("Taiwan constituent data unavailable right now.")
            else:
                _bar_panel(rows, None,
                           "Largest TAIEX constituents over the selected timeframe; "
                           "dashed line is the group average.")

        else:
            st.subheader(f"Sector performance — {timeframe}")
            sectors, sectors_live = live_data.get_sector_performance(timeframe)
            if not sectors_live:
                st.caption("⚪ sample data")
            _bar_panel(sectors, None,
                       "US sector ETFs over the selected timeframe; dashed line is "
                       "the sector average.")

    st.divider()

    # ----------------------------------------------------------- headlines
    head_l, head_r = st.columns([4, 1])
    head_l.subheader("Latest across sources")
    if head_r.button("↻ Refresh", help="Clear the cache and re-pull all feeds"):
        for fn in (live_data.get_headlines, live_data.get_market_data,
                   live_data.get_history, live_data.get_sector_performance,
                   live_data.get_sa_analysis):
            fn.clear()
        st.rerun()

    q_col, filt_col, num_col = st.columns([2, 2, 1])
    query = q_col.text_input(
        "Search headlines", placeholder="e.g. TSMC, oil, Fed",
        help="Filters what's already pulled. If nothing matches, the selected "
             "sources are searched for more coverage on that subject.",
    ).strip()
    src_filter = filt_col.multiselect(
        "Filter by source",
        options=sorted({h["source"] for h in headlines}),
        placeholder="All sources",
    )
    limit = num_col.selectbox("Show", [15, 30, 60, "All"], index=0,
                              help="How many headlines to list")

    pool, fetched_more = headlines, False
    if query:
        pool = live_data.articles_mentioning(query, headlines)
        if not pool:
            # Nothing in this cycle's pull mentions it — go and fetch some.
            with st.spinner(f"No match in the current pull — searching the sources "
                            f"for “{query}”…"):
                pool = live_data.search_news(query, limit=25)
            fetched_more = True

    matching = [h for h in pool if not src_filter or h["source"] in src_filter]
    shown = matching if limit == "All" else matching[:limit]

    if query and fetched_more:
        st.caption(f"🔎 Fetched {len(pool)} fresh articles on “{query}” from the "
                   "selected sources." if pool else
                   f"Nothing found for “{query}” in the selected sources.")
    elif query:
        st.caption(f"Showing {len(shown)} of {len(matching)} headlines matching "
                   f"“{query}” from this cycle's {len(headlines)} articles.")
    else:
        st.caption(f"Showing {len(shown)} of {len(matching)} headlines "
                   f"({len(headlines)} pulled from the selected sources this cycle)")

    for h in shown:
        with st.container(border=True):
            top = st.columns([5, 1])
            title = f"[{h['title']}]({h['link']})" if h.get("link") else f"**{h['title']}**"
            top[0].markdown(title)
            badge = SENTIMENT_BADGE.get(h["sentiment"], "⚪")
            top[1].caption(f"{badge} {h['sentiment']}")
            meta = f"{h['source']} · {h['category']} · {h['time']}"
            if h.get("also_in"):
                meta += " · similar story also in " + ", ".join(h["also_in"])
            st.caption(meta)
            if h["summary"]:
                st.write(h["summary"])
