from pathlib import Path

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


LOGO = Path(__file__).parent / "data" / "logo.svg"


def _sidebar():
    # st.logo pins the wordmark to the very top of the sidebar, above the page
    # nav, and takes far less room than a heading plus caption plus divider.
    if LOGO.exists():
        st.logo(str(LOGO), size="large")

    with st.sidebar:
        if llm.live():
            st.success(f"🤖 {llm.provider_label()}")
        else:
            st.error("🤖 Demo mode — no AI provider connected")

        with st.expander("🔧 Connection check", expanded=not llm.live()):
            st.caption("What the app can actually see right now. On a deployed app "
                       "these come from **Settings → Secrets**, not from your PC.")
            icons = {"ok": "✅", "missing": "❌", "placeholder": "⚠️", "suspect": "⚠️"}
            for row in llm.diagnose():
                where = f" · from {row['source']}" if row["source"] else ""
                st.markdown(f"{icons.get(row['state'], '•')} **{row['key']}**  \n"
                            f"<small>{row['detail']}{where}</small>",
                            unsafe_allow_html=True)

            if st.button("Test connection", width="stretch"):
                with st.spinner("Calling the deployment…"):
                    ok, message = llm.test_connection()
                (st.success if ok else st.error)(message)

            if not llm.live():
                st.caption(
                    "**Deployed and seeing this?** The three values must be pasted into "
                    "your app on share.streamlit.io → **Settings → Secrets** — the local "
                    "`secrets.toml` is git-ignored and never reaches the server. Also "
                    "check the Azure resource's **Networking** tab allows all networks, "
                    "or Streamlit Cloud cannot reach it."
                )

        with st.expander("AI provider settings", expanded=False):
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
        st.caption("Selected sources: Seeking Alpha · Yahoo Finance · Yahoo 奇摩股市 · "
                   "CNBC · SumZero · WhaleWisdom")


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
