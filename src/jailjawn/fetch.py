"""Fetch the rendered census page with a headless browser.

The city page is a WordPress shell whose census tables are rendered
client-side by a small Vue app. Plain HTTP returns no tables, so a browser
is required. The browser is told to abort third-party analytics and
trackers, which are not needed to render the census and which otherwise
keep the network busy indefinitely.
"""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from jailjawn import SOURCE_URL

log = logging.getLogger(__name__)

# Hosts the page loads that play no part in rendering the census.
BLOCKED_HOSTS = (
    "googletagmanager.com",
    "google-analytics.com",
    "analytics.google.com",
    "clarity.ms",
    "bing.com",
    "jam.dev",
    "translate.google.com",
    "translate.googleapis.com",
    "formstack.com",
    "code.highcharts.com",
)

# The Vue app renders an empty table skeleton, with today's date as a
# placeholder, before its census request returns. A cell whose entire text
# is a number proves the data has arrived. (Merely containing a digit is not
# enough: the facility name "RCF ASDMOD3" contains one.)
CENSUS_LOADED_JS = """() => {
    const cells = document.querySelectorAll('#vue-app table td');
    return Array.from(cells).some(
        td => /^[0-9][0-9,]*$/.test(td.textContent.trim())
    );
}"""

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 JailJawn/2"
)


def _is_blocked(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return any(host == h or host.endswith("." + h) for h in BLOCKED_HOSTS)


async def _fetch_once(url: str, timeout_ms: int) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        try:
            context = await browser.new_context(
                viewport={"width": 1280, "height": 900}, user_agent=USER_AGENT
            )

            async def route_handler(route, request):
                if _is_blocked(request.url):
                    await route.abort()
                else:
                    await route.continue_()

            await context.route("**/*", route_handler)
            page = await context.new_page()
            page.on("pageerror", lambda err: log.warning("page error: %s", err))

            log.info("loading %s", url)
            response = await page.goto(
                url, wait_until="domcontentloaded", timeout=timeout_ms
            )
            if response is None or response.status != 200:
                status = response.status if response else "no response"
                raise RuntimeError(f"page returned {status}")

            await page.wait_for_function(CENSUS_LOADED_JS, timeout=timeout_ms)
            return await page.content()
        finally:
            await browser.close()


async def fetch_page_async(
    url: str = SOURCE_URL,
    *,
    attempts: int = 3,
    timeout_ms: int = 30_000,
    retry_delay_s: float = 20.0,
) -> str:
    """Return the page HTML once the census has rendered, retrying on failure."""
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await _fetch_once(url, timeout_ms)
        except Exception as exc:  # noqa: BLE001 - any failure is retried
            last_error = exc
            log.warning("fetch attempt %d of %d failed: %s", attempt, attempts, exc)
            if attempt < attempts:
                await asyncio.sleep(retry_delay_s)
    raise RuntimeError(
        f"could not fetch census after {attempts} attempts"
    ) from last_error


def fetch_page(url: str = SOURCE_URL, **kwargs) -> str:
    """Synchronous wrapper around :func:`fetch_page_async`."""
    return asyncio.run(fetch_page_async(url, **kwargs))
