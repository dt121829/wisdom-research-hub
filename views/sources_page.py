import streamlit as st

SOURCES = [
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
    {
        "name": "CNBC",
        "type": "Real-time market news",
        "unique": "Fastest of the four for breaking events, earnings headlines, and management "
                  "interviews — and a frequent venue for fund managers to state views on record.",
        "complements": "Feeds the event-driven report pipeline where timeliness matters most; "
                       "the slower sources then add depth.",
    },
    {
        "name": "Yahoo 奇摩股市",
        "type": "Taiwan market news (Traditional Chinese)",
        "unique": "Local-language coverage of the TAIEX, Taiwanese corporates and NT-dollar "
                  "policy that the English-language sources report late or not at all.",
        "complements": "Gives the Taiwan section of the dashboard a domestic viewpoint "
                       "rather than a foreign read-across, which matters for a "
                       "Taiwan-based family office.",
    },
    {
        "name": "SumZero",
        "type": "Buyside research community",
        "unique": "The largest members-only community of buyside professionals; long-form, "
                  "conviction-weighted investment theses written by practising fund analysts.",
        "complements": "The purest buyside signal in the set — the direct counterpart to the "
                       "sell-side and media framing in the other sources.",
    },
    {
        "name": "WhaleWisdom",
        "type": "Institutional position tracking (13F)",
        "unique": "Quarterly 13F filings turned into position changes: what institutions "
                  "actually bought and sold, rather than what they said in public.",
        "complements": "Tests the talk against the trade — a manager's stated view can be "
                       "checked against whether the filings show them adding or cutting.",
    },
]


def render():
    st.title("Sources & Methodology")

    st.subheader("Why these sources")
    st.write(
        "Wisdom Family Office historically relied on private-bank outlook reports and earnings "
        "releases — a sell-side-heavy mix. The gap this platform closes is the systematic "
        "capture of **buyside perspectives** (asset managers, hedge funds) and independent "
        "analysis. Each selected source below plays a distinct, complementary role:"
    )

    for s in SOURCES:
        with st.container(border=True):
            st.markdown(f"**{s['name']}**  \n*{s['type']}*")
            st.markdown(f"- **Unique value:** {s['unique']}")
            st.markdown(f"- **How it complements the others:** {s['complements']}")

    st.info(
        "**Source discipline.** Every AI feature in this app — the market outlook, buyside "
        "extraction, the report generator, and the research assistant — grounds its output in "
        "material retrieved from these selected sources. Where the material is missing "
        "something a task genuinely needs, the AI may supplement from outside — but every such "
        "point is explicitly labelled **⚠️ external — not from selected sources** so it can "
        "never be mistaken for sourced research. Buyside Views goes further: every quote it "
        "shows is verbatim from an article the app opened and is discarded if it cannot be "
        "found in that article, so nothing there comes from model memory."
    )

    st.divider()

    st.subheader("What counts as a buyside view")
    st.markdown("""
The firm's gap is **buyside** perspective, so the platform is deliberately strict about
what earns that label. A view is treated as buyside only when the speaker works for:

- an **asset management firm** — mutual funds, pensions, endowments, family offices,
  sovereign funds, long-only and multi-asset managers;
- a **hedge fund** or other private fund running outside capital, including private
  equity and credit;
- one of the firm's **research platforms** — a Seeking Alpha contributor, a SumZero
  member, or WhaleWisdom 13F position data.

These are captured and shown, but marked 🏛 **non-buyside** and excluded by the
*Buyside only* filter:

| Not buyside | Why | Example |
|---|---|---|
| Media commentators | Broadcast or write about markets; do not manage outside capital | A network host or newspaper columnist |
| Retail brokers and trading platforms | Sell access to markets; their analysts market to customers | eToro, Robinhood, Interactive Brokers |
| Bank and broker research | Sell-side by definition — the counterparty to the buyside | Goldman, Jefferies, UBS, Standard Chartered |
| Company executives | Talking about their own business, not allocating a portfolio | A CEO on an earnings call |
| Policymakers | Setting the conditions, not investing in them | Central bankers, ministers, regulators |

The classification follows **who employs the speaker and whether that employer invests
outside capital**, not how authoritative the comment sounds. Well-known cases are
corrected deterministically in code rather than left to the model's judgement.
""")

    st.divider()

    st.subheader("Connector status")
    st.markdown("""
| Source | Connector | Status |
|---|---|---|
| Seeking Alpha | RSS (Market Currents, analysis, Wall St Breakfast, per-ticker) | 🟢 **Live** |
| Yahoo Finance | Market data API + news RSS + per-ticker feeds + FX | 🟢 **Live** |
| Yahoo 奇摩股市 | RSS (台股, 國際股市, 財經新聞) | 🟢 **Live** |
| CNBC | Official RSS (Top News, Investing, Earnings, Technology, Business, Finance) | 🟢 **Live** |
| Federal Reserve | FOMC meeting calendar (scraped from federalreserve.gov) | 🟢 **Live** |
| SumZero | Members-only research feed (subscription API) | ⚪ Pending — no public endpoint |
| WhaleWisdom | 13F position-change API | ⚪ Pending — API returns 401 without a key |

**SumZero** and **WhaleWisdom** both need paid credentials: SumZero publishes no public
feed, and WhaleWisdom's API returns 401 without a key (they have no RSS). Both slot into
the same connector layer in `services/live_data.py` once the firm holds a subscription.
Credentials must be configured by staff in `secrets.toml` — the AI assistant never handles
logins or passwords. Until then, buyside extraction reads the live sources only.

All live connectors are cached (5–15 min) and fall back to the bundled sample dataset if a
feed is unreachable, so the app degrades gracefully rather than breaking.
""")

    st.divider()

    st.subheader("How the platform works")
    st.markdown("""
Wisdom Research Hub is a research desk in software. It continuously pulls the firm's
selected sources, reads what it finds, works out where the sources agree and disagree,
and turns that into the outputs staff actually use — a live dashboard, a comparison of
what named investors are saying, and formatted research reports.

Every cycle begins with **retrieval**: fifteen RSS feeds across Seeking Alpha, Yahoo
Finance, Yahoo 奇摩股市 and CNBC are pulled in parallel, alongside market data, FX rates
and fundamentals from Yahoo Finance, the FOMC calendar from the Federal Reserve, and
company earnings dates. Because several of those feeds mix today's stories with
evergreen items months old, every article is timestamped and anything older than thirty
hours is discarded; duplicates are collapsed by URL, by headline and by token overlap,
with Chinese headlines compared as character bigrams so they de-duplicate properly too.
What survives is a current, non-repeating pool of roughly 150–180 articles.

That pool then feeds three different kinds of analysis. The **dashboard outlook** reads
the sixty freshest articles and writes a geography-structured briefing — macro, US,
Taiwan, Asia, rest of the world — with a five-day calendar built from verified FOMC,
earnings and macro-release dates rather than from memory. **Buyside Views** goes deeper:
it opens individual articles and reads their full text, because the quote almost never
appears in the headline, extracts what named investors actually said, verifies each
quote really exists in the article it claims to come from, then searches the rest of the
coverage for other voices on the same topic and compares them against the day's price
action. The **report generator** gathers topic-specific coverage — more of it for
institutional and technical specifications than for a retail note — adds fundamentals
and same-sector peer multiples where a ticker is given, and produces a formatted PDF.

Two rules hold everywhere. Every claim carries a citation that links to the article it
came from, and anything the model contributes from outside the selected sources is
labelled as such, so a reader can always tell sourced research from inference.
""")

    st.subheader("End-to-end AI workflow")
    st.markdown("""
| Stage | What happens | How it is implemented |
|---|---|---|
| **1 · Data input** | Collect articles, full article bodies, market data, fundamentals, FX and calendars from the selected sources. Users may also attach their own PDFs, Word files, text or CSV in the Research Assistant. | 15 RSS feeds pulled in parallel; article pages fetched and stripped of navigation; Yahoo Finance for quotes, history, fundamentals and FX; Federal Reserve for FOMC dates; `services/live_data.py`, `services/documents.py` |
| **2 · Processing & analysis** | Extract key claims and verbatim quotes; summarise; tag sentiment (positive / negative / neutral / **mixed**); identify topics, named speakers, their firm and role; read numeric and tabular data (valuation multiples, curves, sector and peer returns). | Azure OpenAI reads the retrieved text; quotes are checked back against the source article and discarded if not literally present; charts and tables are computed from primary figures in `services/live_data.py`, not read off images |
| **3 · Cross-source synthesis** | Identify the consensus view, where opinions diverge, and what is genuinely differentiated. Group views by topic, name who takes which side, and test each side against the day's price action. | `buyside_pipeline()` in `services/insights.py`: read → verify → follow up across the corpus → compare, with a "Market check" line grounding each topic in market data |
| **4 · Output** | A structured, concise report with professional formatting: cover band, sections, comparables table, embedded charts, linked citations and a numbered source list. Also the dashboard outlook, buyside comparison, and conversational Q&A. | `services/reports.py` builds the specification-driven prompt; `services/pdf.py` renders PDF and Word; every report is archived in the Reports Library |
""")

    st.subheader("How a report is generated, step by step")
    st.markdown("""
1. **Specification** — you choose type (event-driven / outlook / product-specific),
   audience, length, writing style, language and purpose. This drives everything below:
   an *Institutional · Technical* brief reads up to 50 source articles where a
   *Retail · Simple* note reads 14, and each length carries a word cap and per-section
   budget so the document fits its stated page count.
2. **Retrieval** — topic and ticker-specific coverage is gathered from the selected
   sources, de-duplicated and sorted newest-first, then numbered `[1] … [n]`.
3. **Quantitative input** — when a ticker is supplied, fundamentals and same-sector peer
   multiples are pulled. Figures reported in another currency are converted at spot and
   enterprise value is rebuilt from market cap, debt and cash, so every multiple is
   comparable rather than carrying a currency caveat.
4. **Analysis and synthesis** — the model writes to a fixed skeleton: executive summary,
   analysis sections, valuation (comparables table plus a reverse-DCF with stated
   assumptions), a buyside-versus-sell-side comparison, and monitorables. It must cite
   the numbered article each claim came from.
5. **Citation linking** — every inline citation is turned into a hyperlink to that exact
   article, and a numbered Sources section is appended. Citations do not count against
   the page budget.
6. **Charts** — a price history, a peer-return comparison for single names, and a sector
   chart with the report's own sector highlighted are rendered and embedded.
7. **Rendering and archiving** — the document is typeset as a research PDF (also
   available as Word), previewed page-by-page in the app, and filed to the Reports
   Library.
""")

    st.subheader("Report types supported")
    st.markdown("""
- **Event-driven** — central bank decisions, macro releases, earnings: optimised for speed of synthesis.
- **Outlook** — quarterly/annual: organised around themes, consensus, and divergence.
- **Product-specific** — single security or sector: depth-first, with bull/bear cases compared across sources, plus valuation.
""")

    st.caption(
        "Reports are configurable by type, audience, length, writing style, language "
        "(English / Traditional Chinese) and purpose, rendered as professional research PDFs "
        "or Word documents, and every generated report is archived in the Reports Library."
    )
