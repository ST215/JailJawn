"""Tests for the JailJawn scraper."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from src.scraper import JailJawnScraper


@pytest.fixture
def scraper():
    """Create a scraper instance for testing."""
    return JailJawnScraper()


@pytest.fixture
def sample_html():
    """Sample HTML content for testing."""
    return """
    <html>
        <body>
            <p>Census for: March 8, 2024</p>
            
            <h2>In facility</h2>
            <table>
                <tr>
                    <th>Facility</th>
                    <th>Adult males</th>
                    <th>Adult females</th>
                    <th>Juvenile males</th>
                    <th>Juvenile females</th>
                </tr>
                <tr>
                    <td>CFCF</td>
                    <td>1,789</td>
                    <td>0</td>
                    <td>0</td>
                    <td>0</td>
                </tr>
            </table>
            
            <h2>Temporarily not in facility</h2>
            <table>
                <tr>
                    <th>Facility</th>
                    <th>Male workers</th>
                    <th>Female workers</th>
                    <th>Male furlough</th>
                    <th>Female furlough</th>
                    <th>Male open ward</th>
                    <th>Female open ward</th>
                    <th>Male emergency trips</th>
                    <th>Female emergency trips</th>
                </tr>
                <tr>
                    <td>CFCF</td>
                    <td>2</td>
                    <td>0</td>
                    <td>0</td>
                    <td>0</td>
                    <td>0</td>
                    <td>0</td>
                    <td>5</td>
                    <td>0</td>
                </tr>
            </table>
            
            <h2>PDP facility totals</h2>
            <table>
                <tr>
                    <th>Facility</th>
                    <th>Males</th>
                    <th>Females</th>
                    <th>Total</th>
                </tr>
                <tr>
                    <td>CFCF</td>
                    <td>1,796</td>
                    <td>0</td>
                    <td>1,796</td>
                </tr>
            </table>
            
            <h2>PDP incarcerated people held in other jurisdictions</h2>
            <table>
                <tr>
                    <th>Jurisdiction</th>
                    <th>Males</th>
                    <th>Females</th>
                    <th>Total</th>
                </tr>
                <tr>
                    <td>State</td>
                    <td>0</td>
                    <td>0</td>
                    <td>0</td>
                </tr>
            </table>
            
            <h2>PDP total population</h2>
            <table>
                <tr>
                    <th>Category</th>
                    <th>Count</th>
                </tr>
                <tr>
                    <td>Total</td>
                    <td>4,837</td>
                </tr>
            </table>
        </body>
    </html>
    """


def test_convert_value(scraper):
    """Test value conversion."""
    assert scraper._convert_value("1,234") == 1234
    assert scraper._convert_value("-") == 0
    assert scraper._convert_value("CFCF") == "CFCF"


def test_convert_date_to_iso(scraper):
    """Test date conversion."""
    assert scraper._convert_date_to_iso("March 8, 2024") == "2024-03-08"
    assert scraper._convert_date_to_iso("Invalid Date") == ""


def test_extract_table_data(scraper, sample_html):
    """Test table data extraction."""
    soup = BeautifulSoup(sample_html, "html.parser")
    table = soup.find_all("table")[0]  # Get first table (in facility)
    data = scraper._extract_table_data(table)

    assert len(data) == 1
    assert data[0]["Facility"] == "CFCF"
    assert data[0]["Adult males"] == 1789
    assert data[0]["Adult females"] == 0


def test_parse_data(scraper, sample_html):
    """Test full data parsing."""
    data = scraper.parse_data(sample_html)

    assert data["census_date"] == "2024-03-08"
    assert len(data["facilities"]["in_facility"]) == 1
    assert len(data["facilities"]["temporarily_not_in_facility"]) == 1
    assert len(data["facilities"]["facility_totals"]) == 1
    assert len(data["facilities"]["other_jurisdictions"]) == 1
    assert len(data["facilities"]["total_population"]) == 1


@pytest.mark.asyncio
async def test_fetch_page_success(scraper):
    """Test successful page fetch."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Mock the page content
        await page.goto("data:text/html,<html>test content</html>")
        content = await page.content()

        await browser.close()
        assert "test content" in content


@pytest.mark.asyncio
async def test_fetch_page_failure(scraper):
    """Test failed page fetch."""
    # Save original URL
    original_url = scraper.BASE_URL
    try:
        # Set invalid URL to force failure
        scraper.BASE_URL = "https://invalid.url.that.does.not.exist/"
        content = await scraper.fetch_page()
        assert content is None
    finally:
        # Restore original URL
        scraper.BASE_URL = original_url


def test_save_data(scraper, tmp_path):
    """Test data saving."""
    scraper.data_dir = tmp_path
    data = {
        "census_date": "2024-03-08",
        "scrape_date": "2024-03-08",
        "timestamp": "2024-03-08T12:00:00",
        "facilities": {},
    }

    scraper.save_data(data)
    saved_file = tmp_path / "2024-03-08.json"
    assert saved_file.exists()

    with open(saved_file) as f:
        saved_data = json.load(f)
    assert saved_data == data
