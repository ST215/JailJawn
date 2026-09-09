import json
import shutil
from pathlib import Path

from jailjawn.backfill import (
    compare_tables,
    holds_no_figures,
    prove,
    render_report,
    run,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_old_zero_matches_new_dash():
    assert (
        compare_tables(
            [{"Facility": "X", "Males": 0}], [{"Facility": "X", "Males": None}]
        )
        == []
    )
    assert compare_tables(
        [{"Facility": "X", "Males": 0}], [{"Facility": "X", "Males": 3}]
    )


def test_blank_header_is_renamed_for_comparison():
    old = [{"": "Total", "Total": 5}]
    new = [{"Category": "Total", "Total": 5}]
    assert compare_tables(old, new) == []


def test_proof_of_v1_record_against_v2_parse(v1_record, record):
    """The v1 file's mislabeled table must equal the v2 facility_totals table."""
    assert prove(v1_record, record) == []


def test_proof_catches_a_changed_number(v1_record, record):
    v1_record["facilities"]["in_facility"][0]["Adult males"] += 1
    problems = prove(v1_record, record)
    assert len(problems) == 1
    assert "in_facility -> in_facility" in problems[0]


def test_run_writes_only_proven_days(tmp_path):
    debug = tmp_path / "debug"
    data = tmp_path / "data"
    out = tmp_path / "out"
    debug.mkdir()
    data.mkdir()
    shutil.copy(
        FIXTURES / "census_2026-09-06.html", debug / "page_20260907_170213.html"
    )
    shutil.copy(
        FIXTURES / "placeholder_2026-09-09.html", debug / "page_20260909_021134.html"
    )
    shutil.copy(FIXTURES / "v1_2026-09-06.json", data / "2026-09-06.json")
    placeholder = json.loads((FIXTURES / "v1_2026-09-06.json").read_text())
    for rows in placeholder["facilities"].values():
        for row in rows:
            for col in list(row)[1:]:
                row[col] = ""
    (data / "2026-09-09.json").write_text(json.dumps(placeholder))

    report = run(debug_dir=debug, data_dir=data, out_dir=out)
    assert [p.name for p in report.empty_files] == ["2026-09-09.json"]
    assert [d.census_date for d in report.days] == ["2026-09-06"]
    assert report.days[0].matched
    assert report.days[0].validation == []
    assert [why for _, why in report.skipped] == ["captured before data loaded"]

    written = json.loads((out / "2026-09-06.json").read_text())
    assert written["timestamp"] == "2026-09-07T17:02:14"  # kept from the v1 file
    assert written["facilities"]["facility_totals"][0]["Total"] == 1431
    text = render_report(report)
    assert "days that FAILED the proof (not written): 0" in text


def test_holds_no_figures(record):
    assert not holds_no_figures(record)
    empty = {
        "facilities": {
            "in_facility": [
                {"Facility": "X", "Adult males": "", "Adult females": "NaN"}
            ]
        }
    }
    assert holds_no_figures(empty)
