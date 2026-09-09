"""Re-parse the saved page snapshots and prove the result against stored data.

Every daily run before v2 committed the rendered page to debug/. Those
snapshots are re-parsed with the v2 parser here. Before anything replaces a
stored file, the new record is checked against the old one:

* in_facility, other_jurisdictions and total_population must match the old
  file exactly, once the old file's zeros are read as "0 or dash" (v1 stored
  dashes as 0) and the blank total-population header is read as "Category".
* the old ``temporarily_not_in_facility`` table must equal the new
  ``facility_totals`` table under the same rule, because that is the table
  the v1 parser was actually storing under that key.

Any mismatch is reported and the day is not written. The report is meant
to be read by a person before ``--apply`` is used.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from jailjawn.parse import LABEL_FALLBACK, TABLE_KEYS, build_record, parse_page
from jailjawn.store import DATA_DIR, REPO_ROOT, dump_record, load_record
from jailjawn.validate import attach_warnings, errors, validate

DEBUG_DIR = REPO_ROOT / "debug"
_SNAPSHOT_RE = re.compile(r"page_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})\.html$")

# old key -> new key whose contents it must match
PROOF_PAIRS = (
    ("in_facility", "in_facility"),
    ("temporarily_not_in_facility", "facility_totals"),
    ("other_jurisdictions", "other_jurisdictions"),
    ("total_population", "total_population"),
)


@dataclass
class DayResult:
    census_date: str
    snapshot: Path
    old_path: Path | None
    matched: bool
    mismatches: list[str] = field(default_factory=list)
    validation: list[str] = field(default_factory=list)
    record: dict | None = None


@dataclass
class Report:
    days: list[DayResult] = field(default_factory=list)
    skipped: list[tuple[Path, str]] = field(default_factory=list)
    duplicates: list[tuple[str, Path, Path, bool]] = field(default_factory=list)
    # Stored files that hold no figures: v1 wrote the page's pre-load
    # placeholder as if it were a census. They are removed on --apply.
    empty_files: list[Path] = field(default_factory=list)


def holds_no_figures(record: dict) -> bool:
    for rows in record.get("facilities", {}).values():
        for row in rows:
            if any(isinstance(v, int) for v in list(row.values())[1:]):
                return False
    return True


def _normalise_old(rows: list[dict]) -> list[dict]:
    """Rename the blank label column so old rows compare with new ones."""
    return [{(k or LABEL_FALLBACK): v for k, v in r.items()} for r in rows]


def _same(old_value, new_value) -> bool:
    if new_value is None:
        return old_value == 0
    return old_value == new_value


def compare_tables(old_rows: list[dict], new_rows: list[dict]) -> list[str]:
    old_rows = _normalise_old(old_rows)
    if len(old_rows) != len(new_rows):
        return [f"row count {len(old_rows)} vs {len(new_rows)}"]
    problems = []
    for old, new in zip(old_rows, new_rows):
        if set(old) != set(new):
            problems.append(f"columns differ: {sorted(old)} vs {sorted(new)}")
            continue
        for col in old:
            if not _same(old[col], new[col]):
                problems.append(
                    f"{list(old.values())[0]!r} {col}: {old[col]!r} vs {new[col]!r}"
                )
    return problems


def prove(old: dict, new: dict) -> list[str]:
    problems = []
    for old_key, new_key in PROOF_PAIRS:
        for p in compare_tables(
            old["facilities"].get(old_key, []), new["facilities"].get(new_key, [])
        ):
            problems.append(f"{old_key} -> {new_key}: {p}")
    return problems


def snapshot_time(path: Path) -> datetime | None:
    m = _SNAPSHOT_RE.search(path.name)
    return datetime(*map(int, m.groups())) if m else None


def run(
    *,
    debug_dir: Path = DEBUG_DIR,
    data_dir: Path = DATA_DIR,
    out_dir: Path,
) -> Report:
    """Parse every snapshot, prove each day, and write proven records to out_dir."""
    report = Report()
    by_date: dict[str, tuple[Path, dict]] = {}

    for snapshot in sorted(debug_dir.glob("page_*.html")):
        html = snapshot.read_text(encoding="utf-8", errors="replace")
        parsed = parse_page(html)
        if parsed.census_date is None:
            report.skipped.append((snapshot, "no census date"))
            continue
        census_date = parsed.census_date.isoformat()
        old_path = data_dir / f"{census_date}.json"
        old = load_record(old_path) if old_path.exists() else None

        scraped_at = snapshot_time(snapshot) or datetime.now()
        if old and old.get("timestamp"):
            scraped_at = datetime.fromisoformat(old["timestamp"])
        record = build_record(parsed, scraped_at=scraped_at)

        issues = validate(
            record, today=parsed.census_date if parsed.census_date else None
        )
        if any(i.code == "cells_empty" for i in issues):
            report.skipped.append((snapshot, "captured before data loaded"))
            continue

        if census_date in by_date:
            prev_snap, prev_rec = by_date[census_date]
            identical = prev_rec["facilities"] == record["facilities"]
            report.duplicates.append((census_date, prev_snap, snapshot, identical))
            if identical:
                continue

        attach_warnings(record, issues)
        mismatches = prove(old, record) if old else []
        by_date[census_date] = (snapshot, record)
        report.days.append(
            DayResult(
                census_date=census_date,
                snapshot=snapshot,
                old_path=old_path if old else None,
                matched=not mismatches,
                mismatches=mismatches,
                validation=[str(i) for i in errors(issues)],
                record=record,
            )
        )

    for day in report.days:
        if day.matched and day.record is not None:
            dump_record(day.record, out_dir / f"{day.census_date}.json")

    recovered = {d.census_date for d in report.days}
    for path in sorted(data_dir.glob("????-??-??.json")):
        if path.stem not in recovered and holds_no_figures(load_record(path)):
            report.empty_files.append(path)
    return report


def render_report(report: Report) -> str:
    days = report.days
    matched = [d for d in days if d.matched]
    new_days = [d for d in days if d.old_path is None]
    unmatched = [d for d in days if not d.matched]
    with_validation = [d for d in days if d.validation]
    with_warnings = [d for d in days if d.record and d.record.get("warnings")]
    lines = [
        "# Backfill report",
        "",
        f"- snapshots read: {len(days) + len(report.skipped) + sum(1 for d in report.duplicates if d[3])}",
        f"- census days recovered: {len(days)}",
        f"- days proven against existing data: {len(matched) - len(new_days)}",
        f"- days with no existing file (new to the dataset): {len(new_days)}",
        f"- days that FAILED the proof (not written): {len(unmatched)}",
        f"- days with validation errors (written if proof passed): {len(with_validation)}",
        f"- days stored with warnings (figures as published did not add up): {len(with_warnings)}",
        f"- stored files holding no figures (placeholder captures, removed on apply): {len(report.empty_files)}",
        f"- snapshots skipped: {len(report.skipped)}",
        f"- duplicate snapshots of one census day: {len(report.duplicates)}"
        f" ({sum(1 for d in report.duplicates if not d[3])} with differing content)",
        "",
    ]
    if unmatched:
        lines += ["## Proof failures", ""]
        for d in unmatched:
            lines.append(f"### {d.census_date} ({d.snapshot.name})")
            lines += [f"- {m}" for m in d.mismatches]
            lines.append("")
    if with_validation:
        lines += ["## Validation errors in recovered days", ""]
        for d in with_validation:
            lines.append(f"### {d.census_date}")
            lines += [f"- {v}" for v in d.validation]
            lines.append("")
    if with_warnings:
        lines += ["## Days stored with warnings", ""]
        for d in with_warnings:
            lines.append(f"### {d.census_date}")
            lines += [f"- {w}" for w in d.record["warnings"]]
            lines.append("")
    if report.empty_files:
        lines += ["## Stored files holding no figures", ""]
        lines += [f"- {p.name}" for p in report.empty_files]
        lines.append("")
    if report.skipped:
        lines += ["## Skipped snapshots", ""]
        lines += [f"- {p.name}: {why}" for p, why in report.skipped]
        lines.append("")
    if report.duplicates:
        lines += ["## Census days captured more than once", ""]
        for date_, a, b, identical in report.duplicates:
            lines.append(
                f"- {date_}: {a.name} and {b.name} ({'identical' if identical else 'DIFFER'})"
            )
        lines.append("")
    return "\n".join(lines)
