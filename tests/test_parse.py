from jailjawn.parse import TABLE_KEYS, parse_cell, parse_census_date, parse_page


def test_parse_cell_values():
    assert parse_cell("1,422") == 1422
    assert parse_cell(" 43 ") == 43
    assert parse_cell("0") == 0
    assert parse_cell("-") is None
    assert parse_cell("") == ""
    assert parse_cell("Weekenders") == "Weekenders"


def test_parse_census_date():
    assert (
        parse_census_date("Census for: September 06, 2026").isoformat() == "2026-09-06"
    )
    assert parse_census_date("Census for:  March 5, 2025").isoformat() == "2025-03-05"
    assert parse_census_date("no date here") is None


def test_all_five_tables_found_by_header(census_html):
    parsed = parse_page(census_html)
    assert parsed.census_date.isoformat() == "2026-09-06"
    assert tuple(parsed.tables) == TABLE_KEYS
    assert parsed.unrecognized == []


def test_facility_totals_are_not_filed_as_not_in_facility(record):
    """The v1 bug: the 'PDP facility totals' heading mentions 'temporarily not in facility'."""
    nif = record["facilities"]["temporarily_not_in_facility"]
    totals = record["facilities"]["facility_totals"]
    assert "Male open ward" in nif[0]
    assert nif[0]["Male open ward"] == 8
    assert totals[0] == {
        "Facility": "Curran-Fromhold Correctional Facility (CFCF)",
        "Males": 1431,
        "Females": None,
        "Total": 1431,
    }


def test_dash_is_none_not_zero(record):
    cfcf = record["facilities"]["in_facility"][0]
    assert cfcf["Adult males"] == 1422
    assert cfcf["Adult females"] is None


def test_blank_header_becomes_category(record):
    rows = record["facilities"]["total_population"]
    assert list(rows[0]) == ["Category", "Males", "Females", "Total"]
    assert rows[-1] == {
        "Category": "Total",
        "Males": 3013,
        "Females": 230,
        "Total": 3243,
    }


def test_record_shape(record):
    assert record["schema_version"] == 2
    assert record["census_date"] == "2026-09-06"
    assert record["source_url"].startswith("https://www.phila.gov/")
    assert set(record["facilities"]) == set(TABLE_KEYS)


def test_placeholder_page_parses_with_empty_cells(placeholder_html):
    parsed = parse_page(placeholder_html)
    first = parsed.tables["in_facility"][0]
    assert first["Adult males"] == ""
