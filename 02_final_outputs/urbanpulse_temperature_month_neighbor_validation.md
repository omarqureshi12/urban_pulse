# UrbanPulse Temperature Month-and-Neighbor Validation

## Rule applied

- Month plausible and neighboring temperatures of the same city are consistent: retain unchanged.
- Month plausible but neighboring temperatures are inconsistent: flag for review.
- Month implausible and neighboring temperatures are inconsistent: classify as probable error, preserve the raw value, and do not correct automatically.

Month plausibility uses the historical NASA POWER daily envelope for the same city and calendar month over 2016-01-01 through 2026-10-01.
Neighbor consistency uses the nearest preceding and following non-missing observation for the same city. The maximum spread among the target and both neighbors must be no more than 10 °C.

## Results

| Final decision | Rows |
|---|---:|
| retain_unchanged | 611 |
| flag_for_review | 630 |
| probable_error | 241 |
| not_assessed | 118 |

Month plausibility: implausible 319, plausible 1,249, unknown 32.
Neighbor status: consistent 683, inconsistent 871, insufficient 14, unknown 32.
Probable-error counts by city: Bengaluru 34, Bhopal 25, Delhi 28, Indore 42, Jaipur 31, Nagpur 45, Pune 36.

## Data-preservation statement

No raw or canonical temperature was overwritten. Probable errors are classifications only. Any future correction must be supported by a separate source confirmation and a separate change-log entry.

NASA POWER Daily API: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
SQLite integrity check: `ok`.
