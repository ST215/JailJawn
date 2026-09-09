"""Read and write the repository's data files.

Layout, relative to the repository root:

    raw/YYYY-MM-DD.html   the rendered page exactly as captured
    data/YYYY-MM-DD.json  the parsed census record
    census.csv            one row per census day, every figure as a column

The CSV is regenerated from data/ on every write so it can never drift.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from jailjawn.parse import HEADERS_BY_KEY, TABLE_KEYS
from jailjawn.validate import EXPECTED_ROWS

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = REPO_ROOT / "raw"
CSV_PATH = REPO_ROOT / "census.csv"

# Short, stable identifiers for CSV column names.
ROW_KEYS = {
    "Curran-Fromhold Correctional Facility (CFCF)": "cfcf",
    "Detention Center (DC)": "dc",
    "Detention Center Public Health Services Wing (DC PHSW)": "dc_phsw",
    "Philadelphia Industrial Correctional Center (PICC)": "picc",
    "Riverside Correctional Facility (RCF)": "rcf",
    "Riverside Correctional Facility Alternative and Special Detention Central Unit (RCF ASDCU)": "rcf_asdcu",
    "Riverside Correctional Facility Alternative and Special Detention Modular Unit (RCF ASDMOD3)": "rcf_asdmod3",
    "Weekenders": "weekenders",
    "In facility headcount total": "total",
    "Temporarily not in facility total": "total",
    "In facility headcount and temporarily not in facility total": "total",
    "State Department of Corrections (DOC)": "state_doc",
    "Juveniles": "juveniles",
    "Delaware County": "delaware_county",
    "Lehigh County": "lehigh_county",
    "All other jurisdictions": "all_other",
    "Total": "total",
    "PDP in facility headcount and temporarily not in facility total": "pdp_facilities",
    "Total PDP incarcerated people held in other jurisdictions": "other_jurisdictions",
}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def row_key(label: str) -> str:
    return ROW_KEYS.get(label) or slug(label)


def column_name(table: str, label: str, column: str) -> str:
    return f"{table}.{row_key(label)}.{slug(column)}"


def csv_columns() -> list[str]:
    """Every expected figure, in page order."""
    cols = ["census_date", "scrape_date"]
    for table in TABLE_KEYS:
        headers = HEADERS_BY_KEY[table]
        for label in EXPECTED_ROWS[table]:
            for column in headers[1:]:
                cols.append(column_name(table, label, column))
    return cols


def record_path(census_date: str) -> Path:
    return DATA_DIR / f"{census_date}.json"


def raw_path(census_date: str) -> Path:
    return RAW_DIR / f"{census_date}.html"


def load_record(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def all_records(data_dir: Path = DATA_DIR) -> list[tuple[Path, dict]]:
    """Every stored record, oldest first."""
    return [(p, load_record(p)) for p in sorted(data_dir.glob("????-??-??.json"))]


def latest_record(data_dir: Path = DATA_DIR) -> dict | None:
    paths = sorted(data_dir.glob("????-??-??.json"))
    return load_record(paths[-1]) if paths else None


def dump_record(record: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
        f.write("\n")


def write_raw(html: str, census_date: str, raw_dir: Path = RAW_DIR) -> Path:
    path = raw_dir / f"{census_date}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path


def same_census(a: dict, b: dict) -> bool:
    """True when two records carry the same census figures (capture time aside)."""
    return a.get("census_date") == b.get("census_date") and a.get(
        "facilities"
    ) == b.get("facilities")


def flatten(record: dict) -> dict[str, str]:
    """One CSV row. Dashes (None) become empty cells."""
    row = {
        "census_date": record.get("census_date", ""),
        "scrape_date": record.get("scrape_date", ""),
    }
    for table in TABLE_KEYS:
        headers = HEADERS_BY_KEY[table]
        for r in record.get("facilities", {}).get(table, []):
            label = str(r.get(headers[0], ""))
            for column in headers[1:]:
                value = r.get(column)
                row[column_name(table, label, column)] = (
                    "" if value is None else str(value)
                )
    return row


def export_csv(data_dir: Path = DATA_DIR, csv_path: Path = CSV_PATH) -> int:
    """Rebuild census.csv from every record in data_dir. Returns the row count."""
    columns = csv_columns()
    rows = [flatten(rec) for _, rec in all_records(data_dir)]
    extra = sorted({k for r in rows for k in r} - set(columns))
    columns += extra
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)
