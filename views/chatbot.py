import re

import streamlit as st

from services import ai, chartspec, documents, llm
from services.demo import demo_chat_reply

SUGGESTIONS = [
    "What are the main themes across our sources today?",
    "Where do the sources disagree right now?",
    "Which named investors have expressed a view this week?",
]

ATTACHED_SUGGESTIONS = [
    "Summarise the attached document in ten bullets.",
    "What does the attached say that our live sources do not?",
    "List every figure and claim in the attachment I should verify.",
]


def _stream_hiding_specs(chunks) -> str:
    """Stream the reply, keeping the chart JSON out of view.

    The spec block is machine instructions, not prose — the reader should see the
    rendered chart, never the JSON that produced it.
    """
    placeholder = st.empty()
    raw = ""
    for chunk in chunks:
        raw += chunk
        visible = chartspec.BLOCK_RE.sub("", raw)
        # Also hide a block still being written when the stream ends mid-JSON.
        visible = re.split(r"```chartspec", visible, maxsplit=1)[0]
        placeholder.markdown(visible + "▌")
    placeholder.markdown(chartspec.extract(raw)[0])
    return raw


def _attachments():
    """File uploader plus extraction, returning the documents to hand the model."""
    with st.expander("📎 Attach a document or screenshot", expanded=False):
        st.caption(
            "Attach a **screenshot or image** (PNG, JPG, WEBP, GIF, BMP) — a chart, a "
            "terminal grab, a table photographed from a printed note — or a **document** "
            "(PDF, Word, text, Markdown, CSV) such as a broker note, a fund letter, or a "
            "report from the Report Generator. Everything is processed on this machine; "
            "files are never stored or sent anywhere beyond your configured AI provider."
        )
        uploads = st.file_uploader(
            "Documents", type=documents.SUPPORTED, accept_multiple_files=True,
            label_visibility="collapsed",
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
                             "data": data, "graphics": True, "image": png,
                             "note": note})
                any_graphics = True
                continue

            text, note = documents.extract_text(upload.name, data)
            if note:
                (st.warning if not text else st.info)(note)
            graphics = documents.has_graphics(upload.name, data)
            any_graphics = any_graphics or graphics
            if text or graphics:
                docs.append({"name": upload.name, "text": text, "chars": len(text),
                             "data": data, "graphics": graphics, "image": None})

        read_images = False
        if any_graphics:
            read_images = st.toggle(
                "🔍 Look at the pictures (reads charts, tables and scans)",
                value=True,
                help="Sends screenshots, and each page of a PDF, to the model as an "
                     "image so it can read figures that are drawn rather than "
                     "written. Uses more of your Azure quota than text alone.",
            )

        pictures = [d for d in docs if d.get("image")]
        if pictures and read_images:
            cols = st.columns(min(len(pictures), 4))
            for col, doc in zip(cols, pictures):
                col.image(doc["image"], caption=doc["name"], width="stretch")
                if doc.get("note"):
                    col.caption(doc["note"])

        if docs:
            total = sum(d["chars"] for d in docs)
            bits = [f"{len(docs)} attachment(s)"]
            if total:
                bits.append(f"{total:,} characters of text")
            if read_images:
                pages = sum(1 if d.get("image")
                            else len(documents.page_images(d["name"], d["data"]))
                            for d in docs)
                bits.append(f"{pages} image(s)")
            st.success("Reading " + " · ".join(bits) + " with your next question.")
        return docs, read_images


def render():
    st.title("Research Assistant")
    st.caption(
        "Ask anything about the aggregated research. Answers are grounded in live content "
        "from the selected sources — Seeking Alpha, Yahoo Finance, Yahoo 奇摩股市, CNBC, "
        "SumZero and WhaleWisdom — and always attribute claims. Anything drawn from "
        "outside the selected sources is explicitly labelled."
    )
    if llm.live():
        st.caption(f"Powered by {llm.provider_label()}")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    docs, read_images = _attachments()

    # Suggestion chips (only before the conversation starts)
    if not st.session_state.chat_history:
        chips = ATTACHED_SUGGESTIONS if docs else SUGGESTIONS
        cols = st.columns(len(chips))
        for col, s in zip(cols, chips):
            if col.button(s, width="stretch"):
                st.session_state.pending_prompt = s
                st.rerun()

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            for n, spec in enumerate(msg.get("charts") or []):
                st.plotly_chart(chartspec.figure(spec), width="stretch",
                                config={"displayModeBar": False},
                                key=f"hist_{id(msg)}_{n}")
                if spec.get("note"):
                    st.caption(f"Chart drawn by the assistant · {spec['note']}")

    placeholder = ("Ask about the attachment, or about the live sources…"
                   if docs else "Ask a question, or attach a screenshot with 📎")
    # accept_file puts a paperclip in the message box, so a screenshot can be
    # dropped straight onto the question rather than through the panel above.
    entry = st.chat_input(placeholder, accept_file="multiple",
                          file_type=documents.SUPPORTED)

    prompt = None
    if entry is not None:
        if isinstance(entry, str):
            prompt = entry
        else:
            prompt = (entry.text or "").strip()
            for upload in entry.files or []:
                data = upload.getvalue()
                if documents.is_image(upload.name):
                    png, note = documents.normalise_image(data)
                    if png:
                        docs.append({"name": upload.name, "text": "", "chars": 0,
                                     "data": data, "graphics": True, "image": png,
                                     "note": note})
                        read_images = True
                else:
                    text, _note = documents.extract_text(upload.name, data)
                    if text:
                        docs.append({"name": upload.name, "text": text,
                                     "chars": len(text), "data": data,
                                     "graphics": documents.has_graphics(upload.name, data),
                                     "image": None})
            if not prompt and docs:
                prompt = "What does this show? Summarise it for an investment desk."

    if not prompt and "pending_prompt" in st.session_state:
        prompt = st.session_state.pop("pending_prompt")

    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            if docs:
                st.caption("📎 " + ", ".join(d["name"] for d in docs))
                shots = [d["image"] for d in docs if d.get("image")]
                if shots and read_images:
                    for col, png in zip(st.columns(min(len(shots), 4)), shots):
                        col.image(png, width="stretch")

        with st.chat_message("assistant"):
            specs = []
            if llm.live():
                messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.chat_history
                ]
                system = ai.SYSTEM_PROMPT + "\n" + chartspec.CHART_INSTRUCTIONS
                if docs:
                    system += (
                        "\n\nThe user has attached documents, supplied below. Treat them "
                        "as material the user has provided, NOT as one of the selected "
                        "sources: when a claim comes from an attachment, name the file "
                        "it came from. Where an attachment and the live sources "
                        "disagree, say so explicitly.\n\n"
                        + documents.as_context_block(docs))

                # Send the pages as pictures too, so charts and scanned tables in the
                # attachment can be read rather than skipped.
                if docs and read_images:
                    pngs = []
                    for doc in docs:
                        if doc.get("image"):
                            pngs.append(doc["image"])          # uploaded screenshot
                        else:
                            pngs += documents.page_images(doc["name"], doc["data"])
                    if pngs:
                        system += (
                            "\n\nImages follow the user's question — uploaded "
                            "screenshots and/or rendered pages of the attached "
                            "documents. Read any chart, table or figure in them. When "
                            "you quote a number taken from an image, say which image "
                            "or page it came from, and that you read it off a picture "
                            "rather than from text.")
                        messages[-1] = llm.attach_images(messages[-1], pngs[:8])

                try:
                    raw = _stream_hiding_specs(ai.stream_completion(
                        messages, system=system, max_tokens=8000,
                        reasoning_effort="low"))
                    reply, specs = chartspec.extract(raw)
                except Exception as exc:
                    reply = f"Sorry — the AI request failed: `{exc}`"
                    st.error(reply)
            else:
                reply = demo_chat_reply(prompt)
                st.markdown(reply)

            for n, spec in enumerate(specs):
                st.plotly_chart(chartspec.figure(spec), width="stretch",
                                config={"displayModeBar": False}, key=f"new_{n}")
                if spec.get("note"):
                    st.caption(f"Chart drawn by the assistant · {spec['note']}")

        st.session_state.chat_history.append(
            {"role": "assistant", "content": reply, "charts": specs})

    if st.session_state.chat_history:
        if st.button("Clear conversation"):
            st.session_state.chat_history = []
            st.rerun()
