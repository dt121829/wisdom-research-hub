"""Report generation: prompt construction, citation linking + demo fallbacks."""

import re
from datetime import datetime

SOURCE_NAMES = ("CNBC", "Seeking Alpha", "Yahoo Finance", "Yahoo 奇摩股市",
                "SumZero", "WhaleWisdom")

# Longest first, so "Yahoo 奇摩股市" is not shadowed by the "Yahoo Finance" branch.
_SRC_ALT = "|".join(re.escape(s) for s in sorted(SOURCE_NAMES, key=len, reverse=True))
# "[CNBC 4]", "[Yahoo Finance 12]" and "[Yahoo Finance 2, 6]" — one or more article
# numbers pinned to a source. The multi-number form is what the model produces most
# often, and missing it used to leave those citations unlinked.
_NUMBERED_CITE_RE = re.compile(
    r"\[(%s)\s*#?\s*(\d+(?:\s*[,;&]\s*#?\s*\d+)*)\]" % _SRC_ALT)
# "[CNBC]" or "[CNBC; Yahoo Finance]" — source named but no article pinned.
_PLAIN_CITE_RE = re.compile(r"\[((?:%s)(?:\s*[;,·]\s*(?:%s))*)\]" % (_SRC_ALT, _SRC_ALT))


def numbered_article_block(articles: list[dict]) -> str:
    """Render the supplied articles with the reference numbers the model must cite."""
    return "\n".join(
        f"[{n}] {a['source']} — {a['title']} — {a.get('summary', '')}"
        for n, a in enumerate(articles, 1)
    )


def link_citations(text: str, articles: list[dict]) -> str:
    """Turn every inline citation into a link to the article it refers to.

    "[CNBC 4]" links straight to article 4's URL. A citation that names a source
    without pinning an article falls back to that source's first article, so no
    citation is ever left unlinked.
    """
    if not articles:
        return text

    def first_link_for(source: str) -> str:
        for a in articles:
            if a["source"].lower() == source.strip().lower() and a.get("link"):
                return a["link"]
        return ""

    def numbered(match):
        """Link each article number separately: [Yahoo Finance 2, 6] → two links."""
        source = match.group(1)
        nums = [int(n) for n in re.findall(r"\d+", match.group(2))]
        parts = []
        for num in nums:
            link = ""
            if 1 <= num <= len(articles):
                link = articles[num - 1].get("link", "")
            link = link or first_link_for(source)
            label = f"\\[{source} {num}\\]"
            parts.append(f"[{label}]({link})" if link else label)
        return "".join(parts)

    def plain(match):
        names = re.split(r"\s*[;,·]\s*", match.group(1))
        link = next((first_link_for(n) for n in names if first_link_for(n)), "")
        label = f"\\[{match.group(1)}\\]"
        return f"[{label}]({link})" if link else label

    text = _NUMBERED_CITE_RE.sub(numbered, text)
    text = _PLAIN_CITE_RE.sub(plain, text)
    return text


def add_source_links(text: str, articles: list[dict]) -> str:
    """Link inline citations and append the numbered Sources section."""
    if not articles:
        return text
    text = link_citations(text, articles)

    lines = ["", "---", "", "## Sources", ""]
    for n, a in enumerate(articles, 1):
        title = a["title"] if len(a["title"]) <= 90 else a["title"][:88] + "…"
        if a.get("link"):
            lines.append(f"{n}. [{a['source']} · {title}]({a['link']})")
        else:
            lines.append(f"{n}. {a['source']} · {title}")
    lines.append("")
    lines.append("*Points marked “external — not from selected sources” draw on material "
                 "outside the articles listed above.*")
    return text + "\n".join(lines)

REPORT_TYPES = {
    "Event-driven report": "Focus on timeliness and rapid synthesis of a specific event "
                           "(central bank decision, macro release, earnings print). Lead with "
                           "what happened, then market reaction, then implications.",
    "Outlook report": "Focus on key themes, the consensus view, and where credible sources "
                      "diverge from consensus. Organise by theme, not by source.",
    "Product-specific report": "In-depth analysis of a single security, sector, or product. "
                               "Compare perspectives across sources, include bull and bear "
                               "cases, valuation context, and key monitorables.",
}

AUDIENCES = {
    "Retail Client": "Assume limited finance vocabulary. Explain jargon inline. Short sentences.",
    "Institutional Client": "Assume professional fluency. Be precise with figures and positioning data.",
    "Investment Committee": "Decision-oriented. Lead with the recommendation-relevant facts, "
                            "flag risks and dissenting views prominently, end with monitorables.",
}

# (description, max_tokens, word cap without valuation, word cap with valuation).
# The caps are what actually fits the PDF layout at 9.5pt on A4 once the charts
# and header band are placed.
LENGTHS = {
    "1 page": ("Roughly 450-550 words.", 10000, 500, 700),
    "3 pages": ("Roughly 1,200-1,500 words with section headers.", 16000, 1400, 1700),
    "10 pages": ("Comprehensive, roughly 4,000-5,000 words with numbered sections, "
                 "sub-sections, and a table where useful.", 28000, 4500, 5000),
}

STYLES = {
    "Simple": "Plain language, minimal jargon, use analogies where helpful.",
    "Professional": "Standard institutional research tone.",
    "Technical": "Full technical depth: valuation multiples, spreads, positioning data, factor exposures.",
}

LANGUAGES = ["English", "Traditional Chinese"]

# How much source material to gather. A retail morning note is well served by the
# headline coverage; an institutional or technical piece needs the deeper pool to
# have anything worth saying at that level of detail.
_AUDIENCE_DEPTH = {"Retail Client": 0, "Institutional Client": 1,
                   "Investment Committee": 1}
_STYLE_DEPTH = {"Simple": 0, "Professional": 1, "Technical": 2}
_DEPTH_ARTICLES = {0: 14, 1: 26, 2: 40, 3: 50}


def source_depth(audience: str, style: str, length: str = "3 pages") -> int:
    """Number of topic articles to gather for this report specification."""
    score = _AUDIENCE_DEPTH.get(audience, 0) + _STYLE_DEPTH.get(style, 0)
    if length == "10 pages":
        score += 1
    return _DEPTH_ARTICLES[min(score, 3)]

PURPOSES = {
    "Morning Brief": "A same-day briefing to be read in under five minutes.",
    "Investment Memo": "A document supporting a specific investment decision.",
    "Client Update": "A communication that will be forwarded to clients of the family office.",
    "Market Outlook": "A forward-looking piece covering the next one to two quarters.",
}


def build_valuation_block(fundamentals: dict, comparables: list[dict]) -> str:
    """Financial data the model needs to run a valuation. Empty when no ticker."""
    if not fundamentals:
        return ""
    lines = [f"\nFINANCIAL DATA for {fundamentals['name']} ({fundamentals['symbol']}) "
             f"— Yahoo Finance, {datetime.now():%Y-%m-%d}:",
             f"Sector: {fundamentals.get('sector', 'n/a')} · "
             f"Industry: {fundamentals.get('industry', 'n/a')} · "
             f"Trading currency: {fundamentals.get('currency', 'USD')}"]
    ccy = fundamentals.get("currency", "USD")
    if fundamentals.get("fx_applied"):
        lines.append(
            f"All money figures and multiples below are stated in {ccy}. The company "
            f"reports in {fundamentals['financial_currency']}; those statement figures "
            f"have already been converted at the spot rate "
            f"{fundamentals['fx_rate']:.4f} {fundamentals['financial_currency']}/{ccy}, "
            f"and enterprise value is rebuilt as market cap + debt - cash so every "
            f"multiple is on one currency. They are directly comparable with the peers "
            f"below. State the currency when quoting a figure; do not warn the reader "
            "about currency mixing — it has been handled.")
    else:
        lines.append(f"All money figures and multiples below are stated in {ccy}.")

    for label, value in fundamentals["metrics"].items():
        lines.append(f"  {label}: {value}")

    if comparables and len(comparables) > 1:
        lines.append(f"\nPEER COMPARABLES — same sector, all figures in {ccy} "
                     "(Yahoo Finance, converted where needed):")
        lines.append("  Ticker | Market cap | Fwd P/E | Trail P/E | EV/EBITDA | "
                     "P/S | Rev growth | Op margin")
        for r in comparables:
            mark = " (SUBJECT)" if r["is_subject"] else ""
            note = f"  [converted from {r['converted_from']}]" if r.get("converted_from") else ""
            lines.append(f"  {r['symbol']}{mark} | {r['market_cap']} | {r['fwd_pe']} | "
                         f"{r['trail_pe']} | {r['ev_ebitda']} | {r['ps']} | "
                         f"{r['rev_growth']} | {r['op_margin']}{note}")
        sectors = {r.get("sector") for r in comparables if r.get("sector")}
        if len(sectors) == 1:
            lines.append(f"  All peers are in the {next(iter(sectors))} sector.")
    return "\n".join(lines) + "\n"


VALUATION_INSTRUCTIONS = """
## Valuation
Because this report covers a specific security, include a valuation section built ONLY
from the financial data supplied above:

**Comparables** — a Markdown table of the subject against its peers on the multiples
given (forward P/E, EV/EBITDA, P/S, revenue growth, operating margin). State the
currency once in the section intro. Follow the table with 2-4 bullets: where the
subject sits versus the peer set, and whether any premium or discount is justified by
its growth and margins.

**Reverse-DCF sanity check** — do not invent a full model. Instead:
- State the current price, free cash flow and market cap from the data.
- State clearly labelled assumptions you have chosen (discount rate ~9-10% for a
  large cap, terminal growth 2-3%, and an explicit forecast growth rate).
- Work through the arithmetic in 3-5 bullets to a rough intrinsic value per share.
- Say plainly what growth rate the current price implies, and whether that looks
  demanding or conservative against the revenue/earnings growth in the data.
- End with one line stating this is a simplified check on published figures, not a
  full model, and that the inputs are single-source.
"""


def build_report_messages(topic, report_type, audience, length, style, language, purpose,
                          topic_articles=None, valuation_block=""):
    length_desc, max_tokens, cap_plain, cap_valuation = LENGTHS[length]
    word_cap = cap_valuation if valuation_block else cap_plain
    # Per-section budgets scale with the page count; models hold to these far more
    # reliably than to a single global word count.
    summary_bullets, analysis_bullets, analysis_sections, monitor_items = {
        "1 page": (4, 3, 2, 3),
        "3 pages": (5, 5, 3, 4),
        "10 pages": (6, 8, 6, 5),
    }[length]
    topic_block = ""
    if topic_articles:
        topic_block = ("\nNUMBERED SOURCE ARTICLES from the selected sources — cite these "
                       "by their number:\n" + numbered_article_block(topic_articles) + "\n")
    lang_line = (
        "Write the entire report in Traditional Chinese (繁體中文), using terminology standard "
        "in Taiwan's financial industry."
        if language == "Traditional Chinese"
        else "Write the report in English."
    )
    valuation_section = VALUATION_INSTRUCTIONS if valuation_block else ""
    prompt = f"""Generate an investment research report with the following specification:
{topic_block}{valuation_block}
TOPIC: {topic}
REPORT TYPE: {report_type} — {REPORT_TYPES[report_type]}
AUDIENCE: {audience} — {AUDIENCES[audience]}
LENGTH: {length} — {length_desc}
WRITING STYLE: {style} — {STYLES[style]}
LANGUAGE: {lang_line}
PURPOSE: {purpose} — {PURPOSES[purpose]}

Sourcing rules:
- Ground the report in the supplied source material (the firm's selected sources:
  Seeking Alpha, Yahoo Finance, CNBC, SumZero).
- CITE BY NUMBER. Every claim taken from the material must carry the source name and
  the article's number from the numbered list above, e.g. [CNBC 4] or [Yahoo Finance 11].
  The number must be the article the claim actually came from — these become clickable
  links to that exact article, so a wrong number sends the reader to the wrong place.
- Only where the material is missing information the report genuinely needs may you draw
  on wider knowledge — and every such point must end with the exact label:
  ⚠️ *external — not from selected sources*
- Synthesise across the sources rather than summarising them one by one.

Structure — use exactly this Markdown skeleton (translate the headings if the report
language is not English), filling every section:
# <A specific, informative report title>
## Executive summary
3-5 bullets. Each bullet is one tight sentence stating a conclusion, not a topic.
## <2-4 analysis sections with informative titles of your choosing>
Short paragraphs (max 3 sentences) and bullets. Every figure and claim attributed.
{valuation_section}## Buyside vs sell-side
BULLET POINTS, NOT A TABLE — a table squeezes this into unreadable columns. Use:
- **Buyside stance:** one line, naming who where the material names them
- **Buyside argument:** one line
- **Buyside risk cited:** one line
- **Sell-side / media stance:** one line
- **Sell-side argument:** one line
- **Sell-side risk cited:** one line
- **⚔️ Where they diverge:** one or two lines on the disagreement and why it matters
## Key things to monitor
3-5 numbered, concrete monitorables — each names the trigger and why it matters.

LENGTH DISCIPLINE — a HARD CAP, not a guideline:
- MAXIMUM {word_cap} WORDS for everything you write. The document is typeset to
  "{length}" and charts already occupy part of it; going over spills onto extra pages
  and breaks the format.
- Keep to these per-section budgets, which is how the cap is actually met:
  · Executive summary — at most {summary_bullets} bullets, each ONE line (max 25 words)
  · Each analysis section — at most {analysis_bullets} bullets or 2 short paragraphs,
    and at most {analysis_sections} such sections in total
  · Buyside vs sell-side — the 7 one-line bullets specified above, nothing more
  · Valuation — the comparables table, at most 4 bullets after it, and at most 6
    bullets for the reverse-DCF
  · Key things to monitor — at most {monitor_items} numbered items, one line each
- Every bullet is one line. If a point needs two lines, cut it down or drop it.
- Do not repeat a point in two sections.
- The Sources list is added automatically afterwards and does not count towards the
  cap, so never write your own sources or bibliography section.

Writing quality bar — this goes to paying clients of a family office:
- Professional research-house register throughout. No filler, no hedging boilerplate.
- Be specific: prefer "revenue rose 31% y/y [CNBC 4]" over "revenue grew strongly".
- NEVER discuss the source material itself (no "the dataset lacks...", "coverage does
  not mention...", "as an AI..."). If something is unknown, either omit it or cover it
  with a labelled external point.
- Bold the 3-6 most decision-relevant phrases in the whole report. Do not bold headings.
- Prefer tables ONLY for the comparables valuation, where columns genuinely help.
  Everywhere else use bullets.
- Output clean Markdown starting with the # title. No preamble, no closing remarks.
- End with the one-line italic disclaimer that this is research synthesis, not
  investment advice.
"""
    return [{"role": "user", "content": prompt}], max_tokens


# --------------------------------------------------------------------------- demo fallbacks

DEMO_REPORT_EN = """# Taiwan Semiconductor (TSM) — Investment Memo
*Wisdom Family Office · Sample output (demo mode) · Sources: Seeking Alpha, Yahoo Finance, CNBC, SumZero*

## Executive summary
TSMC remains the most consensus-long name across our monitored sources, and — unusually —
the buyside is *more* constructive than the sell-side. July revenue (+31% y/y, per CNBC)
and an on-track N2 ramp support the bull case; the bear case rests on currency and tariff
risk rather than demand.

## What the sources say
- **CNBC (news flow):** July sales beat; management calls 2nm demand "stronger than 3nm at
  the same stage."
- **Seeking Alpha (crowd + buyside colour):** 14 of 18 recent contributor notes rate TSM
  Buy/Strong Buy. Bears focus on NT\\$ appreciation compressing gross margin.
- **Yahoo Finance (market data & flow):** the semis complex has led sector performance
  over the past week, with TSM outpacing the broader index.
- **SumZero (buyside community):** member theses lean long TSM with FX-hedged expressions;
  AI capex guidance keeps rising (\\$420bn combined for 2026), but contributors urge
  selectivity as valuation dispersion widens.

## Buyside vs. sell-side
| | Sell-side / media | Buyside |
|---|---|---|
| Stance | Constructive, valuation-aware | Overweight, high conviction |
| Key argument | Earnings breadth improving | N2 pricing power + CoWoS capacity doubling |
| Main risk cited | Valuation | FX (NT\\$), Taiwan-strait tail risk |
| Expression | Own the leaders | Long TSM vs. short speculative AI basket, FX-hedged |

**Divergence worth noting:** hedge funds are not reducing Taiwan exposure on geopolitical
risk — they are hedging it in the FX options market. That nuance never appears in the
private-bank outlooks the office previously relied on.

## Key things to monitor
1. NT\\$ strength vs. management's margin guidance (next earnings call).
2. CoWoS capacity adds and any change to 2026 capex.
3. US tariff decisions affecting advanced-node imports.
4. Momentum crowding (quant desks flag the 96th percentile) — a factor unwind would hit semis hardest.

*This report is a synthesis of third-party research for internal use. It is not investment advice.*
"""

DEMO_REPORT_ZH = """# 台積電（TSM）— 投資備忘錄
*智慧家族辦公室 · 示範輸出（Demo 模式）· 資料來源：Seeking Alpha、Yahoo Finance、CNBC、SumZero*

## 摘要
在本所監測的五個資料來源中，台積電仍是共識度最高的多頭標的，且較為罕見的是——買方比賣方更為樂觀。
七月營收年增 31%（CNBC），2 奈米（N2）量產進度符合預期，支撐多頭論點；空頭論點主要集中在匯率與關稅風險，而非需求面。

## 各來源觀點
- **CNBC（新聞面）：** 七月營收優於預期；管理層表示 2 奈米需求「較 3 奈米同期更強」。
- **Seeking Alpha（買方與市場情緒）：** 近期 18 篇分析中有 14 篇給予買進或強力買進評等；空方聚焦新台幣升值壓縮毛利率。
- **Yahoo Finance（市場數據與資金流）：** 近一週半導體類股領先大盤，台積電表現優於指數。
- **SumZero（買方社群）：** 會員論文偏多台積電並以外匯避險；四大雲端業者 2026 年資本支出上看 4,200 億美元，惟提醒估值分歧擴大、宜精選個股。

## 買方 vs. 賣方
| | 賣方／媒體 | 買方 |
|---|---|---|
| 立場 | 審慎樂觀、重視估值 | 加碼、高信念 |
| 核心論點 | 獲利廣度改善 | N2 定價能力、CoWoS 產能倍增 |
| 主要風險 | 估值偏高 | 匯率（新台幣）、台海尾部風險 |
| 操作方式 | 持有龍頭 | 多台積電／空投機性 AI 組合，並以外匯選擇權避險 |

**值得注意的分歧：** 避險基金並未因地緣政治風險減碼台股，而是透過外匯選擇權市場進行避險——
此一細節在本所過去仰賴的私人銀行展望報告中從未出現。

## 後續觀察重點
1. 新台幣走強對毛利率指引的影響（下次法說會）。
2. CoWoS 產能擴充進度與 2026 年資本支出調整。
3. 美國對先進製程產品的關稅政策。
4. 動能因子擁擠度（量化基金指出已達第 96 百分位）——若因子反轉，半導體將首當其衝。

*本報告為第三方研究之彙整，僅供內部使用，不構成投資建議。*
"""


def demo_report(topic: str, language: str) -> str:
    body = DEMO_REPORT_ZH if language == "Traditional Chinese" else DEMO_REPORT_EN
    if "semiconductor" in topic.lower() or "tsm" in topic.lower() or "台積" in topic:
        return body
    note = (
        "> **Demo mode** — without an API key the generator returns this pre-built sample "
        f"(topic requested: *{topic}*). Add an Anthropic API key in the sidebar to generate "
        "a live report on any topic.\n\n"
    )
    return note + body
