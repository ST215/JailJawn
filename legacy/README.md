# The 2013–2017 census

Before the daily scraper in this repository, the first JailJawn scraper ran on AWS Lambda and pushed each day's census into a Firebase database. `firebase-export.json` is that database, exported in July 2017: 138 census days between 2013-12-21 and 2017-07-18, most of them in 2016. It is the only record of those years the project has.

`jailjawn legacy` converts it into two CSV files. Run it again if the importer changes; the JSON is never edited.

## What the old page looked like

The city published one wide table. Facility rows had sixteen columns: adult and juvenile counts by sex, workers, furlough, open ward, emergency room trips, "in/out", and a total. Summary rows (the totals, other jurisdictions, CEC, Lehigh County, and similar) had only three: males, females, total.

The 2013 scraper read every row positionally with the sixteen-column headers, so a summary row's total was stored under **Juvenile Male**. Kevin Diem documented this as issue #25 in the original repository. The importer undoes the shift for the rows listed in `SUMMARY_ROWS` in `src/jailjawn/legacy.py` and marks them `shape = summary`.

Two other quirks are carried as-is:

- The city's own sheet sometimes printed `##`, an Excel overflow, in a cell. Those cells are blank here.
- On four days in 2013 and 2014 the published total does not equal males plus females (for example 7,439 + 782 = 8,221 against a printed 8,759). The row is kept as published with the discrepancy in its `note` column, the same policy as the daily record.

## census-2013-2017.csv

One line per row of the old page, per day. Columns: `date`, `row` (a stable key), `shape` (`facility` or `summary`), `males`, `females`, `total`, then the remaining columns of a facility row (`juvenile_males`, `juvenile_females`, `workers_m/f`, `furlough_m/f`, `open_ward_m/f`, `er_trips_m/f`, `in_out_m/f`), and `note`.

Row keys and what they were on the page:

| key | on the page |
|---|---|
| `cfcf` | Curran-Fromhold Correctional Facility |
| `dc` | Detention Center |
| `dc_phsw` | Detention Center Public Health Services Wing |
| `picc` | Philadelphia Industrial Correctional Center |
| `rcf` | Riverside Correctional Facility |
| `hoc` | House of Correction (no longer in the census) |
| `cec` | Community Education Centers, a contracted facility |
| `asd_cambria`, `asd_cannery`, `asd_wrp`, `asd_asdcu`, `asd_mod3` | Alternative and Special Detention units |
| `weekenders`, `liberty`, `roth` | smaller programs and units |
| `in_facility_total`, `nif_total`, `pdp_in_facility`, `pdp_headcount_nif`, `pdp_headcount_nif_oj`, `total` | the page's own subtotals; `total` is the grand total |
| `other_jurisdictions`, `lehigh_county`, `delaware_county`, `state_doc`, `out_of_county`, `juveniles` | people held elsewhere |

## summary.csv

One line per day, for charts: `total`, `males`, `females`, `in_facility`, `not_in_facility`, `other_jurisdictions`, `juveniles_in_facility`, `open_ward`, `emergency_trips`, `workers`, `furlough`, a `note`, then the total, males, females and juveniles for every facility, `in_facility_males`, `in_facility_females`, and the four other-jurisdiction rows.

The site reads this file for its 2013–2017 chapter. It is not the same schema as `census.csv`: the facilities changed, the categories changed, and the old page had no "temporarily not in facility" breakdown per facility beyond workers, furlough, open ward and emergency trips.
