"""Import the 2013-2017 census from the original JailJawn Firebase export.

The first JailJawn scraper ran on AWS Lambda and pushed each day into a
Firebase database. ``legacy/firebase-export.json`` is that database as
exported in 2017: a dict keyed by census date, each holding one dict per
row of the old census page, each with sixteen fields.

The old page had two kinds of rows. Facility rows had every column (adult
and juvenile counts by sex, workers, furlough, open ward, emergency room
trips, and a total). Summary rows (totals, other jurisdictions, CEC, Lehigh
County and the like) had only three columns: males, females, total. The
2013 scraper read every row positionally, so a summary row's total landed
under "Juvenile Male". Kevin Diem filed this as issue #25 at the time. This
importer undoes that shift and records which rows it applied to.

Outputs, both under legacy/:

    census-2013-2017.csv   every row of every day, corrected, one row per line
    summary.csv            one line per day: the totals the site charts
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from jailjawn.store import REPO_ROOT

LEGACY_DIR = REPO_ROOT / "legacy"
EXPORT_PATH = LEGACY_DIR / "firebase-export.json"
LONG_CSV = LEGACY_DIR / "census-2013-2017.csv"
SUMMARY_CSV = LEGACY_DIR / "summary.csv"

# Old row label (whitespace collapsed) -> stable key
ROW_KEYS = {
    "ASD Cannery": "asd_cannery",
    "ASD WRP-UNIV AVE": "asd_wrp",
    "ASD ASDCU": "asd_asdcu",
    "ASD MOD 3": "asd_mod3",
    "ASD Cambria": "asd_cambria",
    "CEC": "cec",
    "CFCF": "cfcf",
    "DC-DETENTION CENTER": "dc",
    "DC-PHSW": "dc_phsw",
    "Delaware County": "delaware_county",
    "HOC": "hoc",
    "Not in Facility Total": "nif_total",
    "Other Jurisdiction": "other_jurisdictions",
    "Out of County": "out_of_county",
    "PICC": "picc",
    "RCF": "rcf",
    "State DOC": "state_doc",
    "Total": "total",
    'Total "In Facility" Count (Adults Juv)': "in_facility_total",
    "Weekenders": "weekenders",
    "Lehigh Co": "lehigh_county",
    "ROTH": "roth",
    'PDP "In Facility" Count': "pdp_in_facility",
    'PPS "In Facility" Count': "pdp_in_facility",
    "PDP Headcount NIF": "pdp_headcount_nif",
    "PPS Headcount NIF": "pdp_headcount_nif",
    "PDP Headcount NIF OJ (Census)": "pdp_headcount_nif_oj",
    "PPS Headcount NIF OJ (Census)": "pdp_headcount_nif_oj",
    "Juveniles": "juveniles",
    "Liberty": "liberty",
}

# Rows the old page printed with three columns (males, females, total).
SUMMARY_ROWS = {
    "cec",
    "lehigh_county",
    "nif_total",
    "other_jurisdictions",
    "pdp_headcount_nif",
    "pdp_headcount_nif_oj",
    "total",
    "roth",
    "juveniles",
    "state_doc",
    "delaware_county",
    "out_of_county",
    "in_facility_total",
}

FACILITY_NAMES = {
    "cfcf": "Curran-Fromhold Correctional Facility (CFCF)",
    "dc": "Detention Center (DC)",
    "dc_phsw": "Detention Center Public Health Services Wing (DC PHSW)",
    "picc": "Philadelphia Industrial Correctional Center (PICC)",
    "rcf": "Riverside Correctional Facility (RCF)",
    "hoc": "House of Correction (HOC)",
    "cec": "Community Education Centers (CEC)",
    "asd_cambria": "Alternative and Special Detention, Cambria",
    "asd_cannery": "Alternative and Special Detention, Cannery",
    "asd_wrp": "Alternative and Special Detention, Work Release Program",
    "asd_asdcu": "Alternative and Special Detention Central Unit (ASDCU)",
    "asd_mod3": "Alternative and Special Detention Modular Unit 3",
    "weekenders": "Weekenders",
    "liberty": "Liberty",
    "roth": "Roth",
}

FIELD_KEYS = {
    "Adult Male": "adult_males",
    "Adult Female": "adult_females",
    "Juvenile Male": "juvenile_males",
    "Juvenile Female": "juvenile_females",
    "Worker Male": "workers_m",
    "Worker Female": "workers_f",
    "Furlough Male": "furlough_m",
    "Furlough Female": "furlough_f",
    "Open Ward Male": "open_ward_m",
    "Open Ward Female": "open_ward_f",
    "Emergecy Room Trip Male": "er_trips_m",
    "Emergecy Room Trip Female": "er_trips_f",
    "In Out Male": "in_out_m",
    "In Out Female": "in_out_f",
    "Total Count": "total",
}

LONG_COLUMNS = (
    ["date", "row", "shape", "males", "females", "total"]
    + [
        k
        for k in FIELD_KEYS.values()
        if k not in ("adult_males", "adult_females", "total")
    ]
    + ["note"]
)


def _collapse(label: str) -> str:
    return re.sub(r"\s+", " ", label).strip()


def _num(value) -> int | None:
    """Ints pass; '##' (an Excel overflow the city published) and blanks are None."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        v = value.strip().replace(",", "")
        return int(v) if v.isdigit() else None
    return None


def row_key(label: str) -> str:
    return ROW_KEYS.get(
        _collapse(label),
        re.sub(r"[^a-z0-9]+", "_", _collapse(label).lower()).strip("_"),
    )


def convert_row(date: str, label: str, fields: dict) -> dict:
    key = row_key(label)
    values = {FIELD_KEYS[k]: _num(v) for k, v in fields.items() if k in FIELD_KEYS}
    out = {"date": date, "row": key, "note": ""}
    if key in SUMMARY_ROWS:
        # Three-column row read positionally: total sits under juvenile_males.
        out["shape"] = "summary"
        out["males"] = values.get("adult_males")
        out["females"] = values.get("adult_females")
        out["total"] = values.get("juvenile_males")
        for k in LONG_COLUMNS:
            if k not in out:
                out[k] = None
        # in_facility_total kept its open ward and worker columns
        if key == "in_facility_total":
            for k in ("open_ward_m", "open_ward_f", "workers_m", "workers_f"):
                out[k] = values.get(k)
        m, f, t = out["males"], out["females"], out["total"]
        if None not in (m, f, t) and m + f != t:
            out["note"] = f"males + females = {m + f}, published total {t}"
    else:
        out["shape"] = "facility"
        out["males"] = values.get("adult_males")
        out["females"] = values.get("adult_females")
        out["total"] = values.get("total")
        for k in LONG_COLUMNS:
            if k not in out:
                out[k] = values.get(k)
    return out


def load_export(path: Path = EXPORT_PATH) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def convert(export: dict) -> list[dict]:
    rows = []
    for date in sorted(export):
        for label, fields in export[date].items():
            if isinstance(fields, dict):
                rows.append(convert_row(date, label, fields))
    return rows


SUMMARY_COLUMNS = (
    [
        "date",
        "total",
        "males",
        "females",
        "in_facility",
        "not_in_facility",
        "other_jurisdictions",
        "juveniles_in_facility",
        "open_ward",
        "emergency_trips",
        "workers",
        "furlough",
        "note",
    ]
    + list(FACILITY_NAMES)
    + [
        f"{fac}_{col}"
        for fac in FACILITY_NAMES
        for col in ("males", "females", "juveniles")
    ]
    + [
        "in_facility_males",
        "in_facility_females",
        "lehigh_county",
        "delaware_county",
        "state_doc",
        "out_of_county",
    ]
)


def summarize(rows: list[dict]) -> list[dict]:
    by_date: dict[str, dict[str, dict]] = {}
    for r in rows:
        by_date.setdefault(r["date"], {})[r["row"]] = r
    out = []
    for date, day in sorted(by_date.items()):
        g = lambda row, col: (day.get(row) or {}).get(col)  # noqa: E731
        add = lambda *vals: (
            sum(v for v in vals if isinstance(v, int))
            if any(isinstance(v, int) for v in vals)
            else None
        )  # noqa: E731
        inf = day.get("pdp_in_facility") or {}
        s = {
            "date": date,
            "total": g("total", "total"),
            "males": g("total", "males"),
            "females": g("total", "females"),
            "in_facility": g("in_facility_total", "total"),
            "not_in_facility": g("nif_total", "total"),
            "other_jurisdictions": g("other_jurisdictions", "total"),
            "juveniles_in_facility": add(
                inf.get("juvenile_males"), inf.get("juvenile_females")
            ),
            "open_ward": add(inf.get("open_ward_m"), inf.get("open_ward_f")),
            "emergency_trips": add(inf.get("er_trips_m"), inf.get("er_trips_f")),
            "workers": add(inf.get("workers_m"), inf.get("workers_f")),
            "furlough": add(inf.get("furlough_m"), inf.get("furlough_f")),
            "note": (day.get("total") or {}).get("note", ""),
        }
        for fac in FACILITY_NAMES:
            s[fac] = g(fac, "total")
            s[f"{fac}_males"] = g(fac, "males")
            s[f"{fac}_females"] = g(fac, "females")
            s[f"{fac}_juveniles"] = add(
                g(fac, "juvenile_males"), g(fac, "juvenile_females")
            )
        s["in_facility_males"] = g("in_facility_total", "males")
        s["in_facility_females"] = g("in_facility_total", "females")
        for oj in ("lehigh_county", "delaware_county", "state_doc", "out_of_county"):
            s[oj] = g(oj, "total")
        out.append(s)
    return out


def _write(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=columns, lineterminator="\n", extrasaction="ignore"
        )
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if v is None else v) for k, v in r.items()})


def run(export_path: Path = EXPORT_PATH) -> tuple[int, int]:
    rows = convert(load_export(export_path))
    summary = summarize(rows)
    _write(LONG_CSV, LONG_COLUMNS, rows)
    _write(SUMMARY_CSV, SUMMARY_COLUMNS, summary)
    return len(rows), len(summary)
