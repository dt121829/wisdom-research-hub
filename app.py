import streamlit as st

st.set_page_config(
    page_title="Wisdom Research Hub",
    page_icon="📊",
    layout="wide",
)

from services import ai, auth  # noqa: E402
from views import buyside, chatbot, dashboard, report_generator, sources_page  # noqa: E402


def _sidebar():
    with st.sidebar:
        st.markdown("### 📊 Wisdom Research Hub")
        st.caption("AI-driven investment research for Wisdom Family Office")
        st.divider()

        st.text_input(
            "Anthropic API key",
            type="password",
            key="api_key",
            help="Paste a key here for this session, or put it in .streamlit/secrets.toml "
                 "(see secrets.toml.example) so it loads automatically for everyone.",
        )
        if ai.live_mode():
            st.success("Claude connected — outlook, chatbot and reports are live")
        else:
            st.info("AI in demo mode — add an API key to enable live Claude. "
                    "Market data and headlines stream live regardless.")
        st.divider()
        st.caption("Sources: Barron's · WSJ · CNBC · Seeking Alpha · Bloomberg Terminal")


if not auth.check_password():
    st.stop()

pages = [
    st.Page(dashboard.render, title="Dashboard", icon="📈", url_path="dashboard", default=True),
    st.Page(buyside.render, title="Buyside Views", icon="🏦", url_path="buyside"),
    st.Page(report_generator.render, title="AI Report Generator", icon="📝", url_path="reports"),
    st.Page(chatbot.render, title="Research Assistant", icon="💬", url_path="assistant"),
    st.Page(sources_page.render, title="Sources & Methodology", icon="🗂️", url_path="sources"),
]

_sidebar()
st.navigation(pages).run()
