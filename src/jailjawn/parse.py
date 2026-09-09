"""Turn the rendered census page into a census record.

Each of the five tables is identified by its exact header row, in page
order. That is the only thing the parser relies on. Headings are ignored:
the heading for "PDP facility totals" contains the phrase "temporarily not
in facility", which is how the v1 parser filed that table under the wrong
key for 497 days.

Cell values: a run of digits becomes an int, a dash becomes None (the page
prints "-" for an empty cell, which is not the same as zero), and anything
else is kept as stripped text. An empty cell stays an empty string so that
validation can recognise a page captured before its data loaded.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime

from bs4 import BeautifulSoup

from jailjawn import SOURCE_URL

SCHEMA_VERSION = 2

# The page leaves the first header of the total population table blank.
LABEL_FALLBACK = "Category"

# (record key, exact header row) for each table, in page order.
TABLES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "in_facility",
        (
            "Facility",
            "Adult males",
            "Adult females",
            "Juvenile males",
            "Juvenile females",
        ),
    ),
    (
        "temporarily_not_in_facility",
        (
            "Facility",
            "Male workers",
            "Female workers",
            "Male furlough",
            "Female furlough",
            "Male open ward",
            "Female open ward",
            "Male emergency trips",
            "Female emergency trips",
        ),
    ),
    ("facility_totals", ("Facility", "Males", "Females", "Total")),
    ("other_jurisdictions", ("Jurisdiction", "Males", "Females", "Total")),
    ("total_population", (LABEL_FALLBACK, "Males", "Females", "Total")),
)

TABLE_KEYS = tuple(key for key, _ in TABLES)
HEADERS_BY_KEY = {key: headers for key, headers in TABLES}
_KEY_BY_HEADERS = {headers: key for key, headers in TABLES}

_DATE_RE = re.compile(r"Census for:\s*([A-Za-z]+ \d{1,2}, \d{4})")
_INT_RE = re.compile(r"^\d{1,3}(,\d{3})*$|^\d+$")


def parse_cell(text: str) -> int | str | None:
    """Convert one table cell to its stored value."""
    text = text.strip()
    if text == "-":
        return None
    if text == "NaN":
        # Computed total cells before the census request returns.
        return ""
    if _INT_RE.match(text):
        return int(text.replace(",", ""))
    return text


def parse_census_date(text: str) -> date | None:
    """Find "Census for: Month DD, YYYY" in text and return the date."""
    match = _DATE_RE.search(text)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%B %d, %Y").date()
    except ValueError:
        return None


@dataclass
class ParsedPage:
    census_date: date | None
    tables: dict[str, list[dict]] = field(default_factory=dict)
    unrecognized: list[tuple[str, ...]] = field(default_factory=list)


def parse_page(html: str) -> ParsedPage:
    """Parse the rendered page. Missing tables are simply absent from ``tables``."""
    soup = BeautifulSoup(html, "html.parser")
    app = soup.find(id="vue-app") or soup

    parsed = ParsedPage(census_date=parse_census_date(app.get_text(" ")))

    for table in app.find_all("table"):
        headers = tuple(
            th.get_text(" ", strip=True) or LABEL_FALLBACK
            for th in table.find_all("th")
        )
        key = _KEY_BY_HEADERS.get(headers)
        if key is None or key in parsed.tables:
            parsed.unrecognized.append(headers)
            continue
        rows = []
        for tr in table.find_all("tr"):
            cells = tr.find_all("td")
            if not cells:
                continue
            values = [parse_cell(td.get_text(" ", strip=True)) for td in cells]
            if len(values) != len(headers):
                parsed.unrecognized.append(headers)
                break
            rows.append(dict(zip(headers, values)))
        parsed.tables[key] = rows

    return parsed


def build_record(parsed: ParsedPage, *, scraped_at: datetime) -> dict:
    """Assemble the JSON document stored for one census day."""
    return {
        "schema_version": SCHEMA_VERSION,
        "timestamp": scraped_at.isoformat(timespec="seconds"),
        "scrape_date": scraped_at.date().isoformat(),
        "census_date": parsed.census_date.isoformat() if parsed.census_date else "",
        "source_url": SOURCE_URL,
        "facilities": {key: parsed.tables.get(key, []) for key in TABLE_KEYS},
    }


def parse_html(html: str, *, scraped_at: datetime | None = None) -> dict:
    """Convenience: HTML in, record out."""
    return build_record(parse_page(html), scraped_at=scraped_at or datetime.now())
