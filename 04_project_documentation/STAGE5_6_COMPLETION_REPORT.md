# Stage 5 and Stage 6 Completion Report

Date: 2026-10-04

## Stage 5 - printable dashboard

Completed what could be safely completed without modifying the native-PivotTable workbook.

- Created `02_final_outputs/urbanpulse_phase5_dashboard.xlsx` with three editable charts and visible summary tables.
- Created `02_final_outputs/urbanpulse_phase5_dashboard_A4.pdf` as a one-page landscape A4 printable output.
- Visually rendered and checked the PDF. Tables, charts, labels, and scope notes are readable with no clipping or overlap.
- City and month summaries use 1,491 observed-only records and 3,057,918 traffic-volume units.
- Zone summary uses 1,462 known-zone observed-only records and 2,998,962 traffic-volume units.
- The native-PivotTable workbook was not overwritten.
- The dashboard builder now derives all displayed record counts and the unknown-zone scope note from the refreshed summary data rather than hardcoding them.

## Stage 6 - controlled refresh test

Passed end to end in disposable copies; the production presentation companion was regenerated from the unchanged production SQLite database after validation.

- Appended controlled record `URB_TEST_STAGE6` to a temporary copy of the raw-table workbook.
- Refreshed a temporary SQLite database with the portable Stage 2 refresh script.
- Raw rows: 1,635 -> 1,636.
- Canonical rows: 1,600 -> 1,601.
- Observed-only rows: 1,491 -> 1,492.
- Exact duplicate rows removed: 35.
- Stage 2 imputed flags: 0.
- Rebuilt the separate imputation-sensitivity layer: 1,601 rows and 135 sensitivity imputation events; no imputed values entered the primary observed-only view.
- Refreshed dashboard test values and labels: 1,492 observed-only records, 1,463 known-zone records, and 29 unknown-zone records; all three charts remained present and non-overlapping, and the formula-error scan found no errors.
- SQLite integrity: `ok`.
- The controlled record was present in both the raw and canonical temporary tables with `quality_status = observed`.
- No production raw workbook, production database, or native-PivotTable workbook was changed; only the presentation companion was regenerated from the same production database after the test.
- The bundled LibreOffice Calc runtime was also tested on a disposable native-workbook copy. It preserved the PivotTable package parts, but the PivotTable cache counts remained 1,491 city/month rows and 1,462 zone rows after the raw-only test because the workbook's static source tables were unchanged; LibreOffice therefore did not solve the missing raw-to-canonical refresh chain.

## Remaining user-side items

- If the workbook itself must carry native A4 page setup, open the Stage 5 dashboard workbook in Excel or WPS, set A4 and fit-to-width, then export and review the PDF.
- Full native PivotTable/chart refresh after adding a raw workbook row is not available in the current workbook: package inspection shows no Power Query, query-table, or workbook connection linking `tbl_raw` to the canonical and pivot-source tables. The available WPS session was also not stable enough to build that chain, and Microsoft Excel Desktop is not installed in the current environment.
- Source-metadata limitations remain data-owner items rather than Stage 6 refresh defects: temperature station/source, authoritative zone mapping, average-speed semantics, and parking measurement semantics.

## Stage 6 decision

The portable SQLite/Python refresh route is ready for the next controlled run. The remaining native-workbook remediation requires Excel Desktop or another compatible query-capable engine to build the raw → canonical → primary query chain and then verify `Refresh All` for PivotTables, charts, and empty states. If native refresh is not a requirement, no Stage 6 remediation remains on the portable route.
