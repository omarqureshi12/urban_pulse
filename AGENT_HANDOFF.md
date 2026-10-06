# UrbanPulse Project Handoff

Last updated: 2026-10-05 06:56 Asia/Kolkata

This file is the starting point for another AI agent or analyst. Read it before changing any project artifact.

## Current status

The UrbanPulse college project analysis is complete through the nine requested analysis steps and the dashboard/presentation packaging work. The project has been classified as:

`FIT_ONLY_DESCRIPTIVE_REPORTING`

The dataset is intentionally sampled. It should not be treated as a complete city-zone panel, an operational-control feed, proof of causality, or a production forecasting source.

The most recent completed core work is Stage 6 of the refreshable workflow on the portable SQLite/Python route. Stage 5 has a validated presentation companion and one-page A4 PDF. Stage 6 passed end to end in disposable copies: canonical refresh, primary observed-only refresh, imputation-sensitivity rebuild, dashboard summaries, chart preservation, dynamic record-count labels, and integrity checks. Native refresh inspection found that the native-PivotTable workbook has no Power Query, query-table, or workbook connection linking `tbl_raw` to the canonical and pivot-source tables; its PivotTables currently read static output tables. The native workbook remains unchanged. `02_final_outputs/urbanpulse_refreshable.xlsx` remains the protected raw-layer baseline, and `02_final_outputs/urbanpulse_phase4_working.xlsx` is the separate working workbook with native PivotTables. The raw data is stored as an Excel Table named `tbl_raw`. For the non-Excel route, Stage 2 has a tested Python-to-SQLite refresh script at `03_reproducibility_scripts/refresh_stage2_layers.py`, and Stage 3 has a separate imputation sensitivity script at `03_reproducibility_scripts/run_step5a_imputation_sensitivity.py`.

The latest work also verified a live Google Sheets refresh route. The user-provided workbook was successfully authorized and refreshed through its linked Apps Script project. The raw `Sheet1` tab was preserved, while the `Refresh_` layers, `Dashboard_Refresh`, and `Refresh_Status` were rebuilt and verified in the live workbook. This route is now documented in `04_project_documentation/GOOGLE_SHEETS_REFRESH_WORKFLOW.md`; it complements the portable SQLite/Python route and does not replace the packaged local XLSX artifacts.

## Current checkpoint for the next agent

- Stage 5 companion outputs and the portable Stage 6 route are complete. Read `04_project_documentation/STAGE5_CURRENT_CHECKPOINT.md` and `04_project_documentation/STAGE5_6_COMPLETION_REPORT.md` before touching the workbook.
- The live Google Sheets route was successfully refreshed and verified on 2026-10-05. Read `04_project_documentation/GOOGLE_SHEETS_REFRESH_WORKFLOW.md` before rerunning or modifying that route.
- The current packaged working workbook is still the validated Stage 4 artifact. Its SHA-256 is `9caf3ef3338515a50149bb26f3b6d98e6e24f57471c00fd26efbdb646ba3bf28`.
- The pre-Stage-5 archive currently has the same SHA-256, confirming that no Stage 5 chart edit was promoted.
- A disposable WPS session was used to test ordinary chart insertion on a temporary copy. City and zone charts could be created from presentation summary tables, but chart placement became unstable and overlapped the source tables. The monthly chart was not successfully added. The temporary session must not be treated as the final output.
- A safe companion workbook, `02_final_outputs/urbanpulse_phase5_dashboard.xlsx`, was created with three non-overlapping charts and visible summary tables. Its city, zone, and month totals reconcile to the authoritative SQLite views. It is a presentation companion, not a replacement for the native-PivotTable workbook.
- A4 print settings remain unverified for the companion workbook. Do not claim Stage 5 fully complete until A4 export is verified in a compatible spreadsheet engine.
- A one-page landscape A4 PDF companion was generated and visually verified. Native workbook page setup remains a user-side item if the `.xlsx` itself must carry those settings.
- The controlled Stage 6 refresh passed in disposable copies, including the sensitivity layer and dashboard regeneration. Native `Refresh All` is not a working end-to-end chain in the current workbook because the required query/connection layer is absent; building that chain requires Excel Desktop or another compatible query-capable engine.
- The bundled LibreOffice Calc runtime was tested on a disposable raw-row copy. It preserved the PivotTable package parts but left the cache counts unchanged because the static pivot-source tables were not refreshed from `tbl_raw`.
- The native PivotTables and their source tables remain intact in the packaged working workbook. The raw baseline, SQLite database, and canonical data were not changed during the Stage 5 attempt.
- The safest continuation is to use `refresh_stage2_layers.py` followed by `run_step5a_imputation_sensitivity.py` and the dashboard builder for portable refreshes. If native Excel/WPS refresh certification is required, use a disposable copy of the native workbook, append one controlled record, run **Refresh All**, and verify every PivotTable, chart, quality flag, and empty state before promotion. If the engine cannot provide that proof, leave the native workbook unchanged.

## Latest verified progress — Google Sheets route

Completed on 2026-10-05.

- Live workbook: [UrbanPulse Google Sheet](https://docs.google.com/spreadsheets/d/1gZQSJngvZwvKNsy1FVyWOBwp_Rw6eQ4ceb-QSrDMV9U/edit)
- Apps Script project: [UrbanPulse Apps Script project](https://script.google.com/home/projects/18n2ExEh48ld4aF75GfK60qgTt_2LxX3wQbqnf4dTtDAglJ12qjabkZ-2/edit)
- The standard Google authorization prompt was completed and `setupUrbanPulse` finished successfully.
- The raw `Sheet1` tab was not overwritten. The rebuild reads from `Sheet1` and writes only derived/output tabs.
- Verified derived tabs: `Refresh_Canonical`, `Refresh_Primary`, `Refresh_Zone_Complete`, `Refresh_Zone_Pivot_Source`, `Refresh_Quality_Flags`, `Refresh_Change_Log`, `Refresh_Sensitivity`, `Refresh_Imputation_Events`, `Refresh_City`, `Refresh_Zone`, `Refresh_Month`, `Dashboard_Refresh`, and `Refresh_Status`.
- Verified `Refresh_Status` counts: 1,635 raw rows; 1,600 canonical rows; 1,491 primary observed rows; 1,462 known-zone rows; 763 quality flags; 465 change-log entries; 1,600 sensitivity rows; and 135 sensitivity imputation events.
- Verified policy text in the sheet: primary analysis uses observed values only; imputation is sensitivity-only; refresh rebuilds from `Sheet1` and never overwrites the raw tab.
- Verified `Dashboard_Refresh` contains city, zone, and month summary tables plus charts. The workbook showed a saved-to-Drive status after the refresh.
- For future live refreshes, open the Apps Script project and run `refreshUrbanPulse`. Use `setupUrbanPulse` only if the installable refresh trigger must be recreated.
- This live route is cloud-hosted. The local project stores the links, verified counts, operating rules, and handoff instructions; it does not duplicate the Apps Script source code as a local file.

## First files to read

1. `README.md` for the package map.
2. `04_project_documentation/BASELINE_MANIFEST.md` for package checks and fingerprints.
3. `04_project_documentation/OPEN_ISSUES.md` for known limitations.
4. This file for the current handoff state and next action.

## Data and analysis decisions already approved

- Preserve the immutable raw layer. Do not edit or silently correct raw values.
- Keep raw and cleaned values side by side in the canonical layer, with a separate change log.
- Retain quality flags: `missing`, `imputed`, `corrected`, `outlier`, and `unknown`.
- Use observed values only for primary statistical analysis. Imputation is sensitivity analysis only.
- Use `v_primary_zone_complete` for all primary analyses requiring a known zone. It contains 1,462 observed-only rows; `v_primary_observed` remains available for analyses that do not require zone.
- For missing numeric values, sensitivity work used mean for approximately normal variables and median for skewed variables. Mode was used for categorical values.
- Quality decisions classify issues as confirmed error, valid extreme, or unknown. Unknown values remain preserved and are excluded or analyzed separately.
- Temperature validation follows the approved rule: plausible month plus consistent neighboring city temperatures means retain; plausible month plus inconsistent neighbors means flag; implausible month plus inconsistent neighbors means probable error, while preserving the raw value and logging any correction separately. Do not replace values with generic internet averages.
- The dataset grain is an intentional sample. The raw layer contains 1,635 rows and 1,600 distinct record IDs. The canonical layer contains 1,600 deduplicated rows, with 1,491 rows eligible for the primary analysis.
- Power outage definition: four-hour observation window, average outage duration, zone-level geographic scope, random event types including regular, planned, and short interruptions, with overlapping events added together.
- The final decision is descriptive reporting only. Do not make operational, safety, causal, KPI-commitment, or production-forecasting claims.

## Completed deliverables

- `02_final_outputs/urbanpulse_rdbms.sqlite` — packaged SQLite/RDBMS analysis database with promoted Stage 3 sensitivity layers.
- `02_final_outputs/urbanpulse_schema.sql` — schema and layer definitions.
- `02_final_outputs/urbanpulse_data_contract.md` — field and data contract.
- `02_final_outputs/urbanpulse_analysis_report.pdf` — supplied narrative report.
- `02_final_outputs/urbanpulse_analysis_pivots_charts.xlsx` — cleaned static workbook with A4 print settings. It is not a native refreshable PivotTable workbook.
- `02_final_outputs/urbanpulse_refreshable.xlsx` — raw-layer Excel Table workbook, containing `tbl_raw` over `A1:M1636`. Values match the packaged raw source exactly; no cleaning has been applied here.
- `02_final_outputs/urbanpulse_phase4_working.xlsx` — promoted Stage 4 working workbook containing the canonical and observed-only analysis tables plus native `Pivot_City`, `Pivot_Zone`, and `Pivot_Month` PivotTables. Do not replace the raw-layer baseline with this file.
- `02_final_outputs/urbanpulse_phase5_dashboard.xlsx` — safe Stage 5 presentation companion with three charts and summary tables; its labels are generated from the authoritative SQLite summaries. It does not contain native PivotTables and does not replace the Stage 4 working workbook.
- `02_final_outputs/urbanpulse_phase5_dashboard_A4.pdf` — visually verified one-page landscape A4 printable dashboard.
- `04_project_documentation/archives/urbanpulse_phase4_working_before_stage4.xlsx` — recoverable pre-Stage-4 working workbook backup.
- `03_reproducibility_scripts/refresh_stage2_layers.py` — Stage 2 raw-workbook-to-SQLite layer refresh. It creates the base canonical layer without imputation.
- `03_reproducibility_scripts/run_step5a_imputation_sensitivity.py` — Stage 3 sensitivity layer rebuild using mean/median/mode rules without changing raw or canonical observed values.
- `03_reproducibility_scripts/apply_zone_complete_primary_policy.py` — Recreates the non-destructive known-zone primary view.
- `02_final_outputs/urbanpulse_step5a_imputation_sensitivity.md` — Stage 3 method and validation report.
- `02_final_outputs/UrbanPulse_College_Project_Presentation_v3.pptx` — approved college presentation.
- `05_dashboard/urbanpulse_app.py` and `05_dashboard/urbanpulse_data.py` — Streamlit dashboard source and data access layer.
- `04_project_documentation/PHASE3_APPLICATION_TEST_REPORT.md` — browser-level dashboard test record.
- `04_project_documentation/PRESENTATION_VALIDATION_REPORT.md` — presentation validation record.

## Recommended next workflow

The phase is being executed in seven controlled stages. Stages 1 through 6 are complete on the portable SQLite/Python route. Stage 5 charts and a printable A4 PDF are complete in separate companion outputs. Native Excel refresh remains blocked until a query/connection chain is built in Excel Desktop or another compatible engine. See `04_project_documentation/PHASE4_REFRESHABLE_WORKFLOW.md`, `04_project_documentation/STAGE5_CURRENT_CHECKPOINT.md`, and `04_project_documentation/STAGE5_6_COMPLETION_REPORT.md`.

### Refreshable Excel build

1. Use `02_final_outputs/urbanpulse_refreshable.xlsx` as the starting workbook.
2. Build a Power Query cleaning layer sourced from `tbl_raw`.
3. Preserve raw and cleaned columns side by side where a value changes, and add the quality flags and change log.
4. Keep primary-analysis outputs based on observed values only. Keep imputed outputs in a separately named sensitivity query or table.
5. Connect the compact charts and preserve the A4 print layout. The current native PivotTables are based on the observed-only analysis tables, not directly on the raw table.
6. For the portable route, append a controlled new row to a disposable copy, run the Stage 2 refresh, rebuild Stage 3 sensitivity outputs, regenerate the dashboard, and verify counts, flags, charts, and integrity. For the native Excel route, append a controlled new row to `tbl_raw`, select **Refresh All**, and confirm that the canonical layer, PivotTables, charts, quality flags, and empty states update correctly.
7. Update `README.md`, `BASELINE_MANIFEST.md`, `OPEN_ISSUES.md`, and this handoff file after validation.

Do not rebuild the static analysis artifacts unless a new analysis request explicitly requires it. The refreshable workbook should be a separate companion artifact.

## Validation fingerprints

These are the current principal artifact hashes from the packaged project:

| Artifact | SHA-256 |
|---|---|
| `01_source_materials/02_SmartCities_UrbanPulse_RAW-2.xlsx` | `ae8ff0d3a0f96f8bfef80111c26d2d1f414db16d5e916b38bb75d644d01a0c55` |
| `02_final_outputs/urbanpulse_analysis_pivots_charts.xlsx` | `9ed9fe1651fc8973ff866cc3dc5478ee868a603b237a1b339fe4772803c95b78` |
| `02_final_outputs/urbanpulse_refreshable.xlsx` | `412885c2bd75d14f17eae885b7cd17393e18d17ece57619041fd54b79063d730` |
| `02_final_outputs/UrbanPulse_College_Project_Presentation_v3.pptx` | `57b749a71ccd572a892e7127487dd98ed6dba3337ba3d599c1464e910d07f78b` |

The raw-cell-value digest used to compare the source workbook with `urbanpulse_refreshable.xlsx` was identical on both sides: `178f475e67b47e93fdbeedcc13221323280140746b3571461d84db49592e11ed`.

## Handling rules for the next agent

- Treat all files under `01_source_materials/` as preserved source material.
- Do not overwrite the static pivot workbook when creating the refreshable companion.
- Prefer relative paths so the project remains portable when moved between computers.
- Do not add unsupported claims of authenticity from the provenance simulation. It is a flagging exercise, not proof.
- Re-run validation after edits, record material changes, and update the manifest hash for changed final artifacts.
