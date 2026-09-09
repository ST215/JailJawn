import json
from datetime import date
from pathlib import Path

import pytest

from jailjawn.parse import parse_html

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def census_html() -> str:
    """A real capture of the page for the 2026-09-06 census."""
    return (FIXTURES / "census_2026-09-06.html").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def placeholder_html() -> str:
    """A real capture taken before the page's census request returned."""
    return (FIXTURES / "placeholder_2026-09-09.html").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def v1_record() -> dict:
    """The 2026-09-06 record as the v1 scraper stored it (mapping bug included)."""
    return json.loads((FIXTURES / "v1_2026-09-06.json").read_text(encoding="utf-8"))


@pytest.fixture
def record(census_html) -> dict:
    return parse_html(census_html)


@pytest.fixture
def census_day() -> date:
    return date(2026, 9, 6)
