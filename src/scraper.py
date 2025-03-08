#!/usr/bin/env python3
"""
JailJawn Scraper - A modern web scraper for Philadelphia prison data.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class JailJawnScraper:
    """Scraper for Philadelphia prison data."""
    
    BASE_URL = "https://www.phila.gov/departments/philadelphia-department-of-prisons/daily-headcount-and-census/"
    
    def __init__(self):
        """Initialize the scraper with the data directory path."""
        self.data_dir = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)

    def fetch_page(self) -> Optional[str]:
        """
        Fetch the webpage content.
        
        Returns:
            str: HTML content of the page
        """
        try:
            headers = {
                "User-Agent": "JailJawn Scraper/1.0 (https://github.com/yourusername/jailjawn)"
            }
            response = requests.get(self.BASE_URL, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch page: {e}")
            return None

    def _convert_value(self, value: str) -> Union[int, str]:
        """Convert string values to integers where appropriate."""
        if value == '-':
            return 0
        try:
            # Remove commas from numbers
            cleaned_value = value.replace(',', '')
            return int(cleaned_value)
        except ValueError:
            return value.strip()

    def _extract_table_data(self, table: BeautifulSoup) -> List[Dict[str, Any]]:
        """Helper method to extract data from a table."""
        data = []
        headers = [th.text.strip() for th in table.find_all('th')]
        
        for row in table.find_all('tr')[1:]:  # Skip header row
            cells = [self._convert_value(td.text.strip()) for td in row.find_all('td')]
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
        """
        Parse the HTML content and extract relevant data.
        
        Args:
            html_content (str): Raw HTML content
            
        Returns:
            dict: Extracted data
        """
        soup = BeautifulSoup(html_content, 'html.parser')
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
                "total_population": []
            }
        }
        
        try:
            # Extract census date
            date_text = soup.find('p', string=lambda text: text and 'Census for:' in text)
            if date_text:
                raw_date = date_text.text.replace('Census for:', '').strip()
                data["census_date"] = self._convert_date_to_iso(raw_date)

            # Find all tables by their preceding headers
            tables = soup.find_all('table')
            headers = soup.find_all(['h2', 'h3'])
            
            for header in headers:
                if not header.find_next('table'):
                    continue
                    
                table = header.find_next('table')
                header_text = header.text.strip().lower()
                
                if 'in facility' in header_text and 'not' not in header_text:
                    data["facilities"]["in_facility"] = self._extract_table_data(table)
                elif 'temporarily not in facility' in header_text:
                    data["facilities"]["temporarily_not_in_facility"] = self._extract_table_data(table)
                elif 'pdp facility totals' in header_text:
                    data["facilities"]["facility_totals"] = self._extract_table_data(table)
                elif 'other jurisdictions' in header_text:
                    data["facilities"]["other_jurisdictions"] = self._extract_table_data(table)
                elif 'pdp total population' in header_text:
                    data["facilities"]["total_population"] = self._extract_table_data(table)
            
            return data
        except Exception as e:
            logger.error(f"Failed to parse data: {e}")
            return data

    def save_data(self, data: Dict[str, Any]) -> None:
        """
        Save the scraped data to a JSON file.
        
        Args:
            data (dict): Data to save
        """
        if not data["census_date"]:
            logger.error("No census date found, using scrape date for filename")
            file_path = self.data_dir / f"{data['scrape_date']}.json"
        else:
            file_path = self.data_dir / f"{data['census_date']}.json"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Data saved successfully to {file_path}")
        except IOError as e:
            logger.error(f"Failed to save data: {e}")

    def run(self) -> bool:
        """
        Execute the scraping process.
        
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info("Starting scraping process...")
        
        html_content = self.fetch_page()
        if not html_content:
            return False
        
        data = self.parse_data(html_content)
        self.save_data(data)
        
        logger.info("Scraping process completed successfully")
        return True

def main():
    """Main entry point for the scraper."""
    scraper = JailJawnScraper()
    success = scraper.run()
    exit(0 if success else 1)

if __name__ == "__main__":
    main() 