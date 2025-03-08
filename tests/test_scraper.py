"""Tests for the JailJawn scraper."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from bs4 import BeautifulSoup

from src.scraper import JailJawnScraper

@pytest.fixture
def scraper():
    """Create a scraper instance for testing."""
    return JailJawnScraper()

@pytest.fixture
def sample_table_html():
    """Create a sample table HTML for testing."""
    return """
    <table>
        <thead>
            <tr>
                <th>Facility</th>
                <th>Males</th>
                <th>Females</th>
                <th>Total</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Test Facility</td>
                <td>100</td>
                <td>50</td>
                <td>150</td>
            </tr>
        </tbody>
    </table>
    """

def test_scraper_initialization(scraper):
    """Test that the scraper initializes correctly."""
    assert isinstance(scraper, JailJawnScraper)
    assert scraper.data_dir.exists()

@patch('requests.get')
def test_fetch_page_success(mock_get, scraper):
    """Test successful page fetch."""
    mock_response = MagicMock()
    mock_response.text = "<html><body>Test content</body></html>"
    mock_get.return_value = mock_response
    
    result = scraper.fetch_page()
    assert result == mock_response.text
    mock_get.assert_called_once()

@patch('requests.get')
def test_fetch_page_failure(mock_get, scraper):
    """Test failed page fetch."""
    mock_get.side_effect = Exception("Connection error")
    result = scraper.fetch_page()
    assert result is None

def test_extract_table_data(scraper, sample_table_html):
    """Test table data extraction."""
    soup = BeautifulSoup(sample_table_html, 'html.parser')
    table = soup.find('table')
    result = scraper._extract_table_data(table)
    
    expected = [{
        'Facility': 'Test Facility',
        'Males': '100',
        'Females': '50',
        'Total': '150'
    }]
    
    assert result == expected

def test_convert_date_to_iso(scraper):
    """Test date conversion to ISO 8601 format."""
    test_cases = [
        ("March 06, 2024", "2024-03-06"),
        ("January 1, 2024", "2024-01-01"),
        ("December 31, 2023", "2023-12-31"),
    ]
    
    for input_date, expected in test_cases:
        result = scraper._convert_date_to_iso(input_date)
        assert result == expected

def test_convert_date_to_iso_invalid(scraper):
    """Test date conversion with invalid input."""
    result = scraper._convert_date_to_iso("Invalid Date")
    assert result == ""

def test_parse_data_basic(scraper):
    """Test basic data parsing."""
    html_content = f"""
    <html>
        <body>
            <p>Census for: March 06, 2024</p>
            {sample_table_html}
        </body>
    </html>
    """
    data = scraper.parse_data(html_content)
    
    assert isinstance(data, dict)
    assert "timestamp" in data
    assert "census_date" in data
    assert "facilities" in data
    assert data["census_date"] == "2024-03-06"
    assert isinstance(data["facilities"], dict)
    
    # Verify ISO 8601 format
    datetime.fromisoformat(data["timestamp"])  # Should not raise exception
    datetime.fromisoformat(data["scrape_date"])  # Should not raise exception

def test_save_data(tmp_path, scraper):
    """Test data saving functionality."""
    # Temporarily change data directory to test directory
    scraper.data_dir = tmp_path
    
    test_data = {
        "timestamp": "2024-02-29T12:00:00",
        "scrape_date": "2024-02-29",
        "census_date": "2024-03-06",
        "facilities": {
            "in_facility": [],
            "temporarily_not_in_facility": [],
            "facility_totals": [],
            "other_jurisdictions": [],
            "total_population": []
        }
    }
    
    scraper.save_data(test_data)
    
    # Check if file was created with ISO date format
    expected_filename = "2024-03-06.json"
    assert (tmp_path / expected_filename).exists()
    
    # Verify content
    with open(tmp_path / expected_filename, 'r') as f:
        saved_data = json.load(f)
    assert saved_data == test_data 