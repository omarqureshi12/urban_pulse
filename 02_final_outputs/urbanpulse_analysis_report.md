# UrbanPulse RDBMS and 99% Analysis Report

## Scope

The raw workbook was loaded into SQLite without modifying the source file. Raw values are preserved. The cleaned table only canonicalizes zone capitalization and derives timestamp fields. Missing and questionable values remain flagged rather than silently imputed or corrected.

Source SHA-256: `ae8ff0d3a0f96f8bfef80111c26d2d1f414db16d5e916b38bb75d644d01a0c55`

## Database objects

- `raw_urbanpulse`: immutable source rows
- `urbanpulse_clean`: deduplicated, typed, auditable analytical base
- `deduplication_log`: exact duplicate decisions
- `data_quality_issue`: row-level quality issues and treatments
- `coverage_audit`, `dimension_count`, `missingness_summary`: structural checks
- `metric_summary`, `correlation_result`, `group_test_result`: 99% analysis results
- `data_contract`: authoritative schema, quality rules, and decision gates
- `v_observed_analysis`: complete observed cases with invalid speeds excluded

## Structural result

- Raw rows: **1,635**
- Deduplicated rows: **1,600**
- Exact duplicates removed from analytical base: **35**
- Unique timestamps after deduplication: **1,600**
- Expected four-hour slots in the date range: **1,600**
- Missing four-hour slots: **0**
- Full-panel rows if every city-zone-time combination were required: **56,000**
- Known city-zone-time keys observed: **1,568 (2.80%)**

The file behaves as one sampled observation per timestamp after exact de-duplication. It is not a complete city-zone panel unless most expected observations were omitted before delivery.

## 99% statistical results

The analysis used 99% confidence intervals and Holm correction at alpha = 0.01. It did not impute missing values or overwrite unverified values.

### Metric summaries

| Metric | n | Mean | 99% CI |
|---|---:|---:|---:|
| traffic_volume | 1,568 | 2050.949 | [1980.245, 2122.592] |
| avg_speed_kmph | 1,551 | 38.163 | [37.419, 38.953] |
| public_transport_usage | 1,600 | 1298.672 | [1253.509, 1343.776] |
| parking_occupancy_pct | 1,600 | 68.137 | [66.873, 69.443] |
| road_incidents | 1,600 | 1.959 | [1.871, 2.053] |
| waterlogging_reports | 1,600 | 1.021 | [0.958, 1.091] |
| power_outage_minutes | 1,600 | 11.875 | [11.124, 12.682] |
| citizen_complaints | 1,600 | 7.953 | [7.776, 8.134] |
| temperature_c | 1,568 | 28.932 | [28.488, 29.388] |

### Decision results

- Pearson metric pairs significant after Holm correction at 99%: **0 of 36**.
- City, zone, month, hour, and weekday effects significant after Holm correction at 99%: **0 of 45**.
- Largest absolute Pearson correlation: **0.050**.
- These are non-detection results, not proof that the variables are mathematically independent.

## Final assessment

The RDBMS conversion and audit are complete. The dataset is usable for data-engineering, quality-control, and pipeline-testing work. It should not be treated as a complete city-zone sensor panel without confirmation of the intended grain. Any city, zone, temporal, or policy conclusion should remain provisional until the data owner confirms whether the sparse sampling is intentional.

## Verification

- SQLite `PRAGMA integrity_check`: `ok`
- Raw rows preserved in `raw_urbanpulse`
- Exact duplicates retained in raw table and logged separately
- No automatic imputation
- No unverified value correction
- 99% intervals and alpha = 0.01 multiple-testing controls applied
