# UrbanPulse Two-Layer Data Model

The live SQLite package uses an auditable two-layer RDBMS design. The raw source is immutable. `canonical_cleaned` keeps raw and cleaned values side by side. Primary analysis uses observed values only.

## Live database status

- Raw rows: **1,635**
- Canonical cleaned rows: **1,600**
- Primary observed rows: **1,491**
- Zone-complete primary rows: **1,462**
- Change-log entries: **465**
- All live quality-flag entries: **1,158**
- Stage 2 base-layer flags: **763**
- Sensitivity-only imputation flags: **135**
- Corrected/normalized flags: **430**
- SQLite integrity: **ok**

The live flag total includes later temperature-validation and sensitivity-analysis annotations. The Stage 2 refresh script intentionally creates the base-layer total of 763 and performs no imputation. The Stage 3 sensitivity layer has now been promoted and contains the 135 sensitivity-only imputation flags and outputs. After any new source refresh, Stage 3 must be rerun before publishing results.

## Live quality flags

| Flag type | Field | Count |
|---|---|---:|
| corrected | zone | 430 |
| imputed | avg_speed_kmph | 39 |
| imputed | temperature_c | 32 |
| imputed | traffic_volume | 32 |
| imputed | zone | 32 |
| missing | avg_speed_kmph | 39 |
| missing | temperature_c | 32 |
| missing | traffic_volume | 32 |
| missing | zone | 32 |
| outlier | avg_speed_kmph | 10 |
| outlier | parking_occupancy_pct | 113 |
| outlier | power_outage_minutes | 16 |
| outlier | temperature_c | 287 |
| unknown | zone | 32 |

## Authority and compatibility

- `raw_urbanpulse` is the immutable source layer.
- `canonical_cleaned` is the authoritative raw/cleaned analytical layer for new work.
- `quality_flag` stores `missing`, `imputed`, `corrected`, `outlier`, and `unknown` flags.
- `change_log` records canonicalization and de-duplication actions.
- `urbanpulse_clean` remains as a compatibility mirror for legacy scripts. New scripts should use `canonical_cleaned`.
- `v_primary_observed` excludes missing metric values and invalid speeds and contains no imputed values. It remains available for analyses that do not require zone.
- `v_primary_zone_complete` contains 1,462 observed-only rows with known zones and is required for all primary analyses that use zone.

## Refresh procedure

`03_reproducibility_scripts/refresh_stage2_layers.py` reads the table-shaped raw workbook and deterministically rebuilds the raw and canonical layer tables in a supplied SQLite database, including the observed-only `v_primary_zone_complete` view. It was tested on a disposable copy with 1,635 raw rows, 1,600 canonical rows, 35 exact duplicate rows excluded, 465 change-log entries, 763 Stage 2 base flags, and SQLite integrity `ok`.

Do not publish a new refreshed analysis database until the later sensitivity, model, provenance, and fitness steps have been rerun.
