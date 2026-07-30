"""Azure OpenAI connection checker.

Run this after filling in .streamlit/secrets.toml to confirm your Copilot
credentials work, before worrying about whether the app itself is at fault:

    .venv\\Scripts\\python.exe check_azure.py

It reads the same three settings the app uses, makes one very small API call,
and translates whatever comes back into plain English.
"""

import os
import sys
from pathlib import Path

SECRETS = Path(__file__).resolve().parent / ".streamlit" / "secrets.toml"
KEYS = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT")
DEFAULT_API_VERSION = "2025-04-01-preview"  # keep in step with services/llm.py

# Values that mean "not filled in yet" rather than a real setting.
PLACEHOLDER_MARKERS = ("PASTE_", "your-resource", "your-azure-key", "your-key-1-value")


def load_config() -> dict:
    """Read secrets.toml if present, letting real environment variables win."""
    cfg = {}
    if SECRETS.exists():
        try:
            import tomllib
            with SECRETS.open("rb") as fh:
                cfg.update(tomllib.load(fh))
        except Exception as exc:
            print(f"  !  Could not parse {SECRETS}: {exc}")
            print("     Check for a missing quote mark around one of the values.\n")
    for key in KEYS + ("AZURE_OPENAI_API_VERSION",):
        if os.environ.get(key):
            cfg[key] = os.environ[key]
    return cfg


def is_placeholder(value: str) -> bool:
    return any(marker in value for marker in PLACEHOLDER_MARKERS)


def mask(value: str) -> str:
    if not value:
        return "(empty)"
    if is_placeholder(value):
        return value  # show placeholders in full so they're obvious
    return value[:6] + "…" + value[-4:] if len(value) > 12 else "…" * len(value)


def main() -> int:
    print("\nAzure OpenAI connection check")
    print("=" * 60)
    print(f"secrets.toml: {'found' if SECRETS.exists() else 'NOT FOUND at ' + str(SECRETS)}")

    cfg = load_config()

    missing = [k for k in KEYS if not cfg.get(k)]
    unfilled = [k for k in KEYS if cfg.get(k) and is_placeholder(cfg[k])]

    print("\nSettings found:")
    for key in KEYS:
        val = cfg.get(key, "")
        shown = mask(val) if "KEY" in key else (val or "(empty)")
        if not val:
            status = "MISSING"
        elif is_placeholder(val):
            status = "TODO   "
        else:
            status = "OK     "
        print(f"  {status}  {key} = {shown}")

    if missing:
        print(f"\nFAILED: {len(missing)} setting(s) missing: {', '.join(missing)}")
        print("Copy .streamlit/secrets.toml.example to .streamlit/secrets.toml and fill it in.")
        return 1

    if unfilled:
        print(f"\nNOT READY: {len(unfilled)} value(s) still hold the placeholder text.")
        print(f"  {', '.join(unfilled)}")
        print(f"\nOpen this file and replace them with your real Azure values:")
        print(f"  {SECRETS}")
        print("\nFrom a terminal:  notepad .streamlit\\secrets.toml")
        print("\nWhere to find each value:")
        print("  ENDPOINT   Azure portal -> your Azure OpenAI resource -> Keys and Endpoint")
        print("  API_KEY    the same page -> KEY 1")
        print("  DEPLOYMENT ai.azure.com -> Deployments -> the name you gave your model")
        return 1

    endpoint = cfg["AZURE_OPENAI_ENDPOINT"].strip()
    if not endpoint.startswith("https://"):
        print(f"\n  !  Endpoint should start with https:// — got {endpoint!r}")
    if "/openai/deployments/" in endpoint or endpoint.rstrip("/").endswith("/chat/completions"):
        print("\n  !  Your endpoint looks like a full request URL. Use only the base, e.g.")
        print("     https://your-resource.openai.azure.com/")

    api_version = cfg.get("AZURE_OPENAI_API_VERSION", DEFAULT_API_VERSION)
    print(f"\nCalling deployment {cfg['AZURE_OPENAI_DEPLOYMENT']!r} "
          f"(api-version {api_version})…")

    try:
        from openai import AzureOpenAI
    except ImportError:
        print("FAILED: the openai package isn't installed in this environment.")
        print("Run: .venv\\Scripts\\python.exe -m pip install -r requirements.txt")
        return 1

    try:
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=cfg["AZURE_OPENAI_API_KEY"],
            api_version=api_version,
        )
        messages = [{"role": "user", "content": "Reply with exactly: connection ok"}]
        # GPT-5 / o-series want max_completion_tokens; GPT-4-era want max_tokens.
        try:
            response = client.chat.completions.create(
                model=cfg["AZURE_OPENAI_DEPLOYMENT"], messages=messages,
                max_completion_tokens=20)
        except Exception as first:
            if "max_completion_tokens" not in str(first).lower():
                raise
            response = client.chat.completions.create(
                model=cfg["AZURE_OPENAI_DEPLOYMENT"], messages=messages, max_tokens=20)
        reply = (response.choices[0].message.content or "").strip()
        print(f"\nSUCCESS — the model replied: {reply!r}")
        print("\nYour Copilot credentials work. Start the app and the sidebar will")
        print("show 'Copilot (Azure OpenAI · %s)'." % cfg["AZURE_OPENAI_DEPLOYMENT"])
        return 0

    except Exception as exc:
        text = str(exc)
        print(f"\nFAILED: {type(exc).__name__}")
        print(f"  {text[:400]}")
        print("\nWhat this usually means:")
        low = text.lower()
        if "401" in text or "access denied" in low or "invalid" in low and "key" in low:
            print("  - The API key is wrong. Copy it again from the Azure portal:")
            print("    your resource -> Keys and Endpoint -> KEY 1.")
        elif "deploymentnotfound" in low.replace(" ", "") or "404" in text \
                or "not found" in low or "does not exist" in low:
            print("  - Your endpoint and key reached Azure fine, but this resource has")
            print("    no deployment called %r." % cfg["AZURE_OPENAI_DEPLOYMENT"])
            print("    Go to https://ai.azure.com -> Deployments and copy the value in")
            print("    the 'Name' column EXACTLY (it is the name you chose, not the")
            print("    model name, and it is case-sensitive).")
            print("  - If the list is empty, the deployment is in a different resource:")
            print("    make sure the resource selected there matches the endpoint above.")
            print("  - If you only just created it, wait for its state to read 'Succeeded'.")
        elif "getaddrinfo" in low or "connection" in low or "resolve" in low:
            print("  - The endpoint URL is wrong or unreachable. It should look like")
            print("    https://your-resource.openai.azure.com/ with no extra path.")
        elif "429" in text or "quota" in low or "rate" in low:
            print("  - Rate limited or out of quota. Raise the tokens-per-minute limit")
            print("    on the deployment, or wait and retry.")
        elif "content" in low and "filter" in low:
            print("  - A content filter blocked the test message; the connection itself")
            print("    is probably fine.")
        else:
            print("  - Re-check all three values against the Azure portal.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
