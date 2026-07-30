from datetime import datetime

import streamlit as st

from services import ai, documents, live_data, llm, pdf, report_store, reports


def _reference_files():
    """Optional user files folded into the report. Returns (docs, read_images)."""
    with st.expander("📎 Attach reference files (optional)", expanded=False):
        st.caption(
            "Add your own material for the report to draw on — a broker note, a fund "
            "letter, an earnings deck, a screenshot of a chart or table. PDF, Word, "
            "text, Markdown, CSV and images are supported. Anything the report takes "
            "from these is labelled as not from the selected sources. Files are "
            "processed on this machine and sent only to your configured AI provider."
        )
        uploads = st.file_uploader(
            "Reference files", type=documents.SUPPORTED, accept_multiple_files=True,
            label_visibility="collapsed", key="report_refs",
        )

        docs, any_graphics = [], False
        for upload in uploads or []:
            data = upload.getvalue()
            if documents.is_image(upload.name):
                png, note = documents.normalise_image(data)
                if not png:
                    st.warning(f"`{upload.name}`: {note}")
                    continue
                docs.append({"name": upload.name, "text": "", "chars": 0,
                             "data": data, "image": png})
                any_graphics = True
                continue
            text, note = documents.extract_text(upload.name, data)
            if note:
                (st.warning if not text else st.info)(note)
            graphics = documents.has_graphics(upload.name, data)
            any_graphics = any_graphics or graphics
            if text or graphics:
                docs.append({"name": upload.name, "text": text, "chars": len(text),
                             "data": data, "image": None, "graphics": graphics})

        read_images = False
        if any_graphics:
            read_images = st.toggle(
                "🔍 Look at the pictures (reads charts, tables and scans)", value=True,
                help="Sends screenshots and PDF pages to the model as images so it can "
                     "read figures that are drawn rather than written. Uses more quota.",
                key="report_read_images",
            )

        if docs:
            total = sum(d["chars"] for d in docs)
            bits = [f"{len(docs)} file(s)"]
            if total:
                bits.append(f"{total:,} characters")
            st.success("Reference material ready: " + " · ".join(bits) + ".")
        return docs, read_images


def _attachment_images(docs, read_images) -> list[bytes]:
    """Every picture to send with the report request (screenshots + PDF pages)."""
    if not read_images:
        return []
    pngs = []
    for doc in docs:
        if doc.get("image"):
            pngs.append(doc["image"])
        else:
            pngs += documents.page_images(doc["name"], doc["data"])
    return pngs[:8]


def _build_charts_html(symbol: str, sector: str = "", length: str = "3 pages") -> str:
    """Assemble the informative charts embedded at the top of the PDF.

    A one-page report only has room for the charts that earn their space: the
    price history and, for a single name, its peer comparison.
    """
    blocks = []
    short = length == "1 page"

    if symbol:
        dates, values, live = live_data.get_history(symbol, "6M")
        if live and values:
            png = pdf.price_chart_png(dates, values, f"{symbol.upper()} — last 6 months")
            if png:
                blocks.append(pdf._img_tag(
                    png, f"{symbol.upper()} closing price, 6 months. Data: Yahoo Finance."))

        # A single-name report is best judged against genuine sector peers.
        peers, _sector = live_data.get_sector_peers(symbol)
        if peers:
            rows = []
            for sym in [symbol.upper()] + [p.upper() for p in peers]:
                p_dates, p_values, p_live = live_data.get_history(sym, "6M")
                if p_live and len(p_values) >= 2 and p_values[0]:
                    rows.append({"name": sym,
                                 "change": round((p_values[-1] / p_values[0] - 1) * 100, 2)})
            png = pdf.peer_chart_png(rows, symbol.upper(),
                                     f"{symbol.upper()} vs peers — 6-month return")
            if png:
                blocks.append(pdf._img_tag(
                    png, f"{symbol.upper()} (blue) against its Yahoo Finance peer set, "
                         "6-month total return. Dashed line is the peer average."))

    # On a one-pager the sector chart is dropped when a peer chart already ran,
    # since the peer set is the more relevant comparison for a single name.
    if short and blocks:
        return "".join(blocks)

    sectors, live = live_data.get_sector_performance("3M")
    if live and sectors:
        title = "US sector performance — 3 months"
        if sector:
            title += f" · {sector} highlighted"
        png = pdf.sector_chart_png(sectors, title, highlight=sector)
        if png:
            caption = "US sector ETF returns, 3 months. Data: Yahoo Finance."
            if sector:
                caption = (f"US sector ETF returns, 3 months, with **{sector}** — this "
                           "report's sector — highlighted in blue. Data: Yahoo Finance.")
            blocks.append(pdf._img_tag(png, caption))
    return "".join(blocks)


def render():
    st.title("AI Report Generator")
    st.caption(
        "Configure and generate a structured research report synthesised from the selected "
        "sources — Seeking Alpha, Yahoo Finance, CNBC and SumZero. You can also attach your "
        "own reference files. The result is rendered as a professional research PDF."
    )

    ref_docs, read_images = _reference_files()

    with st.form("report_form"):
        c0a, c0b = st.columns([3, 1])
        topic = c0a.text_input("Topic", value="Taiwan Semiconductor (TSM)",
                               help="A ticker, sector, event, or theme.")
        symbol = c0b.text_input("Ticker (optional)", value="TSM",
                                help="Pulls company-specific coverage from Yahoo Finance "
                                     "and Seeking Alpha, and adds a price chart to the PDF.")

        c1, c2, c3 = st.columns(3)
        report_type = c1.selectbox("Report type", list(reports.REPORT_TYPES))
        audience = c2.selectbox("Audience", list(reports.AUDIENCES))
        length = c3.selectbox("Length", list(reports.LENGTHS))

        c4, c5, c6 = st.columns(3)
        style = c4.selectbox("Writing style", list(reports.STYLES))
        language = c5.selectbox("Language", reports.LANGUAGES)
        purpose = c6.selectbox("Purpose", list(reports.PURPOSES))

        submitted = st.form_submit_button("Generate report", type="primary", width="stretch")

    if submitted:
        st.divider()
        spec = f"{report_type} · {audience} · {length} · {style} · {language} · {purpose}"
        st.caption(f"Specification: {spec}")

        if llm.live():
            depth = reports.source_depth(audience, style, length)
            with st.spinner(f"Gathering up to {depth} articles from the selected "
                            "sources…"):
                topic_articles = live_data.get_topic_news(topic, symbol.strip(),
                                                          limit=depth)
            if topic_articles:
                st.caption(f"Reading depth for *{audience} · {style}*: up to {depth} "
                           "articles.")
                with st.expander(f"📎 {len(topic_articles)} source articles used", expanded=False):
                    for a in topic_articles:
                        line = f"**{a['source']}** · {a['title']}"
                        st.markdown(f"- [{line}]({a['link']})" if a.get("link") else f"- {line}")

            # Fundamentals + peer multiples so the model can actually value the name.
            valuation_block, sector = "", ""
            sym = symbol.strip()
            if sym:
                with st.spinner("Pulling fundamentals and peer multiples…"):
                    fundamentals = live_data.get_fundamentals(sym)
                    if fundamentals:
                        sector = fundamentals.get("sector", "")
                        # Same-sector peers only: Yahoo's raw list is behavioural.
                        peers, _sector = live_data.get_sector_peers(sym)
                        comps = live_data.get_comparables(sym, tuple(peers))
                        valuation_block = reports.build_valuation_block(fundamentals, comps)
                if valuation_block:
                    with st.expander("📊 Financial data used for the valuation",
                                     expanded=False):
                        st.code(valuation_block, language="text")
                else:
                    st.caption(f"No fundamentals available for `{sym}` — the report will "
                               "skip the valuation section.")

            # Fold in any reference files the user attached.
            attachments_block = ""
            text_docs = [d for d in ref_docs if d.get("text")]
            if text_docs:
                attachments_block = documents.as_context_block(text_docs)
            ref_images = _attachment_images(ref_docs, read_images)
            if ref_docs:
                names = ", ".join(d["name"] for d in ref_docs)
                extra = f" · {len(ref_images)} image(s)" if ref_images else ""
                st.caption(f"Including reference files: {names}{extra}.")

            messages, max_tokens = reports.build_report_messages(
                topic, report_type, audience, length, style, language, purpose,
                topic_articles=topic_articles, valuation_block=valuation_block,
                attachments_block=attachments_block,
            )
            if ref_images:
                messages[-1] = llm.attach_images(messages[-1], ref_images)
            try:
                with st.spinner("Writing the report…"):
                    text = "".join(ai.stream_completion(
                        messages, max_tokens=max_tokens, reasoning_effort="low"))
                if not text.strip():
                    st.error("The model returned an empty report — try again, or pick a "
                             "shorter length.")
                    return
                text = reports.add_source_links(text, topic_articles)
            except Exception as exc:
                st.error(f"Generation failed: {exc}")
                return

            report_id = report_store.save_report(
                text, topic=topic, report_type=report_type, audience=audience,
                length=length, style=style, language=language, purpose=purpose,
                provider=llm.provider_label(),
            )
            st.session_state["last_report"] = text
            st.session_state["last_report_spec"] = spec
            st.session_state["last_report_symbol"] = sym
            st.session_state["last_report_sector"] = sector
            st.session_state["last_report_type"] = report_type
            st.session_state["last_report_length"] = length
            st.success(f"Saved to the Reports Library (id `{report_id}`).")
        else:
            st.info("Copilot not connected — showing a pre-built sample report. "
                    "Add your Azure OpenAI details in the sidebar for live generation.")
            st.session_state["last_report"] = reports.demo_report(topic, language)
            st.session_state["last_report_spec"] = spec
            st.session_state["last_report_symbol"] = symbol.strip()
            st.session_state["last_report_type"] = report_type
            st.session_state["last_report_length"] = length

    # ------------------------------------------------------------- PDF view
    if st.session_state.get("last_report"):
        text = st.session_state["last_report"]
        try:
            with st.spinner("Rendering the PDF…"):
                charts_html = _build_charts_html(
                    st.session_state.get("last_report_symbol", ""),
                    st.session_state.get("last_report_sector", ""),
                    st.session_state.get("last_report_length", "3 pages"),
                )
                pdf_bytes = pdf.markdown_to_pdf(
                    text,
                    subtitle=st.session_state.get("last_report_spec", ""),
                    charts_html=charts_html,
                )
        except Exception as exc:
            st.error(f"PDF rendering failed ({exc}) — showing the raw text instead.")
            st.markdown(text)
            pdf_bytes = None

        if pdf_bytes:
            dl1, dl2, _sp = st.columns([1, 1, 2])
            dl1.download_button(
                "⬇ Download .pdf",
                data=pdf_bytes,
                file_name=f"report_{datetime.now():%Y%m%d_%H%M}.pdf",
                mime="application/pdf",
                type="primary",
            )
            try:
                docx_bytes = pdf.markdown_to_docx(
                    text, subtitle=st.session_state.get("last_report_spec", ""))
                dl2.download_button(
                    "⬇ Download .docx",
                    data=docx_bytes,
                    file_name=f"report_{datetime.now():%Y%m%d_%H%M}.docx",
                    mime=("application/vnd.openxmlformats-officedocument"
                          ".wordprocessingml.document"),
                )
            except Exception:
                dl2.caption("Word export unavailable")

            # Render the real PDF pages as images: always displays, regardless of
            # browser PDF-plugin policy or optional viewer components.
            try:
                pages = pdf.page_images(pdf_bytes)
            except Exception as exc:
                pages = []
                st.caption(f"Inline preview unavailable ({exc}) — use the download button.")

            if pages:
                st.caption(f"Report preview — {len(pages)} page"
                           f"{'s' if len(pages) > 1 else ''}")
                for n, png in enumerate(pages, 1):
                    st.image(png, width="stretch")
                    st.caption(f"Page {n} of {len(pages)}")

            with st.expander("View as text / copy Markdown", expanded=False):
                st.markdown(text)
