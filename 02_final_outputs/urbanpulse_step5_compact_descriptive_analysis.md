# UrbanPulse Step 5: Compact Descriptive Analysis

This dashboard describes the canonical cleaned layer using observed values only. It does not impute, rank cities, or make inferential claims.

Observed period: `2026-01-01T00:00:00` to `2026-09-24T12:00:00`.
Canonical rows: `1,600`. Raw rows: `1,635`. Exact duplicates removed from the canonical layer: `35`.
Unique canonical timestamps: `1,600`. Primary eligible rows: `1,491`.

## Findings

- Completeness is high for timestamp and city, with 98.0% completeness for zone and 98.0% for traffic and temperature.
- City counts range from 204 to 242 rows. Zone counts range from 32 to 449 rows, with 32 unknown zones.
- Time coverage is balanced across the six four-hour observation slots. September is partial because the source ends on 2026-09-24T12:00:00.
- The sample has one canonical row per unique timestamp after deduplication. This is consistent with the confirmed intentionally sampled design, not a complete city × zone × timestamp panel.
- Quality/provenance signals include: Zone case normalization 430, Temperature probable errors 241, Parking over 100% 113, Exact duplicate rows removed 35, Temperature missing 32, Unknown zones 32, Speed outliers 10.

## Metric ranges

| Metric | Unit | n | Mean | Median | Min | Q1 | Q3 | Max |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Traffic volume | count | 1,568 | 2,050.9 | 2,008.5 | 214 | 1,080.8 | 3,015.2 | 3,999 |
| Average speed | km/h | 1,561 | 38.4 | 37.9 | -10 | 30.4 | 46.1 | 200 |
| Public transport usage | count | 1,600 | 1,298.7 | 1,305 | 100 | 698.2 | 1,889.5 | 2,498 |
| Parking occupancy | % | 1,600 | 68.1 | 67.9 | 5 | 53.9 | 82.1 | 110 |
| Road incidents | count | 1,600 | 2.0 | 2 | 0 | 1 | 3 | 8 |
| Waterlogging reports | count | 1,600 | 1.0 | 1 | 0 | 0 | 2 | 6 |
| Power outage | minutes | 1,600 | 11.9 | 8 | 0 | 3.3 | 16.5 | 127.2 |
| Citizen complaints | count | 1,600 | 8.0 | 8 | 1 | 6 | 10 | 17 |
| Temperature | °C | 1,568 | 28.9 | 28.9 | 6.4 | 24.1 | 33.4 | 53.8 |

## Output

Compact dashboard: `/Users/apple/Documents/Codex/2026-10-01/rea/urban city project/02_final_outputs/urbanpulse_step5_compact_dashboard.html`
Metric summary CSV: `/Users/apple/Documents/Codex/2026-10-01/rea/urban city project/02_final_outputs/urbanpulse_step5_metric_summary.csv`

SQLite integrity check: `ok`.
