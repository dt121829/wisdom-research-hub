import streamlit as st

st.set_page_config(
    page_title="Wisdom Research Hub",
    page_icon="📊",
    layout="wide",
)

from services import auth, llm  # noqa: E402
from views import (  # noqa: E402
    buyside, chatbot, dashboard, report_generator, reports_library, sources_page,
)


def _sidebar():
    with st.sidebar:
        st.markdown("### 📊 Wisdom Research Hub")
        st.caption("AI-driven investment research for Wisdom Family Office")
        st.divider()

        if llm.live():
            st.success(f"🤖 {llm.provider_label()}")
        else:
            st.info("🤖 Demo mode — no AI provider connected")

        with st.expander("AI provider settings", expanded=not llm.live()):
            st.caption(
                "Copilot runs on **Azure OpenAI**. Enter the three values from your Azure "
                "portal, or set them permanently in `.streamlit/secrets.toml`."
            )
            st.text_input("Azure endpoint", key="AZURE_OPENAI_ENDPOINT",
                          placeholder="https://your-resource.openai.azure.com/")
            st.text_input("Azure API key", key="AZURE_OPENAI_API_KEY", type="password")
            st.text_input("Deployment name", key="AZURE_OPENAI_DEPLOYMENT",
                          placeholder="gpt-4o")
            st.caption("Alternatively, an Anthropic key uses Claude as a fallback provider.")
            st.text_input("Anthropic API key (optional)", key="ANTHROPIC_API_KEY",
                          type="password")

        st.divider()
        st.caption("Sources: Barron's · WSJ · CNBC · Seeking Alpha · Yahoo Finance")


if not auth.check_password():
    st.stop()

pages = [
    st.Page(dashboard.render, title="Dashboard", icon="📈", url_path="dashboard", default=True),
    st.Page(buyside.render, title="Buyside Views", icon="🏦", url_path="buyside"),
    st.Page(report_generator.render, title="AI Report Generator", icon="📝", url_path="reports"),
    st.Page(reports_library.render, title="Reports Library", icon="📚", url_path="library"),
    st.Page(chatbot.render, title="Research Assistant", icon="💬", url_path="assistant"),
    st.Page(sources_page.render, title="Sources & Methodology", icon="🗂️", url_path="sources"),
]

_sidebar()
st.navigation(pages).run()
