import csv
import json

from jailjawn.store import (
    column_name,
    csv_columns,
    dump_record,
    export_csv,
    flatten,
    row_key,
    same_census,
)


def test_row_keys_are_short_and_stable():
    assert row_key("Curran-Fromhold Correctional Facility (CFCF)") == "cfcf"
    assert row_key("In facility headcount total") == "total"
    assert row_key("Some Brand New Place (SBNP)") == "some_brand_new_place_sbnp"
    assert (
        column_name("in_facility", "Weekenders", "Adult males")
        == "in_facility.weekenders.adult_males"
    )


def test_csv_columns_cover_the_whole_page():
    cols = csv_columns()
    assert cols[:2] == ["census_date", "scrape_date"]
    assert len(cols) == 2 + 9 * 4 + 9 * 8 + 9 * 3 + 6 * 3 + 3 * 3
    assert len(cols) == len(set(cols))


def test_flatten_matches_columns(record):
    row = flatten(record)
    assert set(row) == set(csv_columns())
    assert row["in_facility.cfcf.adult_males"] == "1422"
    assert row["in_facility.cfcf.adult_females"] == ""  # a dash on the page
    assert row["total_population.total.total"] == "3243"


def test_export_csv_round_trip(tmp_path, record):
    data_dir = tmp_path / "data"
    dump_record(record, data_dir / "2026-09-06.json")
    second = json.loads(json.dumps(record))
    second["census_date"] = "2026-09-07"
    dump_record(second, data_dir / "2026-09-07.json")

    out = tmp_path / "census.csv"
    assert export_csv(data_dir, out) == 2
    with out.open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert [r["census_date"] for r in rows] == ["2026-09-06", "2026-09-07"]
    assert rows[0]["facility_totals.total.total"] == "3075"


def test_same_census_ignores_capture_time(record):
    other = json.loads(json.dumps(record))
    other["timestamp"] = "2099-01-01T00:00:00"
    assert same_census(record, other)
    other["facilities"]["in_facility"][0]["Adult males"] = 1
    assert not same_census(record, other)
