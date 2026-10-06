# UrbanPulse Stage 4: Data-Quality Decisions

Stage 4 classifies issues as confirmed errors, valid extremes, or unknowns. It does not overwrite the immutable raw layer.

## Decisions

| Issue | Class | Count | Source status | Treatment |
|---|---|---:|---|---|
| duplicates | confirmed_error | 35 | confirmed_by_internal_key_check | Exclude exact duplicate rows from canonical_cleaned; preserve all raw rows and log the removal. |
| outage_over_60 | valid_extreme | 16 | window_assumption_pending | Retain and flag. |
| parking_over_100 | unknown | 113 | owner_confirmation_required | Retain and flag; do not cap at 100. |
| speed_extreme | unknown | 5 | not_confirmed | Retain 150/200 values and flag them. |
| speed_missing | unknown | 39 | not_confirmed | Preserve NULL; do not impute in the primary layer. |
| speed_negative | unknown | 5 | not_confirmed | Retain raw -10 values, flag, and do not replace them with +10. |
| temperature_high | unknown | 27 | historical_source_match_pending | Preserve the recorded temperature and flag it. Do not replace it without an exact city-date station source match. |
| temperature_missing | unknown | 32 | not_confirmed | Preserve NULL; do not impute in the primary layer. |
| traffic_missing | unknown | 32 | not_confirmed | Preserve NULL; do not impute in the primary layer. |
| zone_case | confirmed_error | 430 | confirmed_by_controlled_vocabulary | Canonicalize case only in canonical_cleaned; preserve raw zone text. |
| zone_missing | unknown | 32 | not_confirmed | Preserve NULL and flag unknown; do not infer a zone. |

## Explicit non-corrections

- The five `-10` speed values were not changed to `+10`.
- No high-temperature value was replaced.
- No primary-layer imputation was performed.
- Numeric values remain available in raw and canonical side-by-side columns.

## Temperature source confirmation

IMD Climate Services: https://mausam.imd.gov.in/responsive/climate_services.php
IMD City Weather Reports: https://mausam.imd.gov.in/imd_latest/contents/current_weather.php

These official services establish the appropriate source family, but the public pages do not provide an exact historical city-date-station match for the 27 flagged records. Therefore the temperatures remain unknown and unchanged. A correction would require the matching historical station record and a logged source reference for each affected row.

SQLite integrity check: `ok`.
