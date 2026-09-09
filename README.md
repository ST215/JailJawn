# JailJawn

A daily record of how many people are held by the Philadelphia Department of Prisons, collected from the city's [daily headcount and census page](https://www.phila.gov/departments/philadelphia-department-of-prisons/daily-headcount-and-census/) and stored in this repository as data files.

**See it: [st215.github.io/JailJawn](https://st215.github.io/JailJawn/)** — one glyph for every person held, a timeline you can scrub, and what the numbers say.

The city publishes one day at a time and does not include this data in its open data portal. This repository is the history. It started as a civic hackathon project with the City of Philadelphia and a way to learn Python; the city gave permission to collect the page.

## The data

| File | What it holds |
|---|---|
| [`census.csv`](census.csv) | One row per census day, every figure as a column. Start here for charts and spreadsheets. |
| `data/YYYY-MM-DD.json` | One record per census day with the five tables from the page. |
| `raw/YYYY-MM-DD.html` | The page as captured, so any day can be re-parsed. |
| `debug/` | Page captures from before 2.0.0. Kept as the archive those days were re-parsed from. |
| `legacy/` | The 2013–2017 census from the project's first scraper, 138 days, converted from its Firebase export. See [legacy/README.md](legacy/README.md). |
| `feed.xml`, `feed.json`, `latest.json` | Subscribe to new census days. See [SCHEMA.md](SCHEMA.md#feeds). |

The file name is the census date printed on the page, not the day it was collected. See [SCHEMA.md](SCHEMA.md) for every field, what a blank cell means, and which checks each record has passed.

Coverage runs from 2025-04-04. Days the city did not post, or the scraper missed, are simply absent.

## How it works

A GitHub Actions workflow runs twice a day and:

1. Opens the page in headless Chromium. The tables are rendered in the browser by a small app the city hosts, so plain HTTP returns nothing.
2. Saves the page to `raw/`.
3. Parses the five tables, identifying each by its exact header row.
4. Validates the result. The census date must be real and new, every table and row must be present, no cell may be the page's pre-load placeholder, and the total must be plausible. A record that fails is not stored and the run fails loudly.
5. Writes the JSON record, rebuilds `census.csv`, and commits. If the city has not posted a new day yet, nothing is committed.

Arithmetic that does not close (the city has published figures that did not add up) is stored as a `warnings` field on the record rather than refusing the day.

## Running it yourself

Requires [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/ST215/JailJawn.git
cd JailJawn
uv sync
uv run playwright install chromium

uv run jailjawn scrape              # fetch today's census and store it
uv run jailjawn scrape --dry-run    # fetch and validate, write nothing
uv run jailjawn scrape --html raw/2026-09-07.html   # parse a saved page
uv run jailjawn validate data/*.json                # re-check stored records
uv run jailjawn export              # rebuild census.csv from data/
uv run pytest                       # run the tests
```

`jailjawn backfill` re-parses every capture in `debug/` and writes a proof report to `build/`. It was used once, for 2.0.0, and is kept in case the parser ever changes again.

## The site

`site/` is a static page with no build step. It fetches `census.csv` from this repository when it loads, so it is always current, and falls back to the copy deployed with it. The crowd on the front page is laid out with [pretext](https://github.com/chenglou/pretext), vendored in `site/vendor/`. GitHub Pages deploys it whenever `site/` changes on master.

To work on it locally:

```bash
python3 -m http.server 8000 --directory site
# then open http://localhost:8000/
```

## History

- **1.0.0** is the last hand-written version, tagged as a record of the original project.
- **1.1.0** fixed a timeout that had started failing the daily run.
- **2.0.0** rewrote the parser, corrected a table-mapping bug present in every earlier file, re-parsed the full history from the saved pages, added validation, the CSV, tests, and the raw archive. The release notes carry the backfill report.

## Contact and credits

Stanley Griggs, [stanleygriggs.com](http://www.StanleyGriggs.com/), [@ST215](http://www.twitter.com/ST215). Issues and pull requests are welcome.

Everyone who has contributed since the 2013 hackathon, across every repository the project has lived in, is listed in [CONTRIBUTORS.md](CONTRIBUTORS.md).
