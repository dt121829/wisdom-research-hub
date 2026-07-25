from datetime import datetime

import streamlit as st

from services import ai, reports


def render():
    st.title("AI Report Generator")
    st.caption(
        "Configure and generate a structured research report synthesised from all five sources. "
        "Supports event-driven, outlook, and product-specific report types."
    )

    with st.form("report_form"):
        topic = st.text_input("Topic", value="Taiwan Semiconductor (TSM)",
                              help="A ticker, sector, event, or theme.")

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

        if ai.live_mode():
            messages, max_tokens = reports.build_report_messages(
                topic, report_type, audience, length, style, language, purpose
            )
            with st.spinner("Synthesising across sources…"):
                text = st.write_stream(ai.stream_completion(messages, max_tokens=max_tokens))
            st.session_state["last_report"] = text
        else:
            st.info("Demo mode — showing a pre-built sample report. Add an API key in the sidebar "
                    "for live generation on any topic.")
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
