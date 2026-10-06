# Stage 5 Current Checkpoint

Last updated: 2026-10-04 22:36 Asia/Kolkata

## Status

Stage 5 chart construction and a separate A4 printable PDF are complete. The portable Stage 6 refresh test is also complete. Native workbook page setup and native Excel refresh certification remain open. The native-PivotTable workbook was not modified.

The authoritative packaged workbook remains:

`02_final_outputs/urbanpulse_phase4_working.xlsx`

Its current SHA-256 is:

`9caf3ef3338515a50149bb26f3b6d98e6e24f57471c00fd26efbdb646ba3bf28`

The archive created before the Stage 5 attempt is:

`04_project_documentation/archives/urbanpulse_phase4_working_before_stage5.xlsx`

It currently has the same SHA-256. This confirms that the attempted chart edits were not promoted into the project package.

## New safe companion

`02_final_outputs/urbanpulse_phase5_dashboard.xlsx`

This companion contains the visible city, zone, and month summary tables plus three non-overlapping editable charts. It is sourced from the authoritative SQLite summary views and is intentionally separate from the native-PivotTable workbook.

Validated totals:

- City: 1,491 records, 3,057,918 traffic-volume units.
- Zone: 1,462 known-zone records, 2,998,962 traffic-volume units.
- Month: 1,491 records, 3,057,918 traffic-volume units.

The companion rendered cleanly and its chart/drawing package parts were present. It does not contain native PivotTables.

The dashboard builder now derives its displayed record counts and unknown-zone scope note from the refreshed SQLite summary data. A disposable Stage 6 refresh confirmed that the tables, charts, labels, and formula-error scan update together.

The A4 PDF companion is:

`02_final_outputs/urbanpulse_phase5_dashboard_A4.pdf`

It is one-page landscape A4 and was rendered for visual inspection with no clipping or overlap observed.

## What was tested

- WPS Office was used as the spreadsheet engine because the available authoring runtime cannot reliably create native PivotTables.
- A disposable copy of the Stage 4 workbook was given a `Dashboard` sheet containing summary source tables for city, zone, and month traffic.
- Ordinary single-series city and zone charts could be inserted from those source tables without altering the native PivotTables.
- The artifact-tool dashboard build created all three charts with fixed non-overlapping cell anchors and passed a formula-error scan.

## Issue encountered

WPS inserted the charts at overlapping default positions. Attempts to reposition them were unstable. The temporary WPS session is therefore not a deliverable and must not be copied over the packaged workbook. The artifact-tool companion solved the chart placement problem. Native workbook A4 page-setup controls remain unverified, but the separate A4 PDF output is complete.

## Safe continuation procedure

1. Start from `02_final_outputs/urbanpulse_phase4_working.xlsx`, not from the temporary WPS session.
2. Create a new disposable copy before making any Stage 5 edit.
3. Keep the native PivotTables on `Pivot_City`, `Pivot_Zone`, and `Pivot_Month` untouched.
4. Build a compact Dashboard with visible city, zone, and month summary tables plus three non-overlapping charts. Use only traffic-volume series; do not include record count as a chart series.
5. Apply A4 print settings with the orientation chosen per sheet, fit-to-width, explicit print areas, and readable table/chart placement.
6. Save, then verify the XLSX package still contains three PivotTable parts, two pivot caches, chart/drawing parts, and the expected raw/canonical sheets.
7. Recheck the city, zone, and month totals before promoting the workbook.
8. On success, update the workflow log, manifest, README, and this handoff file. Keep the native Stage 4 workbook unchanged unless A4 and PivotTable compatibility are verified in a compatible spreadsheet engine.

## Data safety

The raw baseline, SQLite database, canonical values, change log, and native PivotTables were not changed by the Stage 5 attempt. Do not use chart layout work as a reason to modify any of those layers.

## Stage 6 handoff

The portable route is ready for future controlled refreshes. Native Excel/WPS `Refresh All` is not yet an end-to-end chain: the workbook has no query/connection layer linking `tbl_raw` to the canonical and pivot-source tables. Building and verifying that chain requires Excel Desktop or another compatible query-capable engine. See `STAGE5_6_COMPLETION_REPORT.md` for the test counts and results.
