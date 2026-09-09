from jailjawn import legacy


def test_row_keys_collapse_whitespace():
    assert legacy.row_key("DC-DETENTION   CENTER") == "dc"
    assert legacy.row_key("Lehigh Co ") == "lehigh_county"
    assert legacy.row_key('PPS   "In Facility" Count') == "pdp_in_facility"
    assert legacy.row_key("Something New") == "something_new"


def test_summary_row_shift_is_undone():
    fields = {
        "Facility Name": "Total",
        "Adult Male": 6800,
        "Adult Female": 663,
        "Juvenile Male": 7463,  # the grand total, shifted by the 2013 scraper
        "Juvenile Female": 0,
        "Total Count": 0,
    }
    row = legacy.convert_row("2016-08-15", "Total", fields)
    assert row["shape"] == "summary"
    assert (row["males"], row["females"], row["total"]) == (6800, 663, 7463)
    assert row["juvenile_males"] is None
    assert row["note"] == ""


def test_summary_row_notes_a_mismatch():
    row = legacy.convert_row(
        "2013-12-21",
        "Total ",
        {"Adult Male": 7439, "Adult Female": 782, "Juvenile Male": 8759},
    )
    assert row["total"] == 8759
    assert "8221" in row["note"]


def test_facility_row_keeps_all_columns():
    fields = {
        "Adult Male": 2772,
        "Adult Female": 0,
        "Juvenile Male": 0,
        "Open Ward Male": 2,
        "Worker Male": "##",
        "Total Count": 2774,
    }
    row = legacy.convert_row("2013-12-21", "CFCF", fields)
    assert row["shape"] == "facility"
    assert row["total"] == 2774
    assert row["open_ward_m"] == 2
    assert row["workers_m"] is None  # the city's Excel overflow


def test_summarize_one_day():
    rows = [
        legacy.convert_row(
            "2016-08-15",
            "Total",
            {"Adult Male": 6800, "Adult Female": 663, "Juvenile Male": 7463},
        ),
        legacy.convert_row(
            "2016-08-15",
            "CFCF",
            {"Adult Male": 2793, "Total Count": 2798, "Open Ward Male": 4},
        ),
        legacy.convert_row(
            "2016-08-15",
            'PDP   "In Facility" Count',
            {
                "Adult Male": 6331,
                "Adult Female": 656,
                "Juvenile Male": 54,
                "Open Ward Male": 7,
                "Open Ward Female": 1,
                "Total Count": 7052,
            },
        ),
        legacy.convert_row(
            "2016-08-15",
            "Other   Jurisdiction",
            {"Adult Male": 58, "Adult Female": 3, "Juvenile Male": 61},
        ),
    ]
    (day,) = legacy.summarize(rows)
    assert day["total"] == 7463
    assert day["cfcf"] == 2798
    assert day["cfcf_males"] == 2793
    assert day["juveniles_in_facility"] == 54
    assert day["open_ward"] == 8
    assert day["other_jurisdictions"] == 61
