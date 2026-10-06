# UrbanPulse Data Contract

This contract is the Step 2 quality gate for the SQLite RDBMS. The raw workbook remains unchanged. Quality treatments apply to the clean analytical layer only.

| Key | Category | Specification | Status | Action required |
|---|---|---|---|---|
| row_grain | Structure | One observed row per four-hour timestamp after exact de-duplication; not a complete city-zone-time panel. | CONFIRMED_INTENTIONAL_SAMPLE | Data owner must confirm whether the sparse sampled grain is intentional. |
| primary_key_clean | Structure | record_id is unique in canonical_cleaned; source row number is retained for traceability. urbanpulse_clean is retained only as a compatibility mirror. | PASS | Use canonical_cleaned for new work. |
| timestamp | Structure | All 1,600 deduplicated timestamps parse and align to the four-hour schedule from 2026-01-01 through 2026-09-24 12:00:00. | PASS |  |
| city | Domain | Seven city labels are present: Bengaluru, Bhopal, Delhi, Indore, Jaipur, Nagpur, Pune. | PASS |  |
| zone | Domain | Five canonical zone labels are present, with 32 missing zone values; case variants were canonicalized only in the clean table. | REQUIRES_OWNER_CONFIRMATION | Confirm whether blank zones may remain unknown. |
| duplicates | Quality | 35 exact duplicate rows are preserved in raw_urbanpulse and excluded from canonical_cleaned; each decision is recorded in the change log. | PASS_WITH_AUDIT_TRAIL |  |
| missing_numeric | Quality | Missing traffic, speed, and temperature values remain NULL in the analytical base; no imputation was applied. | PRESERVE_NULL | Choose an imputation policy only for a separately labeled sensitivity analysis. |
| speed | Quality | Five negative speeds and five speeds above 120 km/h are flagged and excluded from the primary observed analysis; raw values are unchanged. | REQUIRES_OWNER_CONFIRMATION | Confirm whether these are sentinel or sensor errors. |
| parking | Quality | Provisional definition: reported occupied parking capacity percentage at the recorded observation timestamp, conceptually occupied spaces divided by total designated capacity multiplied by 100. The 113 readings above 100% are retained and flagged, not corrected. | PROVISIONAL_DEFINITION_SOURCE_CONFIRMATION_PENDING | Confirm the numerator, denominator, observation window, and whether values above 100% represent over-capacity or another utilization index. |
| temperature | Quality | The Stage 2 base layer retains and flags 27 readings at or above 45 C. Later benchmark and neighboring-value validation contributes additional live temperature flags; no raw value is overwritten. | REQUIRES_SENSOR_CONTEXT | Confirm valid operating range before any correction or exclusion. |
| power_outage | Quality | Provisional definition: source-reported average outage duration in minutes for a zone during each four-hour observation window. Regular, planned, unplanned, and short interruptions are included; overlapping outage durations are added together. The 16 readings above 60 minutes are retained and flagged as plausible under a four-hour window. | PARTIALLY_CONFIRMED_TIMESTAMP_ROLE_PENDING | Confirm whether the timestamp marks the start, end, or label of the four-hour window. |
| analysis_base | Analysis | 1,491 complete observed rows meet the primary metric and speed eligibility rules. | READY_WITH_LIMITATION | Do not generalize to a full panel until row grain is confirmed. |
| confidence_standard | Analysis | Primary intervals use 99% confidence and hypothesis tests use alpha 0.01 with Holm correction. | PASS |  |

## Decision gate

Step 2 is complete. The data owner confirmed that one sampled observation per timestamp is intentional. Analyses must treat the data as an intentionally sampled stream, not as a complete city-zone-time panel.

## Step 3: Two-layer data model

- `raw_urbanpulse` is immutable and preserves the workbook values.
- `canonical_cleaned` stores raw and cleaned values side by side.
- `quality_flag` stores normalized `missing`, `imputed`, `corrected`, `outlier`, and `unknown` flags.
- `change_log` records actual canonicalization and de-duplication actions.
- `v_primary_observed` is observed-only and contains no imputed values.
- `v_primary_zone_complete` is the observed-only, known-zone subset for primary analyses requiring zone; it contains 1,462 rows and does not delete the underlying raw or canonical records.
- Imputation is confined to the Stage 3 sensitivity tables: `canonical_imputed_sensitivity`, `imputation_method`, and `imputation_value`. Imputed values are excluded from primary analysis.

## Stage 2 refresh

`03_reproducibility_scripts/refresh_stage2_layers.py` reads the table-shaped raw workbook and deterministically rebuilds the raw and canonical layer tables in a supplied SQLite database. It performs no imputation. After a new source refresh, rerun the later sensitivity, model, provenance, and fitness stages before publishing results.
