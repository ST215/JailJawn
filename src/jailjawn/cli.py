"""Command line entry point.

    jailjawn scrape            fetch, parse, validate, store, and rebuild the CSV
    jailjawn scrape --html F   same, but parse a saved page instead of fetching
    jailjawn validate FILE...  run the checks against stored JSON records
    jailjawn backfill          re-parse debug/ snapshots and write a proof report
    jailjawn export            rebuild census.csv and the feeds from data/
    jailjawn legacy            convert the 2013-2017 Firebase export in legacy/

Exit codes: 0 success or nothing new, 1 validation refused the data,
2 the page could not be fetched.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

from jailjawn import __version__
from jailjawn.store import (
    CSV_PATH,
    DATA_DIR,
    RAW_DIR,
    REPO_ROOT,
    dump_record,
    export_csv,
    export_feeds,
    latest_record,
    load_record,
    record_path,
    same_census,
    write_raw,
)
from jailjawn.validate import attach_warnings, errors, validate

log = logging.getLogger("jailjawn")


def cmd_scrape(args: argparse.Namespace) -> int:
    from jailjawn.parse import parse_html

    if args.html:
        html = Path(args.html).read_text(encoding="utf-8")
    else:
        from jailjawn.fetch import fetch_page

        try:
            html = fetch_page()
        except Exception as exc:  # noqa: BLE001
            log.error("fetch failed: %s", exc)
            return 2

    record = parse_html(html, scraped_at=datetime.now().astimezone())
    previous = latest_record(args.data_dir)
    issues = validate(record, previous=previous)
    for issue in issues:
        log.log(
            logging.ERROR if issue.level == "error" else logging.WARNING, "%s", issue
        )
    if errors(issues):
        log.error("refusing to store census dated %r", record["census_date"])
        return 1
    attach_warnings(record, issues)

    census_date = record["census_date"]
    existing_path = args.data_dir / f"{census_date}.json"
    if existing_path.exists():
        existing = load_record(existing_path)
        if same_census(existing, record):
            log.info("census for %s already stored; nothing to do", census_date)
            return 0
        log.error(
            "census for %s is already stored with different figures; "
            "refusing to overwrite %s",
            census_date,
            existing_path,
        )
        return 1

    if args.dry_run:
        log.info("dry run: would store census for %s", census_date)
        return 0

    write_raw(html, census_date, args.raw_dir)
    dump_record(record, existing_path)
    rows = export_csv(args.data_dir, args.csv)
    if args.data_dir == DATA_DIR:
        export_feeds(args.data_dir)
    log.info("stored census for %s; census.csv now has %d rows", census_date, rows)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    failed = 0
    previous = None
    for path in args.files:
        record = load_record(Path(path))
        issues = validate(record, previous=previous, today=datetime.now().date())
        previous = record
        if errors(issues):
            failed += 1
            print(f"{path}: {len(errors(issues))} error(s)")
            for issue in issues:
                print(f"  {issue}")
        elif args.verbose:
            print(f"{path}: ok")
    print(f"{len(args.files) - failed} ok, {failed} with errors")
    return 1 if failed else 0


def cmd_backfill(args: argparse.Namespace) -> int:
    from jailjawn.backfill import render_report, run

    out_dir = Path(args.out)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    report = run(out_dir=out_dir, data_dir=args.data_dir)
    text = render_report(report)
    Path(args.report).write_text(text, encoding="utf-8")
    print(text.split("\n\n")[1])
    print(f"\nfull report: {args.report}")

    if args.apply:
        unmatched = [d for d in report.days if not d.matched]
        if unmatched:
            print(f"not applying: {len(unmatched)} day(s) failed the proof")
            return 1
        written = 0
        for path in sorted(out_dir.glob("*.json")):
            shutil.copy(path, args.data_dir / path.name)
            written += 1
        for path in report.empty_files:
            path.unlink()
        rows = export_csv(args.data_dir, args.csv)
        print(
            f"applied {written} records to {args.data_dir}, removed "
            f"{len(report.empty_files)} placeholder files; census.csv has {rows} rows"
        )
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    rows = export_csv(args.data_dir, args.csv)
    print(f"wrote {rows} rows to {args.csv}")
    if args.data_dir == DATA_DIR:
        entries = export_feeds(args.data_dir)
        print(f"wrote feed.xml, feed.json ({entries} entries) and latest.json")
    return 0


def cmd_legacy(args: argparse.Namespace) -> int:
    from jailjawn import legacy

    rows, days = legacy.run()
    print(
        f"wrote {rows} rows for {days} days to {legacy.LONG_CSV.name} and {legacy.SUMMARY_CSV.name}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jailjawn", description=__doc__.split("\n")[0]
    )
    parser.add_argument(
        "--version", action="version", version=f"jailjawn {__version__}"
    )
    parser.add_argument(
        "--data-dir", type=Path, default=DATA_DIR, help=argparse.SUPPRESS
    )
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR, help=argparse.SUPPRESS)
    parser.add_argument("--csv", type=Path, default=CSV_PATH, help=argparse.SUPPRESS)
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("scrape", help="fetch today's census and store it")
    p.add_argument("--html", help="parse this saved page instead of fetching")
    p.add_argument("--dry-run", action="store_true", help="validate but write nothing")
    p.set_defaults(func=cmd_scrape)

    p = sub.add_parser("validate", help="check stored records")
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("backfill", help="re-parse debug/ snapshots and prove them")
    p.add_argument("--out", default=str(REPO_ROOT / "build" / "backfill"))
    p.add_argument("--report", default=str(REPO_ROOT / "build" / "backfill-report.md"))
    p.add_argument(
        "--apply", action="store_true", help="copy proven records into data/"
    )
    p.set_defaults(func=cmd_backfill)

    p = sub.add_parser("export", help="rebuild census.csv and the feeds")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser(
        "legacy", help="convert the 2013-2017 Firebase export in legacy/"
    )
    p.set_defaults(func=cmd_legacy)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
