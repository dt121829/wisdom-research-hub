import streamlit as st

SOURCES = [
    {
        "name": "The Wall Street Journal",
        "type": "Premier financial journalism",
        "unique": "Deep reporting on macro policy, corporate strategy, and market structure, "
                  "with strong sourcing inside institutions and government.",
        "complements": "Provides the macro narrative frame that contextualises the single-name "
                       "research coming from Seeking Alpha and Barron's.",
    },
    {
        "name": "Barron's",
        "type": "Investment-focused weekly analysis",
        "unique": "Actionable, valuation-driven investment ideas and strategist interviews — "
                  "closer to research than to news.",
        "complements": "Bridges journalism and research; its strategist surveys are a useful "
                       "sell-side consensus benchmark to contrast against buyside views.",
    },
    {
        "name": "CNBC",
        "type": "Real-time market news",
        "unique": "Fastest of the five for breaking events, earnings headlines, and management "
                  "interviews — and a frequent venue for fund managers to state views on record.",
        "complements": "Feeds the event-driven report pipeline where timeliness matters most; "
                       "the slower sources then add depth.",
    },
    {
        "name": "Seeking Alpha",
        "type": "Crowd-sourced & buyside-adjacent analysis",
        "unique": "Long-form theses from independent analysts and former buyside professionals, "
                  "including contrarian views that never appear in mainstream coverage.",
        "complements": "Supplies the bull/bear argument texture and early divergence signals "
                       "that the news wires do not carry.",
    },
    {
        "name": "Yahoo Finance",
        "type": "Market data & aggregated news",
        "unique": "Real-time quotes, index and sector data, plus per-company news feeds that "
                  "make topic-specific research possible on any ticker.",
        "complements": "Supplies the quantitative backbone — prices, sector moves — against "
                       "which the narrative sources can be tested.",
    },
]


def render():
    st.title("Sources & Methodology")

    st.subheader("Why these five sources")
    st.write(
        "Wisdom Family Office historically relied on private-bank outlook reports and earnings "
        "releases — a sell-side-heavy mix. The gap this platform closes is the systematic "
        "capture of **buyside perspectives** (asset managers, hedge funds) and independent "
        "analysis. Each source below plays a distinct, complementary role:"
    )

    for s in SOURCES:
        with st.container(border=True):
            st.markdown(f"**{s['name']}**  \n*{s['type']}*")
            st.markdown(f"- **Unique value:** {s['unique']}")
            st.markdown(f"- **How it complements the others:** {s['complements']}")

    st.info(
        "**Source discipline.** Every AI feature in this app — the market outlook, the news "
        "digest, buyside extraction, the report generator, and the research assistant — is "
        "instructed to use only material retrieved from these five sources, and to say when "
        "the material does not support a claim rather than drawing on general knowledge."
    )

    st.divider()

    st.subheader("Connector status")
    st.markdown("""
| Source | Connector | Status |
|---|---|---|
| CNBC | Official RSS (Top News, Investing) | 🟢 **Live** |
| WSJ | Dow Jones public RSS (Markets, Business) | 🟢 **Live** |
| Seeking Alpha | RSS (Market Currents, analysis, per-ticker) | 🟢 **Live** |
| Yahoo Finance | Market data API + news RSS + per-ticker feeds | 🟢 **Live** |
| Barron's | Licensed content feed (subscription API) | ⚪ Pending — all public endpoints return 403 |

Barron's is hard-paywalled: every public RSS endpoint refuses anonymous requests. Wiring it
in requires the firm's Dow Jones subscription credentials (Dow Jones DNA or the Factiva API),
which slot into the same connector layer in `services/live_data.py`.

All live connectors are cached (5–15 min) and fall back to the bundled sample dataset if a
feed is unreachable, so the app degrades gracefully rather than breaking.
""")

    st.subheader("End-to-end AI workflow")
    st.markdown("""
| Stage | What happens | How |
|---|---|---|
| **1 · Data input** | Collect articles, analysis, quotes and per-ticker coverage from the five sources | RSS pulls (CNBC, WSJ, Seeking Alpha, Yahoo Finance), market data API (Yahoo Finance), licensed feed (Barron's, pending) |
| **2 · Processing & analysis** | Extract key claims, summarise, tag sentiment and topic, identify named parties and their stances | Azure OpenAI ("Copilot") reads the retrieved material; results cached so a page refresh never re-bills |
| **3 · Cross-source synthesis** | Identify consensus, divergence, and unique insight; match the same party across sources and flag where their attributed stance differs | AI extraction followed by deterministic name-matching in `services/insights.py` |
| **4 · Output** | Dashboard outlook with citations, news digest, buyside view cards, configurable reports, conversational Q&A, and a saved reports archive | Streamlit front-end; every report filed to the Reports Library |
""")

    st.subheader("Report types supported")
    st.markdown("""
- **Event-driven** — central bank decisions, macro releases, earnings: optimised for speed of synthesis.
- **Outlook** — quarterly/annual: organised around themes, consensus, and divergence.
- **Product-specific** — single security or sector: depth-first, with bull/bear cases compared across sources.
""")

    st.caption(
        "Reports are configurable by type, audience, length, writing style, language "
        "(English / Traditional Chinese) and purpose, and every generated report is archived "
        "in the Reports Library."
    )
