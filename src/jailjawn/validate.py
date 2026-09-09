"""Decide whether a census record is fit to store.

A green workflow run must mean the data is right, not merely that the
fetch succeeded. Every check here returns an Issue; the CLI fails the run
if any issue is an error. Checks, in order:

1. The census date parses, is not in the future, and is not older than
   the newest record already stored.
2. Every table is present with its exact header row.
3. Every table has exactly the expected row labels, in order.
4. Arithmetic closes: facility rows sum to the total row, males plus
   females equals total, in facility plus temporarily not in facility
   equals facility totals, and facility totals plus other jurisdictions
   equals total population. These are warnings, not errors: the city has
   published figures that did not add up (2025-08-27, off by two people
   at RCF) and the record of what was published is worth keeping. The
   warnings are stored on the record so the discrepancy travels with it.
5. No numeric cell is empty text (the page's pre-load placeholder) or
   non-numeric text. Dashes are stored as None and are fine.
6. Plausibility: total population within a sane band and not swinging
   wildly from the previous day.
7. (In the CLI.) A census date already stored with different content
   is refused rather than overwritten.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from jailjawn.parse import HEADERS_BY_KEY, LABEL_FALLBACK, TABLE_KEYS

PHILADELPHIA = ZoneInfo("America/New_York")

FACILITIES = (
    "Curran-Fromhold Correctional Facility (CFCF)",
    "Detention Center (DC)",
    "Detention Center Public Health Services Wing (DC PHSW)",
    "Philadelphia Industrial Correctional Center (PICC)",
    "Riverside Correctional Facility (RCF)",
    "Riverside Correctional Facility Alternative and Special Detention Central Unit (RCF ASDCU)",
    "Riverside Correctional Facility Alternative and Special Detention Modular Unit (RCF ASDMOD3)",
    "Weekenders",
)

EXPECTED_ROWS: dict[str, tuple[str, ...]] = {
    "in_facility": FACILITIES + ("In facility headcount total",),
    "temporarily_not_in_facility": FACILITIES + ("Temporarily not in facility total",),
    "facility_totals": FACILITIES
    + ("In facility headcount and temporarily not in facility total",),
    "other_jurisdictions": (
        "State Department of Corrections (DOC)",
        "Juveniles",
        "Delaware County",
        "Lehigh County",
        "All other jurisdictions",
        "Total",
    ),
    "total_population": (
        "PDP in facility headcount and temporarily not in facility total",
        "Total PDP incarcerated people held in other jurisdictions",
        "Total",
    ),
}

# Population band and the largest day-over-day change accepted without a human look.
POPULATION_MIN = 1_000
POPULATION_MAX = 10_000
MAX_DAILY_SWING = 0.15


@dataclass(frozen=True)
class Issue:
    level: str  # "error" or "warning"
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.level}: {self.code}: {self.message}"


def _n(value) -> int:
    """Treat a dash (None) as zero for arithmetic."""
    return value if isinstance(value, int) else 0


def _label_column(key: str) -> str:
    return HEADERS_BY_KEY[key][0]


def _labels(rows: list[dict], key: str) -> list[str]:
    col = _label_column(key)
    return [str(r.get(col, "")) for r in rows]


def _row(rows: list[dict], key: str, label: str) -> dict | None:
    col = _label_column(key)
    for r in rows:
        if r.get(col) == label:
            return r
    return None


def _total_population(record: dict) -> int | None:
    rows = record["facilities"].get("total_population") or []
    total = _row(rows, "total_population", "Total")
    return total.get("Total") if total and isinstance(total.get("Total"), int) else None


def validate(
    record: dict,
    *,
    previous: dict | None = None,
    today: date | None = None,
) -> list[Issue]:
    """Return every problem found. An empty list means the record is good."""
    issues: list[Issue] = []
    err = lambda code, msg: issues.append(Issue("error", code, msg))  # noqa: E731
    warn = lambda code, msg: issues.append(Issue("warning", code, msg))  # noqa: E731
    tables = record.get("facilities", {})

    # 1. Census date
    today = today or datetime.now(PHILADELPHIA).date()
    census_date: date | None = None
    try:
        census_date = date.fromisoformat(record.get("census_date") or "")
    except ValueError:
        err("date_missing", "no census date found on the page")
    if census_date:
        if census_date > today:
            err("date_future", f"census date {census_date} is after today {today}")
        if previous and previous.get("census_date"):
            prev_date = date.fromisoformat(previous["census_date"])
            if census_date < prev_date:
                err(
                    "date_older",
                    f"census date {census_date} is older than stored {prev_date}",
                )

    # 2. Tables present with exact headers (the parser only files a table
    #    under a key when its header row matches exactly).
    for key in TABLE_KEYS:
        rows = tables.get(key)
        if not rows:
            err("table_missing", f"{key}: table not found or empty")
    if any(not tables.get(k) for k in TABLE_KEYS):
        return issues  # nothing below is meaningful without the tables

    # 3. Exact row labels in order
    for key, expected in EXPECTED_ROWS.items():
        got = _labels(tables[key], key)
        if tuple(got) != expected:
            missing = [l for l in expected if l not in got]
            extra = [l for l in got if l not in expected]
            err(
                "rows_unexpected",
                f"{key}: rows differ from expected"
                + (f"; missing {missing}" if missing else "")
                + (f"; unexpected {extra}" if extra else "")
                + ("; order differs" if not missing and not extra else ""),
            )

    # 5. Numeric cells hold ints or None. (Checked before arithmetic so the
    #    placeholder page produces one clear message, not twenty sums.)
    placeholder = False
    for key in TABLE_KEYS:
        label_col = _label_column(key)
        for row in tables[key]:
            for col, value in row.items():
                if col == label_col or value is None or isinstance(value, int):
                    continue
                if value == "":
                    placeholder = True
                else:
                    err(
                        "cell_not_numeric",
                        f"{key}: {row[label_col]!r} {col} = {value!r}",
                    )
    if placeholder:
        err(
            "cells_empty",
            "numeric cells are empty text: the page was captured before its data loaded",
        )
        return issues

    # 4. Arithmetic
    def check_column_sums(key: str, total_label: str) -> None:
        rows = tables[key]
        total = _row(rows, key, total_label)
        if total is None:
            return
        for col in HEADERS_BY_KEY[key][1:]:
            expected = sum(_n(r[col]) for r in rows if r is not total)
            if expected != _n(total[col]):
                warn(
                    "sum_mismatch",
                    f"{key}: {col} rows sum to {expected}, total row says {_n(total[col])}",
                )

    check_column_sums("in_facility", "In facility headcount total")
    check_column_sums(
        "temporarily_not_in_facility", "Temporarily not in facility total"
    )
    check_column_sums(
        "facility_totals", "In facility headcount and temporarily not in facility total"
    )
    check_column_sums("other_jurisdictions", "Total")
    check_column_sums("total_population", "Total")

    for key in ("facility_totals", "other_jurisdictions", "total_population"):
        for row in tables[key]:
            if _n(row["Males"]) + _n(row["Females"]) != _n(row["Total"]):
                warn(
                    "males_females_total",
                    f"{key}: {row[_label_column(key)]!r} males + females != total",
                )

    nif_male = (
        "Male workers",
        "Male furlough",
        "Male open ward",
        "Male emergency trips",
    )
    nif_female = tuple(c.replace("Male", "Female") for c in nif_male)
    for facility in FACILITIES:
        inf = _row(tables["in_facility"], "in_facility", facility)
        nif = _row(
            tables["temporarily_not_in_facility"],
            "temporarily_not_in_facility",
            facility,
        )
        tot = _row(tables["facility_totals"], "facility_totals", facility)
        if not (inf and nif and tot):
            continue
        males = (
            _n(inf["Adult males"])
            + _n(inf["Juvenile males"])
            + sum(_n(nif[c]) for c in nif_male)
        )
        females = (
            _n(inf["Adult females"])
            + _n(inf["Juvenile females"])
            + sum(_n(nif[c]) for c in nif_female)
        )
        if males != _n(tot["Males"]) or females != _n(tot["Females"]):
            warn(
                "facility_total_mismatch",
                f"{facility!r}: in facility + not in facility = {males}/{females}, "
                f"facility totals say {_n(tot['Males'])}/{_n(tot['Females'])}",
            )

    pop = tables["total_population"]
    fac_total = _row(
        tables["facility_totals"],
        "facility_totals",
        "In facility headcount and temporarily not in facility total",
    )
    oj_total = _row(tables["other_jurisdictions"], "other_jurisdictions", "Total")
    pop_fac = _row(pop, "total_population", EXPECTED_ROWS["total_population"][0])
    pop_oj = _row(pop, "total_population", EXPECTED_ROWS["total_population"][1])
    for name, a, b in (
        ("facility totals", fac_total, pop_fac),
        ("other jurisdictions", oj_total, pop_oj),
    ):
        if a and b:
            for col in ("Males", "Females", "Total"):
                if _n(a[col]) != _n(b[col]):
                    warn(
                        "population_mismatch",
                        f"total_population {name} {col} = {_n(b[col])}, source table says {_n(a[col])}",
                    )

    # 6. Plausibility
    total = _total_population(record)
    if total is None:
        err("total_missing", "total population has no numeric Total")
    else:
        if not POPULATION_MIN <= total <= POPULATION_MAX:
            err(
                "total_implausible",
                f"total population {total} outside {POPULATION_MIN}-{POPULATION_MAX}",
            )
        prev_total = _total_population(previous) if previous else None
        if prev_total:
            swing = abs(total - prev_total) / prev_total
            if swing > MAX_DAILY_SWING:
                err(
                    "total_swing",
                    f"total population moved {swing:.0%} from {prev_total} to {total}",
                )

    return issues


def errors(issues: list[Issue]) -> list[Issue]:
    return [i for i in issues if i.level == "error"]


def warnings(issues: list[Issue]) -> list[Issue]:
    return [i for i in issues if i.level == "warning"]


def attach_warnings(record: dict, issues: list[Issue]) -> dict:
    """Store any warnings on the record so they travel with the data."""
    messages = [f"{i.code}: {i.message}" for i in warnings(issues)]
    if messages:
        record["warnings"] = messages
    else:
        record.pop("warnings", None)
    return record
