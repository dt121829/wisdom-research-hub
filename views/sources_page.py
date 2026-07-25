import streamlit as st

SOURCES = [
    {
        "name": "Bloomberg Terminal (incl. Bloomberg Intelligence)",
        "type": "Institutional data & research",
        "unique": "Real-time market data, BI analyst research, fund letters, and 13F holdings — "
                  "the primary window into *actual buyside positioning* rather than opinions.",
        "complements": "Provides the positioning ground-truth against which the narrative "
                       "sources (media, contributors) can be tested.",
    },
    {
        "name": "Seeking Alpha",
        "type": "Crowd-sourced & buyside-adjacent analysis",
        "unique": "Long-form theses from independent analysts and former buyside professionals, "
                  "including contrarian views that never appear in mainstream coverage.",
        "complements": "Supplies the bull/bear argument texture and early divergence signals "
                       "that complement Bloomberg's quantitative positioning data.",
    },
    {
        "name": "The Wall Street Journal",
        "type": "Premier financial journalism",
        "unique": "Deep reporting on macro policy, corporate strategy, and market structure "
                  "with strong sourcing inside institutions and government.",
        "complements": "Provides the macro narrative frame that contextualises single-name "
                       "research from Seeking Alpha and Barron's.",
    },
    {
        "name": "Barron's",
        "type": "Investment-focused weekly analysis",
        "unique": "Actionable, valuation-driven investment ideas and strategist interviews — "
                  "closer to research than news.",
        "complements": "Bridges journalism and research; its strategist surveys are a useful "
                       "sell-side consensus benchmark to contrast with buyside views.",
    },
    {
        "name": "CNBC",
        "type": "Real-time market news",
        "unique": "Fastest of the five for breaking events, earnings headlines, and "
                  "management interviews.",
        "complements": "Feeds the event-driven report pipeline where timeliness matters most; "
                       "the slower sources then add depth.",
    },
]


def render():
    st.title("Sources & Methodology")

    st.subheader("Why these five sources")
    st.write(
        "Wisdom Family Office historically relied on private-bank outlook reports and earnings "
        "releases — a sell-side-heavy mix. The gap this platform closes is the systematic "
        "integration of **buyside perspectives** (asset managers, hedge funds) and independent "
        "analysis. Each source below was selected for a distinct, complementary role:"
    )

    for s in SOURCES:
        with st.container(border=True):
            st.markdown(f"**{s['name']}**  \n*{s['type']}*")
            st.markdown(f"- **Unique value:** {s['unique']}")
            st.markdown(f"- **How it complements the others:** {s['complements']}")

    st.divider()

    st.subheader("Connector status")
    st.markdown("""
| Source | Connector | Status |
|---|---|---|
| CNBC | Official RSS (Top News, Investing) | 🟢 **Live** |
| WSJ | Dow Jones public RSS (Markets, Business) | 🟢 **Live** |
| Seeking Alpha | RSS (Market Currents + long-form analysis feed) | 🟢 **Live** |
| Market quotes | Yahoo Finance (indices, 10Y, VIX, sector ETFs) | 🟢 **Live** |
| Barron's | Licensed content feed (subscription API) | ⚪ Planned — no free public feed |
| Bloomberg Terminal | Desktop export / B-PIPE (firm licence) | ⚪ Planned — manual export in the interim |

All live connectors are cached (5–15 min) and fall back to the bundled sample
dataset automatically if a feed is unreachable, so the app degrades gracefully offline.
""")

    st.subheader("End-to-end AI workflow")
    st.markdown("""
| Stage | What happens | How |
|---|---|---|
| **1 · Data input** | Collect articles, research notes, fund letters, 13F filings, PDFs and charts from the five sources | RSS/API pulls (CNBC, Seeking Alpha), licensed feeds (WSJ, Barron's), Terminal exports (Bloomberg); PDFs and images pass through Claude's native document & vision input |
| **2 · Processing & analysis** | Extract key claims, summarise, tag sentiment/topic/entity; read charts and tables inside documents | Claude analyses both text and visual content (graphs, tables) in a single pass; output is stored as structured records |
| **3 · Cross-source synthesis** | Identify consensus, divergence, and unique insights; separate buyside from sell-side voices | Synthesis prompts compare records across sources; divergence is surfaced explicitly rather than averaged away |
| **4 · Output** | Dashboard outlook, buyside consensus map, on-demand reports, conversational Q&A | Streamlit front-end; reports configurable by type, audience, length, style, language, and purpose |
""")

    st.subheader("Report types supported")
    st.markdown("""
- **Event-driven** — central bank decisions, macro releases, earnings: optimised for speed of synthesis.
- **Outlook** — quarterly/annual: organised around themes, consensus, and divergence.
- **Product-specific** — single security or sector: depth-first, with bull/bear cases compared across sources.
""")

    st.caption(
        "This prototype ships with a sample dataset so every screen works without credentials. "
        "Connecting the live ingestion pipeline replaces `data/sample_data.py` with the "
        "production content store; no UI changes required."
    )
