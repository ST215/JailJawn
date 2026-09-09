import copy
from datetime import date

from jailjawn.parse import parse_html
from jailjawn.validate import errors, validate


def codes(issues):
    return sorted({i.code for i in issues})


def test_real_page_passes_every_check(record, census_day):
    assert validate(record, today=census_day) == []


def test_placeholder_page_is_refused(placeholder_html):
    record = parse_html(placeholder_html)
    found = codes(errors(validate(record, today=date(2026, 9, 8))))
    assert "cells_empty" in found
    assert "date_future" in found


def test_future_census_date(record):
    assert codes(validate(record, today=date(2026, 9, 5))) == ["date_future"]


def test_older_than_stored(record, census_day):
    previous = copy.deepcopy(record)
    previous["census_date"] = "2026-09-07"
    assert "date_older" in codes(
        validate(record, previous=previous, today=date(2026, 9, 7))
    )


def test_missing_date(record, census_day):
    record["census_date"] = ""
    assert "date_missing" in codes(validate(record, today=census_day))


def test_missing_table_stops_early(record, census_day):
    record["facilities"]["facility_totals"] = []
    assert codes(validate(record, today=census_day)) == ["table_missing"]


def test_unexpected_row(record, census_day):
    record["facilities"]["in_facility"][0]["Facility"] = "New Facility (NEW)"
    assert "rows_unexpected" in codes(validate(record, today=census_day))


def test_sum_mismatch_detected(record, census_day):
    record["facilities"]["in_facility"][0]["Adult males"] += 1
    found = codes(validate(record, today=census_day))
    assert "sum_mismatch" in found
    assert "facility_total_mismatch" in found


def test_mislabeled_tables_would_have_been_caught(v1_record, census_day):
    """The v1 files hold facility totals under the not-in-facility key."""
    found = codes(validate(v1_record, today=census_day))
    assert "table_missing" in found


def test_males_plus_females(record, census_day):
    record["facilities"]["other_jurisdictions"][-1]["Total"] += 5
    found = codes(validate(record, today=census_day))
    assert "males_females_total" in found


def test_population_cross_check(record, census_day):
    record["facilities"]["total_population"][1]["Total"] = 999
    assert "population_mismatch" in codes(validate(record, today=census_day))


def test_implausible_total(record, census_day):
    for row in record["facilities"]["total_population"]:
        for col in ("Males", "Females", "Total"):
            row[col] = 0
    record["facilities"]["total_population"][0]["Total"] = 0
    found = codes(validate(record, today=census_day))
    assert "total_implausible" in found


def test_daily_swing(record, census_day):
    previous = copy.deepcopy(record)
    previous["census_date"] = "2026-09-05"
    previous["facilities"]["total_population"][-1]["Total"] = 2000
    assert "total_swing" in codes(validate(record, previous=previous, today=census_day))
