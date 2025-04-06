# JailJawn Scraper

This project scrapes daily inmate census data from the Philadelphia Department of Prisons website. It uses Python, Playwright (for fetching dynamic content), and BeautifulSoup (for parsing HTML) to collect the data and save it as JSON files.

## Project Goal

The primary goal of this project is to automatically collect and store historical inmate census data for Philadelphia, making it accessible for analysis and visualization to understand trends over time.

## How it Works

1. **Fetching**: The scraper uses `Playwright` to load the target webpage ([Philadelphia Department of Prisons - Daily Headcount and Census](https://www.phila.gov/departments/philadelphia-department-of-prisons/daily-headcount-and-census/)). Playwright handles any JavaScript execution required to render the full page content.
2. **Parsing**: Once the page is loaded, `BeautifulSoup` parses the HTML structure.
3. **Data Extraction**: The scraper identifies relevant tables and extracts the census data.
4. **Storage**: The extracted data is saved into a JSON file named with the date of the census (e.g., `YYYY-MM-DD.json`) in the `data/` directory.
5. **Automation**: A GitHub Actions workflow (`.github/workflows/scrape.yml`) is configured to run the scraper automatically on a schedule (daily at 12:00 UTC) and commit the new data back to the repository.

## Core Dependencies

This project relies on the following key Python libraries:

- `playwright`: For browser automation and fetching dynamically rendered web pages.
- `beautifulsoup4`: For parsing HTML content and extracting data.
- `python-dotenv`: For managing environment variables.

The full list of dependencies can be found in `requirements.txt`.

## Setup

To run the scraper locally, follow these steps:

1. **Clone the repository:**

   ```bash
   git clone https://github.com/ST215/JailJawn.git
   cd JailJawn
   ```

2. **Create and activate a virtual environment:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers:**
   ```bash
   playwright install chromium
   ```

## Usage

To run the scraper manually:

```bash
python src/scraper.py
```

The script will:

- Fetch the latest data from the website
- Save the data in the `data/` directory
- Save debug information (HTML snapshot and screenshot) in the `debug/` directory

## Data Storage

The scraper saves data in the following structure:

- `data/`: Contains JSON files with census data, named by date (e.g., `2024-04-06.json`)
- `debug/`: Contains HTML snapshots and screenshots for debugging purposes

## Contributing

Contributions are welcome! If you find issues or have suggestions for improvements, please feel free to:

1. **Open an issue:** Describe the bug or enhancement request.
2. **Submit a pull request:** Fork the repository, make your changes on a feature branch, and submit a pull request for review.

## Contact

For questions or comments, you can reach out to Stanley Griggs:

- Website: [http://www.StanleyGriggs.com/](http://www.StanleyGriggs.com/)
- Twitter: [@ST215](http://www.twitter.com/ST215)

---

_Previous project information (may be outdated):_

_The project initially involved deploying the scraper to AWS Lambda and storing data in Google Firebase, with a separate API and web app. These components are not part of the current simplified setup in this repository but may exist in related repositories:_

- _API: https://github.com/JailJawn/JailJawnAPI_
- _WebApp / Site: https://github.com/JailJawn/jailjawnapp_

# Jail Jawn

Data Source: (http://www.phila.gov/prisons/page.htm)

## What is Jail Jawn and Why?

This is the repository for the JailJawn.com scraper code written in Python. This started as a project to learn Python and Serverless deployment.

The following code in the repository accesses the static page provided by The City of Philadelphia Department of Prisons Census page (http://www.phila.gov/prisons/page.htm). This web page is generated internally possible by a human at infrequent times using Excel to HTML which doesn't create clean tables for scraping which requires a custom solution which as been implemented.

The Python code is deployed to Amazon Web Services Lambda running on a daily CRON job. Once the data is scraped via AWS Lambda it is pushed to our Google Firebase instance for permanent storage.

From the Google Firebase instance, we use Heroku to push the data API to the web using Javascript to render the charts on the client side.

The repositories for the those are located here:
API: https://github.com/JailJawn/JailJawnAPI
WebApp / Site: https://github.com/JailJawn/jailjawnapp

Any questions I can be found on
Website: http://www.StanleyGriggs.com/

Twitter: http://www.twitter.com/ST215

Feel free to make issue tickets and suggestions.

## Goal

Historical Inmate Data, Beautiful Charts, and The Ability see trends over time.

## Tech:

Python Requests (http://docs.python-requests.org/en/latest/)
Python lxml (http://lxml.de/)

## Steps to run on Windows

#### Download Python

    1. http://docs.python-requests.org/en/latest/user/install/#install

#### Set up Python Path

    1. Open Control Panel
    2. Go To Security and Systems
    3. Go to System
    4. Open Advanced System Settings
    5. Go to the "Advanced" tab and open Environmental Variables
    6. Scoll down to "Path" in System Variables and then double-click
    7. Add the local address of your Python library to the Variable Value field (For example: C:\Python27)
    	-If there are any other paths in the field then seperate them with a semicolon (For example C:\Java_lib;C:\Python27)

####Download Requests

    1. clone git://github.com/kennethreitz/requests.git
    2. Open terminal and run python setup.py install

#### Download lxml

    1. https://pypi.python.org/pypi/lxml/3.2.3
