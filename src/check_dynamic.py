"""Script to check for dynamically loaded content on the prison census page."""

import asyncio

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


async def check_dynamic_content():
    """Check for dynamically loaded content using Playwright."""
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Enable request interception
        await page.route("**/*", lambda route: route.continue_())

        print("Loading page...")
        await page.goto(
            "https://www.phila.gov/departments/philadelphia-department-of-prisons/daily-headcount-and-census/"
        )

        # Wait for any dynamic content
        await page.wait_for_load_state("networkidle")

        # Get all network requests
        requests = await page.evaluate(
            """() => {
            return window.performance.getEntries().map(e => e.name);
        }"""
        )

        print("\nNetwork Requests:")
        for req in requests:
            if "census" in req.lower() or "prison" in req.lower():
                print(f"Found request: {req}")

        # Get the final HTML content
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")

        # Check for iframes
        iframes = soup.find_all("iframe")
        print(f"\nFound {len(iframes)} iframes:")
        for iframe in iframes:
            src = iframe.get("src", "No src")
            print(f"iframe src: {src}")
            if src:
                # Navigate to iframe source if it's interesting
                if "census" in src.lower() or "prison" in src.lower():
                    print(f"Checking iframe content: {src}")
                    await page.goto(src)
                    iframe_content = await page.content()
                    iframe_soup = BeautifulSoup(iframe_content, "html.parser")
                    tables = iframe_soup.find_all("table")
                    print(f"Found {len(tables)} tables in iframe")
                    for table in tables:
                        print(
                            f"Table headers: {[th.text.strip() for th in table.find_all('th')]}"
                        )

        # Check for tables in main document
        tables = soup.find_all("table")
        print(f"\nFound {len(tables)} tables in main document:")
        for table in tables:
            headers = [th.text.strip() for th in table.find_all("th")]
            print(f"Table headers: {headers}")

        # Check for interesting elements
        for element in soup.find_all(["div", "iframe", "embed"]):
            for attr in ["id", "class", "src", "data-src"]:
                value = element.get(attr, "")
                if value and ("census" in value.lower() or "prison" in value.lower()):
                    print(f"\nFound interesting element:")
                    print(f"Tag: {element.name}")
                    print(f"Attributes: {element.attrs}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(check_dynamic_content())
