"""Report generation: prompt construction + demo-mode fallbacks."""

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

LENGTHS = {
    "1 page": ("Roughly 400-500 words.", 4000),
    "3 pages": ("Roughly 1,200-1,500 words with section headers.", 8000),
    "10 pages": ("Comprehensive, roughly 4,000-5,000 words with numbered sections, "
                 "sub-sections, and a table where useful.", 20000),
}

STYLES = {
    "Simple": "Plain language, minimal jargon, use analogies where helpful.",
    "Professional": "Standard institutional research tone.",
    "Technical": "Full technical depth: valuation multiples, spreads, positioning data, factor exposures.",
}

LANGUAGES = ["English", "Traditional Chinese"]

PURPOSES = {
    "Morning Brief": "A same-day briefing to be read in under five minutes.",
    "Investment Memo": "A document supporting a specific investment decision.",
    "Client Update": "A communication that will be forwarded to clients of the family office.",
    "Market Outlook": "A forward-looking piece covering the next one to two quarters.",
}


def build_report_messages(topic, report_type, audience, length, style, language, purpose):
    length_desc, max_tokens = LENGTHS[length]
    lang_line = (
        "Write the entire report in Traditional Chinese (繁體中文), using terminology standard "
        "in Taiwan's financial industry."
        if language == "Traditional Chinese"
        else "Write the report in English."
    )
    prompt = f"""Generate an investment research report with the following specification:

TOPIC: {topic}
REPORT TYPE: {report_type} — {REPORT_TYPES[report_type]}
AUDIENCE: {audience} — {AUDIENCES[audience]}
LENGTH: {length} — {length_desc}
WRITING STYLE: {style} — {STYLES[style]}
LANGUAGE: {lang_line}
PURPOSE: {purpose} — {PURPOSES[purpose]}

Requirements:
- Synthesise across the five sources in the context block; attribute views to sources.
- Include a dedicated section contrasting the buyside view (asset managers, hedge funds)
  with sell-side / media commentary, and state where they diverge.
- End with "Key things to monitor" and a one-line disclaimer that this is research synthesis,
  not investment advice.
- Output clean Markdown starting with a # title. Do not include any preamble before the title.
"""
    return [{"role": "user", "content": prompt}], max_tokens


# --------------------------------------------------------------------------- demo fallbacks

DEMO_REPORT_EN = """# Taiwan Semiconductor (TSM) — Investment Memo
*Wisdom Family Office · Sample output (demo mode) · Sources: Barron's, WSJ, CNBC, Seeking Alpha, Bloomberg Terminal*

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
- **Bloomberg Terminal (positioning):** Q2 13F filings show hedge funds adding semis;
  one multi-strategy fund is long TSM against a basket of unprofitable AI names.
- **WSJ / Barron's (macro frame):** AI capex guidance keeps rising (\\$420bn combined for
  2026), but strategists urge selectivity as valuation dispersion widens.

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
*智慧家族辦公室 · 示範輸出（Demo 模式）· 資料來源：Barron's、華爾街日報、CNBC、Seeking Alpha、彭博終端機*

## 摘要
在本所監測的五個資料來源中，台積電仍是共識度最高的多頭標的，且較為罕見的是——買方比賣方更為樂觀。
七月營收年增 31%（CNBC），2 奈米（N2）量產進度符合預期，支撐多頭論點；空頭論點主要集中在匯率與關稅風險，而非需求面。

## 各來源觀點
- **CNBC（新聞面）：** 七月營收優於預期；管理層表示 2 奈米需求「較 3 奈米同期更強」。
- **Seeking Alpha（買方與市場情緒）：** 近期 18 篇分析中有 14 篇給予買進或強力買進評等；空方聚焦新台幣升值壓縮毛利率。
- **彭博終端機（部位資料）：** 第二季 13F 顯示避險基金加碼半導體；一檔多策略基金作多台積電、放空無獲利支撐的 AI 概念股。
- **華爾街日報 / Barron's（總經框架）：** 四大雲端業者 2026 年資本支出上看 4,200 億美元，惟策略師提醒估值分歧擴大、宜精選個股。

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
