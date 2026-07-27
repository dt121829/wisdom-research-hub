"""Visit the deployed app with a real browser so Streamlit Cloud counts it as traffic.

Streamlit Community Cloud puts apps to sleep after 12 hours without traffic. A plain
HTTP request does NOT count — the server returns 200 while the app stays asleep, because
Streamlit measures real browser sessions (websocket connections), not page fetches.
So this uses headless Chromium, and clicks the wake button if the app is already asleep.

Run by .github/workflows/keep-awake.yml on a schedule.
"""

import os
import sys

from playwright.sync_api import sync_playwright

WAKE_BUTTON = "Yes, get this app back up!"


def main() -> int:
    url = os.environ.get("APP_URL", "").strip()
    if not url:
        print("APP_URL is not set. Add it in your GitHub repository under "
              "Settings > Secrets and variables > Actions > Variables.")
        return 1

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        print(f"Visiting {url}")
        page.goto(url, timeout=120_000, wait_until="domcontentloaded")

        # If the app was asleep, Streamlit shows a wake button instead of the app.
        try:
            button = page.get_by_role("button", name=WAKE_BUTTON)
            if button.is_visible(timeout=8_000):
                print("App was asleep - clicking the wake button.")
                button.click()
                page.wait_for_timeout(90_000)  # wake-up takes up to ~90s
        except Exception:
            pass  # button absent means the app was already awake

        # Hold the session open briefly so the visit registers as real traffic.
        page.wait_for_timeout(15_000)
        print(f"Done. Page title: {page.title()}")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
