# Phase 4: Refreshable Excel Workflow

Status: Stages 1-6 complete on the portable SQLite/Python route; Stage 5 charts and A4 PDF complete; native workbook refresh remains open.

## Seven-stage plan

1. Protect the baseline.
2. Build the canonical cleaning layer.
3. Separate primary and sensitivity analysis populations.
4. Create native PivotTables.
5. Connect charts and preserve the A4 print layout.
6. Test the refresh workflow with a controlled new record.
7. Document, validate, and package the final refreshable workbook.

## Stage 1 — Protect the baseline

Completed on 2026-10-04.

- Preserved `02_final_outputs/urbanpulse_refreshable.xlsx` as the unchanged raw-table baseline.
- Created `02_final_outputs/urbanpulse_phase4_working.xlsx` as the working copy for the remaining phase.
- Confirmed both files have the same SHA-256 hash:
  `412885c2bd75d14f17eae885b7cd17393e18d17ece57619041fd54b79063d730`
- Confirmed the working copy passes the XLSX package integrity test.
- Confirmed the workbook contains one sheet, one table named `tbl_raw`, range `A1:M1636`, 1,635 observations, and 13 columns.
- Confirmed the raw-cell values and approved raw-layer structure are unchanged.

## Issue report before Stage 2

No blocking issue was found in Stage 1.

Known implementation limitation: the current workbook is a raw-table foundation. Building genuine Power Query transformations and native Excel PivotTables requires Excel Desktop or another compatible Excel engine. The existing spreadsheet authoring runtime can validate and format the workbook, but it should not be treated as proof that native Excel refresh behavior exists.

## Stage 2 entry condition

After confirmation, build or harden the canonical cleaning layer from the raw input while preserving raw values, cleaned values, quality flags, and a separate change log. Do not modify `urbanpulse_refreshable.xlsx` or any file under `01_source_materials/`.

## Stage 2 — Audit findings before remediation

The existing RDBMS already contained a canonical two-layer implementation, so Stage 2 was partly complete. The audit found these issues:

1. **Refresh-input gap — resolved:** added `03_reproducibility_scripts/refresh_stage2_layers.py`, which reads the table-shaped raw workbook and rebuilds the raw and canonical layer tables deterministically.
2. **Two canonical sources — resolved by authority rule:** `canonical_cleaned` is now the authoritative layer for new work. `urbanpulse_clean` remains only as a compatibility mirror for legacy scripts.
3. **Documentation mismatch — resolved:** regenerated `02_final_outputs/urbanpulse_data_layers.md` from the live database and separated Stage 2 base flags from later sensitivity-only flags.
4. **Unused empty database — resolved:** moved `02_final_outputs/urbanpulse.sqlite` to `04_project_documentation/archives/urbanpulse.sqlite.empty`. The active database remains `urbanpulse_rdbms.sqlite`.

No source values were changed. The refresh script was tested on a disposable copy of the active database and produced: 1,635 raw rows, 1,600 canonical rows, 35 exact duplicate rows excluded, 1,491 primary observed rows, 465 change-log entries, 763 Stage 2 base flags, zero imputed Stage 2 values, and SQLite integrity `ok`. The active database was backed up before the archive cleanup and was not overwritten, because it contains later-stage temperature and sensitivity outputs that must be rerun after any future source refresh.

## Stage 3 — Separate primary and sensitivity populations

Completed on 2026-10-04.

- Ran the imputation workflow in an isolated project copy before promotion.
- Created a recoverable pre-promotion backup at `04_project_documentation/archives/urbanpulse_rdbms_before_stage3.sqlite`.
- Promoted the validated database and Stage 5A output files into `02_final_outputs/`.
- Preserved the observed-only primary view `v_primary_observed` at 1,491 rows; it contains no imputed values.
- Preserved the separate `canonical_imputed_sensitivity` layer at 1,600 rows with 135 imputation events across four methods.
- Used mean imputation for `traffic_volume`, `avg_speed_kmph`, and `temperature_c`; used mode imputation for `zone`. No skewed numeric field required median imputation in this dataset.
- All 135 imputed quality flags are marked `Sensitivity only; excluded from primary analysis.`
- Twenty-nine primary rows retain an unknown zone as `NULL`; they remain available for analyses that do not require zone. The explicit `v_primary_zone_complete` view contains 1,462 rows and is required for all primary analyses that use zone.
- Protected-copy and promoted-database SQLite integrity checks passed.

## Stage 4 — Create native PivotTables

Completed on 2026-10-04 in the separate working workbook.

- Used WPS Office as the compatible spreadsheet engine because the available authoring runtime cannot create reliable native PivotTables and LibreOffice was not available.
- Preserved the immutable raw baseline and archived the prior working workbook as `04_project_documentation/archives/urbanpulse_phase4_working_before_stage4.xlsx` before promotion.
- Promoted `02_final_outputs/urbanpulse_phase4_working.xlsx` only after native PivotTable and package-level validation.
- Added native PivotTables on sheets `Pivot_City`, `Pivot_Zone`, and `Pivot_Month`.
- `Pivot_City` and `Pivot_Month` use the observed-only `tbl_primary_observed` source with 1,491 rows. `Pivot_Zone` uses `tbl_zone_pivot_source` with 1,462 known-zone rows.
- Each summary includes observation count and traffic-volume sum. The validated totals are 1,491 observations and 3,057,918 traffic-volume units for city/month summaries, and 1,462 observations and 2,998,962 traffic-volume units for the zone summary.
- Kept `source_row_number` in the full analysis tables for lineage, but excluded it from `tbl_zone_pivot_source` so it cannot appear as an accidental zone metric.
- Verified the workbook contains three native PivotTable parts and two native pivot caches. The zone cache points to `tbl_zone_pivot_source`; no `source_row_number` data field appears in the zone PivotTable.
- Artifact-level inspection found no formula errors and confirmed the visible city, zone, and month summary values.

### Stage 4 issue report

One non-blocking implementation issue occurred: WPS initially placed the lineage field `source_row_number` in the zone PivotTable as an extra summed metric. This was corrected by creating the dedicated `tbl_zone_pivot_source` table. No raw values, canonical values, database rows, or lineage records were changed. The previous working workbook remains recoverable in the archive.

## Stage 5 — Current checkpoint: charts and A4 print layout

Started on 2026-10-04; chart portion completed in a separate companion and a one-page landscape A4 PDF companion was visually verified.

- The protected raw-layer workbook and the SQLite database were not changed.
- A disposable WPS workbook was used to test ordinary chart insertion from summary tables. This confirmed that single-series city and zone charts can be created without changing the native PivotTables.
- WPS chart placement was unstable: inserted charts overlapped the source tables and each other during repositioning. The monthly chart was not successfully completed, and no Stage 5 workbook was promoted.
- The packaged `02_final_outputs/urbanpulse_phase4_working.xlsx` remains the validated Stage 4 workbook. Its SHA-256 is `9caf3ef3338515a50149bb26f3b6d98e6e24f57471c00fd26efbdb646ba3bf28`.
- The recoverable archive `archives/urbanpulse_phase4_working_before_stage5.xlsx` currently has the same hash, so the attempted Stage 5 edits are not part of the project package.
- Created `02_final_outputs/urbanpulse_phase5_dashboard.xlsx` as a safe presentation companion. It contains three non-overlapping native charts and visible summary tables sourced from the authoritative SQLite summaries.
- Verified city totals of 1,491 records / 3,057,918 traffic units, zone totals of 1,462 records / 2,998,962 traffic units, and month totals of 1,491 records / 3,057,918 traffic units.
- Artifact-level formula scan found no formula errors and the rendered Dashboard was visually checked.
- Native workbook A4 print settings and full Excel-native refresh could not be safely configured or verified in the available authoring runtime. A separate one-page landscape A4 PDF was generated and visually verified.
- The dashboard builder derives record counts and the unknown-zone scope note from the authoritative SQLite summary data; no dashboard count labels are hardcoded.

See `STAGE5_CURRENT_CHECKPOINT.md` and `STAGE5_6_COMPLETION_REPORT.md` for the exact status. The chart companion and A4 PDF are ready for review but do not replace the native PivotTable workbook.

## Stage 6 — Controlled refresh test

Portable refresh test completed end to end on 2026-10-04 in disposable copies.

- Added controlled record `URB_TEST_STAGE6` to a temporary raw-table workbook.
- Portable refresh produced 1,636 raw rows, 1,601 canonical rows, and 1,492 observed-only rows.
- Rebuilt the separate imputation-sensitivity layer with 1,601 rows and 135 sensitivity imputation events; no imputed values entered the primary observed-only view.
- Regenerated the dashboard from the refreshed disposable database; record-count labels updated to 1,492 observed-only and 1,463 known-zone rows, the three charts remained present, and the formula-error scan found no errors.
- SQLite integrity remained `ok`; no imputed Stage 2 flags were introduced.
- The production raw workbook, production database, and native-PivotTable workbook were not changed; the presentation companion was regenerated from the unchanged production database after validation.
- Native Excel `Refresh All` is not an end-to-end chain in the current workbook because no Power Query, query-table, or workbook connection links `tbl_raw` to the canonical and pivot-source tables. Building that chain requires Excel Desktop or another compatible query-capable engine; the portable SQLite/Python route is the verified Stage 6 implementation.
