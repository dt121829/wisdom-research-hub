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

import base64
import json
import os
import re

import streamlit as st

DEFAULT_API_VERSION = "2025-04-01-preview"
ANTHROPIC_MODEL = "claude-opus-5"

# Model families disagree on how to cap output and whether temperature is allowed:
# GPT-5 / o-series want `max_completion_tokens` and only the default temperature,
# while GPT-4-era deployments want `max_tokens`. Rather than hard-coding a guess
# from the deployment name (which the user is free to call anything), try the
# shapes in order and remember the one that worked for each deployment.
_WORKING_SHAPE: dict[tuple, int] = {}

_PARAM_ERROR_HINTS = ("unsupported", "unrecognized", "not supported", "invalid_request",
                      "max_tokens", "max_completion_tokens", "temperature",
                      "reasoning_effort")


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


AZURE_KEYS = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT")

# Placeholder text that means "not filled in yet" rather than a real value.
_PLACEHOLDERS = ("PASTE_", "your-resource", "your-azure-key", "your-key-1-value",
                 "your-key", "<", "xxx")


def _source_of(name: str) -> str:
    """Where a setting came from — used by the on-screen diagnostic."""
    if st.session_state.get(name):
        return "sidebar (this session only)"
    try:
        if name in st.secrets:
            return "secrets"
    except Exception:
        pass
    if os.environ.get(name):
        return "environment variable"
    return ""


def diagnose() -> list[dict]:
    """Per-setting status for the Azure connection, safe to show on screen."""
    out = []
    for key in AZURE_KEYS:
        value = _cfg(key)
        source = _source_of(key)
        if not value:
            state, detail = "missing", "not set anywhere"
        elif any(p.lower() in value.lower() for p in _PLACEHOLDERS):
            state, detail = "placeholder", "still holds example text"
        elif key == "AZURE_OPENAI_API_KEY":
            state, detail = "ok", f"{value[:6]}…{value[-4:]} ({len(value)} chars)"
        elif key == "AZURE_OPENAI_ENDPOINT":
            detail = value
            if not value.startswith("https://"):
                state = "suspect"
                detail += "  ← should start with https://"
            elif "/openai/" in value or value.rstrip("/").endswith("completions"):
                state = "suspect"
                detail += "  ← use the base URL only, no path"
            else:
                state = "ok"
        else:
            state, detail = "ok", value
        out.append({"key": key, "state": state, "detail": detail, "source": source})
    return out


def test_connection() -> tuple[bool, str]:
    """Make one tiny call and translate the result into plain English."""
    if not azure_configured():
        return False, "Azure settings are incomplete — see the checklist above."
    try:
        client = _azure_client()
        response = _azure_create(
            client, [{"role": "user", "content": "Reply with: ok"}], 20,
            reasoning_effort="low")
        reply = (response.choices[0].message.content or "").strip()
        return True, f"Connected. The model replied: {reply or '(empty)'}"
    except Exception as exc:
        text, low = str(exc), str(exc).lower()
        if "401" in text or "access denied" in low or "invalid api key" in low:
            hint = ("The API key is wrong. Copy it again from the Azure portal → your "
                    "resource → Keys and Endpoint → KEY 1.")
        elif "404" in text or "deploymentnotfound" in low.replace(" ", ""):
            hint = ("The endpoint and key work, but this resource has no deployment "
                    f"called {_cfg('AZURE_OPENAI_DEPLOYMENT')!r}. Take the endpoint, key "
                    "and deployment name from the same deployment page.")
        elif "connection" in low or "getaddrinfo" in low or "timed out" in low:
            hint = ("Could not reach the endpoint. Check the URL, and check the Azure "
                    "resource's Networking tab allows access from all networks — a "
                    "firewall there blocks Streamlit Cloud.")
        elif "429" in text or "quota" in low:
            hint = ("Rate limited or out of quota. Raise the tokens-per-minute limit on "
                    "the deployment, or wait and retry.")
        else:
            hint = "Re-check all three values against the Azure portal."
        return False, f"{type(exc).__name__}: {text[:200]}\n\n{hint}"


def azure_configured() -> bool:
    return all(_cfg(k) for k in AZURE_KEYS)


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


def _azure_create(client, messages, max_tokens, *, stream=False, temperature=0.3,
                  response_format=None, reasoning_effort=None):
    """Call the deployment, adapting to whichever parameter shape it accepts.

    `reasoning_effort` ("low"/"medium"/"high") only applies to GPT-5 / o-series
    deployments; it is dropped automatically if the deployment rejects it.
    """
    deployment = _cfg("AZURE_OPENAI_DEPLOYMENT")
    base = {"model": deployment, "messages": messages, "stream": stream}
    if response_format:
        base["response_format"] = response_format

    shapes = [
        {"max_completion_tokens": max_tokens, "temperature": temperature},
        {"max_completion_tokens": max_tokens},          # GPT-5 / o-series
        {"max_tokens": max_tokens, "temperature": temperature},
        {"max_tokens": max_tokens},                     # oldest deployments
    ]
    if reasoning_effort:
        # Try the reasoning-capable shapes first, then the same shapes without it.
        shapes = [{"max_completion_tokens": max_tokens,
                   "reasoning_effort": reasoning_effort}] + shapes

    # Reuse the shape that worked last time for this deployment.
    key = (deployment, bool(reasoning_effort))
    order = list(range(len(shapes)))
    if key in _WORKING_SHAPE:
        first = _WORKING_SHAPE[key]
        if first < len(shapes):
            order = [first] + [i for i in order if i != first]

    last_error = None
    for index in order:
        try:
            result = client.chat.completions.create(**base, **shapes[index])
            _WORKING_SHAPE[key] = index
            return result
        except Exception as exc:
            last_error = exc
            message = str(exc).lower()
            # Only keep trying when the complaint is about the parameters
            # themselves; a bad key or missing deployment should surface at once.
            if not any(hint in message for hint in _PARAM_ERROR_HINTS):
                raise
    raise last_error


# ------------------------------------------------------------------ streaming

def attach_images(message: dict, images: list[bytes], mime: str = "image/png") -> dict:
    """Return a copy of `message` carrying images alongside its text.

    Produces the multimodal content-part shape both providers understand, so a
    caller can hand the model a chart or a scanned page to look at.
    """
    if not images:
        return message
    text = message.get("content") or ""
    parts = [{"type": "text", "text": text}] if isinstance(text, str) else list(text)
    for data in images:
        b64 = base64.b64encode(data).decode("ascii")
        parts.append({"type": "image_url",
                      "image_url": {"url": f"data:{mime};base64,{b64}"}})
    return {**message, "content": parts}


def _to_anthropic(message: dict) -> dict:
    """Translate multimodal content parts into Anthropic's block shape."""
    content = message.get("content")
    if isinstance(content, str):
        return message
    blocks = []
    for part in content:
        if part.get("type") == "text":
            blocks.append({"type": "text", "text": part["text"]})
        elif part.get("type") == "image_url":
            url = part["image_url"]["url"]
            if url.startswith("data:"):
                header, _, data = url.partition(",")
                media = header[5:].split(";")[0] or "image/png"
                blocks.append({"type": "image",
                               "source": {"type": "base64", "media_type": media,
                                          "data": data}})
    return {**message, "content": blocks}


def stream(messages: list[dict], system: str, max_tokens: int = 4000,
           reasoning_effort: str | None = None):
    """Yield text chunks from the active provider.

    `messages` uses the shared shape [{"role": "user"|"assistant", "content": str}].
    `content` may also be a list of content parts (see `attach_images`) to send
    pictures as well as text.

    On reasoning deployments `max_tokens` covers reasoning *and* output, so a long
    prompt with a small budget can return nothing at all — pass a generous budget,
    and `reasoning_effort="low"` where the task is structured rather than hard.
    """
    provider = active_provider()

    if provider == "azure":
        client = _azure_client()
        payload = [{"role": "system", "content": system}] + messages
        response = _azure_create(client, payload, max_tokens, stream=True,
                                 reasoning_effort=reasoning_effort)
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    elif provider == "anthropic":
        client = _anthropic_client()
        with client.messages.stream(
            model=ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[_to_anthropic(m) for m in messages],
        ) as s:
            for text in s.text_stream:
                yield text

    else:
        raise RuntimeError("No AI provider configured")


def complete(prompt: str, system: str, max_tokens: int = 2000,
             reasoning_effort: str | None = None) -> str:
    """Non-streaming completion, returned as one string."""
    return "".join(stream([{"role": "user", "content": prompt}], system, max_tokens,
                          reasoning_effort=reasoning_effort))


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
    # Grab the outermost object or array.
    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = text.find(opener), text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                continue
    # Last resort — the output was probably truncated mid-array (reasoning models
    # can exhaust the token budget). Salvage every complete object we can find.
    salvaged = _salvage_objects(text)
    if salvaged:
        return salvaged
    raise ValueError("model did not return usable JSON")


def _salvage_objects(text: str) -> list:
    """Extract every complete {...} object from possibly-truncated JSON text.

    Handles the typical truncation shape '{"views": [{...}, {...}, {"par…' where
    the outer wrapper never closes: each complete inner object is recovered.
    """
    spans = []          # (start, end) of every balanced {...}
    stack = []          # indices of currently-open braces
    in_string = escape = False
    for i, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            stack.append(i)
        elif ch == "}" and stack:
            spans.append((stack.pop(), i + 1))

    # Keep only outermost complete spans (drop objects nested inside another).
    spans.sort()
    objects, last_end = [], -1
    for start, end in spans:
        if start >= last_end:
            try:
                obj = json.loads(text[start:end])
                if isinstance(obj, dict):
                    objects.append(obj)
                    last_end = end
            except json.JSONDecodeError:
                pass

    # A single wrapper like {"views": [...]} unwraps to the inner list.
    if len(objects) == 1 and len(objects[0]) == 1:
        inner = next(iter(objects[0].values()))
        if isinstance(inner, list):
            return inner
    return objects


def complete_json(prompt: str, system: str, max_tokens: int = 4000,
                  reasoning_effort: str | None = None):
    """Completion parsed as JSON. Uses native JSON mode on Azure where available."""
    provider = active_provider()
    system = system + "\n\nRespond with valid JSON only — no prose, no code fences."

    if provider == "azure":
        client = _azure_client()
        payload = [{"role": "system", "content": system},
                   {"role": "user", "content": prompt}]
        try:
            response = _azure_create(client, payload, max_tokens, temperature=0.1,
                                     response_format={"type": "json_object"},
                                     reasoning_effort=reasoning_effort)
        except Exception:
            # Some deployments reject response_format; retry without it and lean
            # on _extract_json to cope with any wrapping prose.
            response = _azure_create(client, payload, max_tokens, temperature=0.1,
                                     reasoning_effort=reasoning_effort)
        return _extract_json(response.choices[0].message.content or "")

    return _extract_json(complete(prompt, system, max_tokens))
