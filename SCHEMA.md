# Data schema

One census day is stored three ways. All three are written by every run.

| Path | What it is |
|---|---|
| `raw/YYYY-MM-DD.html` | The rendered city page, exactly as the browser saw it once the census loaded. Kept so the day can always be re-parsed. Started with 2.0.0; earlier captures live in `debug/`. |
| `data/YYYY-MM-DD.json` | The parsed record described below. |
| `census.csv` | One row per census day with every figure as a column. Rebuilt from `data/` on every run. |

The date in the file name is the **census date** the city printed on the page ("Census for: September 06, 2026"), not the day the scraper ran. The city usually posts a day's census the following morning.

## The JSON record

```json
{
  "schema_version": 2,
  "timestamp": "2026-09-07T17:02:14",
  "scrape_date": "2026-09-07",
  "census_date": "2026-09-06",
  "source_url": "https://www.phila.gov/departments/philadelphia-department-of-prisons/daily-headcount-and-census/",
  "facilities": {
    "in_facility": [ ... ],
    "temporarily_not_in_facility": [ ... ],
    "facility_totals": [ ... ],
    "other_jurisdictions": [ ... ],
    "total_population": [ ... ]
  },
  "warnings": [ "only present when the published figures did not add up" ]
}
```

| Field | Meaning |
|---|---|
| `schema_version` | `2`. Files without this field were written by the 1.x scraper and have since been re-parsed; see [Backfill](#backfill-from-1x). |
| `timestamp` | When the page was captured, local time of the runner. |
| `scrape_date` | The date part of `timestamp`. |
| `census_date` | The date printed on the page. Also the file name. |
| `source_url` | Where the page was fetched from. |
| `facilities` | The five tables, in the order they appear on the page. |
| `warnings` | Present only when a consistency check failed on the published figures. The record is still stored as published. |

Each table is a list of row objects. Keys are the column headers exactly as printed on the page. The first key of every row is its label.

### Cell values

| On the page | Stored as | Meaning |
|---|---|---|
| `1,422` | `1422` | A count. |
| `0` | `0` | The city printed a zero. |
| `-` | `null` | The city left the cell empty. Not the same as zero. In `census.csv` this is an empty cell. |

The 1.x scraper stored dashes as `0`. Every file was re-parsed from its saved page in 2.0.0, so this distinction now holds across the whole dataset.

### The five tables

**`in_facility`**. People physically inside each facility.
Columns: `Facility`, `Adult males`, `Adult females`, `Juvenile males`, `Juvenile females`.
Rows: the eight facilities below, then `In facility headcount total`.

**`temporarily_not_in_facility`**. People a facility is responsible for who are elsewhere at the moment of the count.
Columns: `Facility`, `Male workers`, `Female workers`, `Male furlough`, `Female furlough`, `Male open ward`, `Female open ward`, `Male emergency trips`, `Female emergency trips`.
Rows: the eight facilities, then `Temporarily not in facility total`.

**`facility_totals`**. In facility plus temporarily not in facility, per facility.
Columns: `Facility`, `Males`, `Females`, `Total`.
Rows: the eight facilities, then `In facility headcount and temporarily not in facility total`.

**`other_jurisdictions`**. People the Philadelphia Department of Prisons is responsible for who are held elsewhere.
Columns: `Jurisdiction`, `Males`, `Females`, `Total`.
Rows: `State Department of Corrections (DOC)`, `Juveniles`, `Delaware County`, `Lehigh County`, `All other jurisdictions`, `Total`.

**`total_population`**. The grand total.
Columns: `Category`, `Males`, `Females`, `Total`. (The page leaves this header blank; `Category` is ours.)
Rows: `PDP in facility headcount and temporarily not in facility total`, `Total PDP incarcerated people held in other jurisdictions`, `Total`.

### Facilities

| Row label on the page | CSV key |
|---|---|
| Curran-Fromhold Correctional Facility (CFCF) | `cfcf` |
| Detention Center (DC) | `dc` |
| Detention Center Public Health Services Wing (DC PHSW) | `dc_phsw` |
| Philadelphia Industrial Correctional Center (PICC) | `picc` |
| Riverside Correctional Facility (RCF) | `rcf` |
| Riverside Correctional Facility Alternative and Special Detention Central Unit (RCF ASDCU) | `rcf_asdcu` |
| Riverside Correctional Facility Alternative and Special Detention Modular Unit (RCF ASDMOD3) | `rcf_asdmod3` |
| Weekenders | `weekenders` |

## census.csv

Columns are named `table.row.column`, for example `in_facility.cfcf.adult_males` or `facility_totals.total.total`. The first two columns are `census_date` and `scrape_date`. There are 164 columns. A dash on the page is an empty cell. The full list is produced by `jailjawn.store.csv_columns()`.

## Feeds

Three files at the repository root are rebuilt on every run and served from the site:

| File | What it is |
|---|---|
| `feed.xml` | An Atom feed with one entry per census day for the last 30 days. Subscribe at `https://st215.github.io/JailJawn/feed.xml`. |
| `feed.json` | The same entries as a [JSON Feed](https://jsonfeed.org/). Each item carries `_jailjawn.total` and `_jailjawn.census_date`. |
| `latest.json` | The newest record, exactly as stored in `data/`. |

Entry links point at the site with the census date in the URL fragment, for example `https://st215.github.io/JailJawn/#2026-09-07`, which opens the page on that day.

## The 2013–2017 census

`legacy/` holds the census from the project's first scraper, 138 days between 2013-12-21 and 2017-07-18, in a different schema from the daily record. See [legacy/README.md](legacy/README.md).

## What the checks guarantee

Every record in `data/` has passed these before being committed:

- The census date parsed, was not in the future, and was not older than the newest stored day.
- All five tables were present with exactly the headers above.
- Every table had exactly the rows above, in order.
- No cell was empty text, which is what the page shows before its data has loaded.
- Total population was between 1,000 and 10,000 and moved less than 15% from the previous day.
- The same census date was not already stored with different figures.

These are recorded as `warnings` rather than refusing the day, because the city has published figures that do not add up and the published record is worth keeping:

- Facility rows sum to the total row in each table.
- Males plus females equals total.
- In facility plus temporarily not in facility equals facility totals, per facility.
- Facility totals plus other jurisdictions equals total population.

## Backfill from 1.x

The 1.x scraper matched tables to nearby headings. The heading for "PDP facility totals" contains the phrase "temporarily not in facility", so for every day from 2025-04-04 to 2026-09-07 it stored that table under `temporarily_not_in_facility`, left `facility_totals` empty, and never captured the real temporarily-not-in-facility table.

Because every 1.x run committed the rendered page to `debug/`, 2.0.0 re-parsed all of them. Before replacing a file, the new record was proven against the old one: `in_facility`, `other_jurisdictions` and `total_population` had to match exactly (with the old zeros accepted for new nulls), and the old `temporarily_not_in_facility` had to equal the new `facility_totals`. Every recovered day passed. The report is attached to the 2.0.0 release.

Seven 1.x files (2026-06-19, 06-20, 06-25, 06-28, 06-29, 06-30, 07-01) contained no figures at all: the page had been captured before its data loaded and the scraper wrote the empty placeholder under that day's date. They were removed; those census days were never captured.
