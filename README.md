# UrbanPulse Smart-City Project

This folder contains the finalized UrbanPulse college-project materials.

## Contents

- `AGENT_HANDOFF.md` — current state, decisions, validation fingerprints, and next steps for another AI agent.
- `01_source_materials/` — original raw Excel workbook used for the project.
- `02_final_outputs/` — finalized RDBMS database, schema, data layers, analyses, dashboard, quality decisions, provenance results, fitness decision, pivot workbook, and college presentation.
- `03_reproducibility_scripts/` — Python scripts used to build and analyze the project artifacts.
- `04_project_documentation/` — run instructions, baseline notes, and open-issue register.
- `05_dashboard/` — the Streamlit application and SQLite-backed data-access module.
- `requirements.txt` — minimum Python dependencies for the packaged scripts.

The live Google Sheets companion and Apps Script refresh route are documented in `04_project_documentation/GOOGLE_SHEETS_REFRESH_WORKFLOW.md`. The local SQLite/Python route remains the portable, reproducible route; the Google Sheet is a separately verified cloud workbook.

## Current project classification

The dataset is **fit only for descriptive reporting**. It is suitable for descriptive dashboards, exploratory analysis, data-quality demonstrations, training, and pipeline testing. It should not be presented as a validated operational forecasting or causal-decision system.

## Main files

- Database: `02_final_outputs/urbanpulse_rdbms.sqlite`
- Stage 2 refresh script: `03_reproducibility_scripts/refresh_stage2_layers.py`
- Stage 3 sensitivity script: `03_reproducibility_scripts/run_step5a_imputation_sensitivity.py`
- Zone-complete primary policy: `03_reproducibility_scripts/apply_zone_complete_primary_policy.py`
- Stage 3 sensitivity report: `02_final_outputs/urbanpulse_step5a_imputation_sensitivity.md`
- Dashboard: `02_final_outputs/urbanpulse_step5_compact_dashboard.html`
- Final fitness decision: `02_final_outputs/urbanpulse_step9_fitness_decision.md`
- Narrative PDF report: `02_final_outputs/urbanpulse_analysis_report.pdf`
- Cleaned pivot/chart workbook: `02_final_outputs/urbanpulse_analysis_pivots_charts.xlsx`
- Refreshable raw-layer workbook: `02_final_outputs/urbanpulse_refreshable.xlsx` (`tbl_raw`)
- Phase 4 working workbook: `02_final_outputs/urbanpulse_phase4_working.xlsx` (validated Stage 4 native PivotTables; do not overwrite)
- Stage 5 dashboard companion: `02_final_outputs/urbanpulse_phase5_dashboard.xlsx` (three charts and summary tables; labels refresh from SQLite summaries; native workbook A4 settings remain open)
- Stage 5 A4 printable output: `02_final_outputs/urbanpulse_phase5_dashboard_A4.pdf` (one-page landscape A4, visually verified)
- Stage 5/6 completion report: `04_project_documentation/STAGE5_6_COMPLETION_REPORT.md`
- Phase 4 workflow log: `04_project_documentation/PHASE4_REFRESHABLE_WORKFLOW.md`
- Stage 5 checkpoint: `04_project_documentation/STAGE5_CURRENT_CHECKPOINT.md`
- College presentation: `02_final_outputs/UrbanPulse_College_Project_Presentation_v3.pptx`
- Data contract: `02_final_outputs/urbanpulse_data_contract.md`
- Database schema: `02_final_outputs/urbanpulse_schema.sql`
- Parking definition: `04_project_documentation/PARKING_MEASUREMENT_DEFINITION.md`
- Power-outage definition: `04_project_documentation/POWER_OUTAGE_MEASUREMENT_DEFINITION.md`
- PDF verification record: `04_project_documentation/PDF_VERIFICATION.md`
- Phase 2 design audit: `04_project_documentation/PHASE2_DESIGN_AUDIT.md`
- Presentation validation: `04_project_documentation/PRESENTATION_VALIDATION_REPORT.md`
- Dashboard entry point: `05_dashboard/urbanpulse_app.py`

## Portability

The reproducibility scripts now resolve paths relative to this project folder. See `04_project_documentation/RUN_INSTRUCTIONS.md` before running a script. Running analysis scripts can update the packaged database and outputs, so preserve the finalized package first.

The original source PDF referenced during the analysis was not available at its previous Downloads path when this package was assembled, so it has not been copied here.
