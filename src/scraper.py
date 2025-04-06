#!/usr/bin/env python3
"""
JailJawn Scraper - A modern web scraper for Philadelphia prison data.
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from bs4 import BeautifulSoup, Comment
from playwright.async_api import async_playwright
import requests

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class JailJawnScraper:
    """Scraper for Philadelphia prison data."""

    BASE_URL = "https://www.phila.gov/departments/philadelphia-department-of-prisons/daily-headcount-and-census/"

    def __init__(self):
        """Initialize the scraper with the data directory path."""
        self.data_dir = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)

    async def fetch_page(self) -> Optional[str]:
        """
        Fetch the webpage content using Playwright to handle dynamic content.

        Returns:
            str: HTML content of the page after JavaScript execution
        """
        try:
            async with async_playwright() as p:
                # Launch browser with more debugging
                browser = await p.chromium.launch(
                    headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"]
                )

                # Create context with more realistic browser settings
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                )

                # Create page and set up error handling
                page = await context.new_page()

                # Listen for console messages
                page.on(
                    "console",
                    lambda msg: logger.debug(f"Browser console {msg.type}: {msg.text}"),
                )
                page.on(
                    "pageerror", lambda err: logger.error(f"Browser page error: {err}")
                )

                # Listen for all network requests
                async def handle_request(request):
                    logger.debug(f"Network request: {request.method} {request.url}")

                page.on("request", handle_request)

                async def handle_response(response):
                    logger.debug(f"Network response: {response.status} {response.url}")
                    if response.status != 200:
                        logger.warning(
                            f"Non-200 response: {response.status} {response.url}"
                        )

                page.on("response", handle_response)

                logger.info(f"Loading page from {self.BASE_URL}")

                # Navigate with more options
                try:
                    response = await page.goto(
                        self.BASE_URL,
                        wait_until="networkidle",
                        timeout=30000,  # 30 seconds
                    )
                    if not response:
                        logger.error("No response received from page")
                        return None
                    if response.status != 200:
                        logger.error(f"Bad response status: {response.status}")
                        return None

                    # Wait for potential dynamic content
                    await page.wait_for_load_state("networkidle")
                    await page.wait_for_load_state("domcontentloaded")

                    # Try to find any tables
                    table_count = await page.locator("table").count()
                    logger.info(f"Found {table_count} tables in page")

                    # Log interesting elements
                    for selector in [
                        "table",
                        "iframe",
                        '[id*="census"]',
                        '[class*="census"]',
                        '[id*="prison"]',
                        '[class*="prison"]',
                    ]:
                        elements = await page.locator(selector).all()
                        logger.info(
                            f"Found {len(elements)} elements matching '{selector}'"
                        )

                    # Get the final HTML content
                    content = await page.content()

                    # Save HTML for debugging
                    debug_path = Path(__file__).parent.parent / "debug"
                    debug_path.mkdir(exist_ok=True)
                    debug_file = (
                        debug_path
                        / f"page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                    )
                    debug_file.write_text(content, encoding="utf-8")
                    logger.info(f"Saved debug HTML to {debug_file}")

                    # Take screenshot for debugging
                    screenshot_path = (
                        debug_path
                        / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    )
                    await page.screenshot(path=str(screenshot_path))
                    logger.info(f"Saved screenshot to {screenshot_path}")

                    logger.info("Successfully fetched page content")
                    return content

                except Exception as e:
                    logger.error(f"Error during page load: {e}", exc_info=True)
                    return None
                finally:
                    await context.close()
                    await browser.close()

        except Exception as e:
            logger.error(f"Failed to fetch page: {e}", exc_info=True)
            return None

    def _convert_value(self, value: str) -> Union[int, str]:
        """Convert string values to integers where appropriate."""
        if value == "-":
            return 0
        try:
            # Remove commas from numbers
            cleaned_value = value.replace(",", "")
            return int(cleaned_value)
        except ValueError:
            return value.strip()

    def _extract_table_data(self, table: BeautifulSoup) -> List[Dict[str, Any]]:
        """Helper method to extract data from a table."""
        data = []
        headers = [th.text.strip() for th in table.find_all("th")]

        for row in table.find_all("tr")[1:]:  # Skip header row
            cells = [self._convert_value(td.text.strip()) for td in row.find_all("td")]
            if cells and len(cells) == len(headers):
                row_data = dict(zip(headers, cells))
                data.append(row_data)

        return data

    def _convert_date_to_iso(self, date_str: str) -> str:
        """
        Convert date string from 'Month DD, YYYY' to ISO 8601 format.

        Args:
            date_str (str): Date string in format 'Month DD, YYYY'

        Returns:
            str: Date in ISO 8601 format (YYYY-MM-DD)
        """
        try:
            parsed_date = datetime.strptime(date_str.strip(), "%B %d, %Y")
            return parsed_date.date().isoformat()
        except ValueError as e:
            logger.error(f"Failed to parse date '{date_str}': {e}")
            return ""

    def parse_data(self, html_content: str) -> Dict[str, Any]:
        """Parse the HTML content and extract relevant data."""
        soup = BeautifulSoup(html_content, "html.parser")
        now = datetime.now()
        data = {
            "timestamp": now.isoformat(),
            "scrape_date": now.date().isoformat(),
            "census_date": "",
            "facilities": {
                "in_facility": [],
                "temporarily_not_in_facility": [],
                "facility_totals": [],
                "other_jurisdictions": [],
                "total_population": [],
            },
        }

        try:
            # Log the full HTML for debugging
            logger.debug(f"Raw HTML content: {html_content[:1000]}...")

            # Extract census date - try different patterns
            date_patterns = [
                lambda s: s.find(
                    "p", string=lambda text: text and "Census for:" in text
                ),
                lambda s: s.find(string=lambda text: text and "Census for:" in text),
                lambda s: s.find(
                    "strong", string=lambda text: text and "Census" in text
                ),
                lambda s: s.find(
                    ["p", "div"], string=lambda text: text and "Census" in text
                ),
            ]

            for pattern in date_patterns:
                date_text = pattern(soup)
                if date_text:
                    logger.info(f"Found date text: {date_text}")
                    raw_date = (
                        date_text.text.replace("Census for:", "")
                        .replace("Census:", "")
                        .strip()
                    )
                    data["census_date"] = self._convert_date_to_iso(raw_date)
                    break

            # Find all potential table containers
            tables = soup.find_all("table")
            logger.info(f"Found {len(tables)} tables")

            # Try to find headers near tables
            headers = soup.find_all(["h2", "h3", "h4", "strong"])
            logger.info(f"Found {len(headers)} potential headers")

            for header in headers:
                header_text = header.text.strip().lower()
                logger.info(f"Processing header: {header_text}")

                # Find the closest table after this header
                table = header.find_next("table")
                if not table:
                    continue

                # Log table structure for debugging
                logger.debug(
                    f"Table headers: {[th.text.strip() for th in table.find_all('th')]}"
                )

                if "in facility" in header_text and "not" not in header_text:
                    data["facilities"]["in_facility"] = self._extract_table_data(table)
                    logger.info(
                        f"Extracted in_facility data: {len(data['facilities']['in_facility'])} rows"
                    )
                elif "temporarily not in facility" in header_text:
                    data["facilities"]["temporarily_not_in_facility"] = (
                        self._extract_table_data(table)
                    )
                    logger.info(
                        f"Extracted temporarily_not_in_facility data: {len(data['facilities']['temporarily_not_in_facility'])} rows"
                    )
                elif (
                    "pdp facility totals" in header_text
                    or "facility totals" in header_text
                ):
                    data["facilities"]["facility_totals"] = self._extract_table_data(
                        table
                    )
                    logger.info(
                        f"Extracted facility_totals data: {len(data['facilities']['facility_totals'])} rows"
                    )
                elif "other jurisdictions" in header_text:
                    data["facilities"]["other_jurisdictions"] = (
                        self._extract_table_data(table)
                    )
                    logger.info(
                        f"Extracted other_jurisdictions data: {len(data['facilities']['other_jurisdictions'])} rows"
                    )
                elif "total population" in header_text:
                    data["facilities"]["total_population"] = self._extract_table_data(
                        table
                    )
                    logger.info(
                        f"Extracted total_population data: {len(data['facilities']['total_population'])} rows"
                    )

            # If we didn't find any data, try a more aggressive approach
            if not any(data["facilities"].values()):
                logger.warning(
                    "No data found with header matching, trying direct table analysis"
                )
                for table in tables:
                    headers = [th.text.strip().lower() for th in table.find_all("th")]
                    logger.info(f"Found table with headers: {headers}")

                    if any("adult males" in h for h in headers):
                        data["facilities"]["in_facility"] = self._extract_table_data(
                            table
                        )
                    elif any("workers" in h for h in headers):
                        data["facilities"]["temporarily_not_in_facility"] = (
                            self._extract_table_data(table)
                        )
                    elif (
                        "males" in headers
                        and "females" in headers
                        and "total" in headers
                    ):
                        if not data["facilities"]["facility_totals"]:
                            data["facilities"]["facility_totals"] = (
                                self._extract_table_data(table)
                            )
                    elif "jurisdiction" in headers:
                        data["facilities"]["other_jurisdictions"] = (
                            self._extract_table_data(table)
                        )
                    elif len(headers) == 2 and "count" in headers:
                        data["facilities"]["total_population"] = (
                            self._extract_table_data(table)
                        )

            return data
        except Exception as e:
            logger.error(f"Failed to parse data: {e}", exc_info=True)
            return data

    def save_data(self, data: Dict[str, Any]) -> None:
        """Save the scraped data to a JSON file."""
        if not data["census_date"]:
            logger.error("No census date found, using scrape date for filename")
            file_path = self.data_dir / f"{data['scrape_date']}.json"
        else:
            file_path = self.data_dir / f"{data['census_date']}.json"

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Data saved successfully to {file_path}")
        except IOError as e:
            logger.error(f"Failed to save data: {e}")

    async def run(self) -> bool:
        """Execute the scraping process."""
        logger.info("Starting scraping process...")

        html_content = await self.fetch_page()
        if not html_content:
            return False

        data = self.parse_data(html_content)
        self.save_data(data)

        logger.info("Scraping process completed successfully")
        return True


def main():
    """Main entry point for the scraper."""
    scraper = JailJawnScraper()
    success = asyncio.run(scraper.run())
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
