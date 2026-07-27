from datetime import datetime

import streamlit as st

from services import ai, live_data, llm, report_store, reports


def render():
    st.title("AI Report Generator")
    st.caption(
        "Configure and generate a structured research report synthesised from Barron's, WSJ, "
        "CNBC, Seeking Alpha and Yahoo Finance. Supports event-driven, outlook, and "
        "product-specific report types."
    )

    with st.form("report_form"):
        c0a, c0b = st.columns([3, 1])
        topic = c0a.text_input("Topic", value="Taiwan Semiconductor (TSM)",
                               help="A ticker, sector, event, or theme.")
        symbol = c0b.text_input("Ticker (optional)", value="TSM",
                                help="Pulls company-specific coverage from Yahoo Finance "
                                     "and Seeking Alpha.")

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
            with st.spinner("Gathering topic coverage from the approved sources…"):
                topic_articles = live_data.get_topic_news(topic, symbol.strip())
            if topic_articles:
                with st.expander(f"📎 {len(topic_articles)} source articles used", expanded=False):
                    for a in topic_articles:
                        line = f"**{a['source']}** · {a['title']}"
                        st.markdown(f"- [{line}]({a['link']})" if a.get("link") else f"- {line}")

            messages, max_tokens = reports.build_report_messages(
                topic, report_type, audience, length, style, language, purpose,
                topic_articles=topic_articles,
            )
            try:
                text = st.write_stream(ai.stream_completion(messages, max_tokens=max_tokens))
            except Exception as exc:
                st.error(f"Generation failed: {exc}")
                return

            report_id = report_store.save_report(
                text, topic=topic, report_type=report_type, audience=audience,
                length=length, style=style, language=language, purpose=purpose,
                provider=llm.provider_label(),
            )
            st.session_state["last_report"] = text
            st.success(f"Saved to the Reports Library (id `{report_id}`).")
        else:
            st.info("Copilot not connected — showing a pre-built sample report. "
                    "Add your Azure OpenAI details in the sidebar for live generation.")
            text = reports.demo_report(topic, language)
            st.markdown(text)
            st.session_state["last_report"] = text

    if st.session_state.get("last_report"):
        st.download_button(
            "⬇ Download report (Markdown)",
            data=st.session_state["last_report"],
            file_name=f"report_{datetime.now():%Y%m%d_%H%M}.md",
            mime="text/markdown",
        )
