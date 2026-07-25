import streamlit as st

from services import ai
from services.demo import demo_chat_reply

SUGGESTIONS = [
    "What's the latest on TSMC across our sources?",
    "Where do the buyside and sell-side disagree right now?",
    "Summarise hedge fund positioning from the 13F data.",
]


def render():
    st.title("Research Assistant")
    st.caption(
        "Ask anything about the aggregated research. Answers are grounded in the ingested "
        "content and always attribute claims to their source."
    )

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Suggestion chips (only before the conversation starts)
    if not st.session_state.chat_history:
        cols = st.columns(len(SUGGESTIONS))
        for col, s in zip(cols, SUGGESTIONS):
            if col.button(s, width="stretch"):
                st.session_state.pending_prompt = s
                st.rerun()

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("e.g. What is the consensus on the Fed's next move?")
    if not prompt and "pending_prompt" in st.session_state:
        prompt = st.session_state.pop("pending_prompt")

    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            if ai.live_mode():
                messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.chat_history
                ]
                reply = st.write_stream(ai.stream_completion(messages, max_tokens=4000))
            else:
                reply = demo_chat_reply(prompt)
                st.markdown(reply)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})

    if st.session_state.chat_history:
        if st.button("Clear conversation"):
            st.session_state.chat_history = []
            st.rerun()
