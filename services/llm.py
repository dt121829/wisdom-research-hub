"""Provider-agnostic LLM layer.

The app's AI features call this module rather than any vendor SDK directly, so the
backend can be swapped without touching the UI.

Providers
---------
azure     Azure OpenAI Service ("Copilot") — the default.
anthropic Claude, kept as an alternative.
none      No credentials configured; callers fall back to demo content.

Azure OpenAI configuration (Streamlit secrets, or environment variables):
    AZURE_OPENAI_ENDPOINT   https://<your-resource>.openai.azure.com/
    AZURE_OPENAI_API_KEY    <key from the Azure portal>
    AZURE_OPENAI_DEPLOYMENT <your deployment name, e.g. gpt-4o>
    AZURE_OPENAI_API_VERSION  optional, defaults below
"""

import json
import os
import re

import streamlit as st

DEFAULT_API_VERSION = "2024-10-21"
ANTHROPIC_MODEL = "claude-opus-5"


# --------------------------------------------------------------------- config

def _cfg(name: str) -> str | None:
    """Read config from session state, then Streamlit secrets, then env."""
    val = st.session_state.get(name)
    if val:
        return str(val).strip()
    try:
        if name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:
        pass
    val = os.environ.get(name)
    return val.strip() if val else None


def azure_configured() -> bool:
    return all(_cfg(k) for k in
               ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT"))


def anthropic_configured() -> bool:
    return bool(_cfg("ANTHROPIC_API_KEY"))


def active_provider() -> str:
    """Which backend is live. Azure wins if both are configured."""
    if azure_configured():
        return "azure"
    if anthropic_configured():
        return "anthropic"
    return "none"


def provider_label() -> str:
    return {
        "azure": f"Copilot (Azure OpenAI · {_cfg('AZURE_OPENAI_DEPLOYMENT')})",
        "anthropic": f"Claude ({ANTHROPIC_MODEL})",
        "none": "Demo mode — no AI credentials",
    }[active_provider()]


def live() -> bool:
    return active_provider() != "none"


# -------------------------------------------------------------------- clients

def _azure_client():
    from openai import AzureOpenAI

    return AzureOpenAI(
        azure_endpoint=_cfg("AZURE_OPENAI_ENDPOINT"),
        api_key=_cfg("AZURE_OPENAI_API_KEY"),
        api_version=_cfg("AZURE_OPENAI_API_VERSION") or DEFAULT_API_VERSION,
    )


def _anthropic_client():
    import anthropic

    return anthropic.Anthropic(api_key=_cfg("ANTHROPIC_API_KEY"))


# ------------------------------------------------------------------ streaming

def stream(messages: list[dict], system: str, max_tokens: int = 4000):
    """Yield text chunks from the active provider.

    `messages` uses the shared shape [{"role": "user"|"assistant", "content": str}].
    """
    provider = active_provider()

    if provider == "azure":
        client = _azure_client()
        payload = [{"role": "system", "content": system}] + messages
        response = client.chat.completions.create(
            model=_cfg("AZURE_OPENAI_DEPLOYMENT"),
            messages=payload,
            max_tokens=max_tokens,
            temperature=0.3,
            stream=True,
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    elif provider == "anthropic":
        client = _anthropic_client()
        with client.messages.stream(
            model=ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        ) as s:
            for text in s.text_stream:
                yield text

    else:
        raise RuntimeError("No AI provider configured")


def complete(prompt: str, system: str, max_tokens: int = 2000) -> str:
    """Non-streaming completion, returned as one string."""
    return "".join(stream([{"role": "user", "content": prompt}], system, max_tokens))


# ---------------------------------------------------------------- JSON output

def _extract_json(text: str):
    """Pull a JSON value out of a model response, tolerating code fences."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Last resort: grab the outermost object or array.
    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = text.find(opener), text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("model did not return usable JSON")


def complete_json(prompt: str, system: str, max_tokens: int = 4000):
    """Completion parsed as JSON. Uses native JSON mode on Azure where available."""
    provider = active_provider()
    system = system + "\n\nRespond with valid JSON only — no prose, no code fences."

    if provider == "azure":
        client = _azure_client()
        try:
            response = client.chat.completions.create(
                model=_cfg("AZURE_OPENAI_DEPLOYMENT"),
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
        except Exception:
            # Older deployments reject response_format; retry without it.
            response = client.chat.completions.create(
                model=_cfg("AZURE_OPENAI_DEPLOYMENT"),
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.1,
            )
        return _extract_json(response.choices[0].message.content or "")

    return _extract_json(complete(prompt, system, max_tokens))
