# UrbanPulse City Temperature Benchmarks

## Rule applied

The immutable raw layer and canonical temperature values were not overwritten. Each dataset temperature was compared with a city-level external benchmark. Values within the benchmark range were retained unchanged. Values outside it were retained but flagged for station-level review.

Benchmark period: `2016-01-01` through `2026-10-01`.
Source: NASA POWER Daily API, using daily `T2M_MIN` and `T2M_MAX` at each city-center coordinate, in local solar time.

## Benchmarks

| City | Low benchmark °C | Date | High benchmark °C | Date | Daily observations |
|---|---:|---|---:|---|---:|
| Bengaluru | 9.22 | 2023-01-10 | 40.78 | 2024-04-30 | 3,924 |
| Bhopal | 1.96 | 2019-12-29 | 47.18 | 2016-05-20 | 3,924 |
| Delhi | 0.45 | 2023-01-15 | 48.50 | 2024-05-28 | 3,924 |
| Indore | 4.33 | 2019-12-29 | 47.76 | 2016-05-19 | 3,924 |
| Jaipur | 1.09 | 2019-12-29 | 47.84 | 2024-05-27 | 3,924 |
| Nagpur | 3.59 | 2019-12-29 | 47.80 | 2026-05-21 | 3,924 |
| Pune | 5.96 | 2022-01-25 | 43.20 | 2019-04-26 | 3,924 |

## Dataset comparison

| Status | Rows | Treatment |
|---|---:|---|
| within_benchmark | 1,549 | Retained unchanged |
| above_benchmark | 19 | Retained and flagged, not overwritten |
| below_benchmark | 0 | Retained and flagged, not overwritten |
| missing | 32 | Preserved missing; no imputation |
| unknown_city | 0 | Preserved and flagged |

Out-of-benchmark counts by city: Bengaluru 13, Indore 1, Jaipur 2, Pune 3.

## Interpretation

These are gridded area benchmarks, not exact station certificates for each 4-hour record. An out-of-benchmark value is therefore an evidence flag, not proof of an error. The next correction step would require an exact station/date/time match from an authoritative station record. Until that exists, the dataset value remains unchanged.

NASA POWER Daily API documentation: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
NASA POWER processing methodology: https://power.larc.nasa.gov/docs/methodology/data/processing/

SQLite integrity check: `ok`.
