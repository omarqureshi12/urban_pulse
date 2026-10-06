# UrbanPulse Baseline Manifest

Baseline package updated on 2026-10-04.

## Package checks

- Total packaged files: 101 (excluding temporary finalizer files, Python bytecode caches, and generated inspection sidecars)
- Final output files: 48
- Reproducibility scripts, including portable path configuration: 24
- Dashboard files, including the read-only data layer and smoke test: 3
- Raw workbook rows: 1,635
- Raw distinct record IDs: 1,600
- Canonical cleaned rows: 1,600
- Primary-analysis eligible rows: 1,491
- SQLite integrity check: `ok`
- Final fitness classification: `FIT_ONLY_DESCRIPTIVE_REPORTING`
- Portability validation: all 23 Python scripts parsed successfully, and the compact dashboard regenerated successfully from `/tmp` using project-relative paths.
- Pivot/chart companion workbook: supplied workbook reconciled to the packaged SQLite database for headline counts, city counts, metric summaries, and quality-flag totals; static snapshot limitation documented; A4 print settings verified in a seven-page PDF export with charts and tables preserved.
- Refreshable raw-layer workbook: `tbl_raw` contains the complete 1,635-row raw dataset with values unchanged; the original raw workbook remains preserved separately.
- Stage 2 refresh validation: the portable raw-to-canonical script passed on a disposable database copy with 1,635 raw rows, 1,600 canonical rows, 35 exact duplicates excluded, 465 change-log entries, 763 base flags, zero Stage 2 imputed values, and SQLite integrity `ok`.
- Stage 3 sensitivity validation: the imputation workflow passed in an isolated project copy before promotion. It preserved 1,491 observed-only primary rows, created 1,600 sensitivity rows and 135 imputation events across four methods, kept all imputed flags sensitivity-only, preserved the canonical-layer content hash, and passed SQLite integrity checks. A pre-promotion database backup is stored at `04_project_documentation/archives/urbanpulse_rdbms_before_stage3.sqlite`.
- Zone-complete primary policy: created `v_primary_zone_complete` with 1,462 observed-only known-zone rows, excluded 29 undefined-zone rows from zone-required primary analyses, preserved raw/canonical row counts, and passed SQLite integrity and dashboard smoke tests. A pre-policy database backup is stored at `04_project_documentation/archives/urbanpulse_rdbms_before_zone_complete_primary.sqlite`.
- Phase 4 native PivotTable validation: promoted a separate working workbook with native `Pivot_City`, `Pivot_Zone`, and `Pivot_Month` summaries. City/month sources contain 1,491 observed-only rows; the zone source contains 1,462 known-zone rows and excludes only `source_row_number` from the pivot source while preserving it in the full analysis table. Three PivotTable parts, two pivot caches, visible totals, and zero formula errors were verified. The pre-Stage-4 working workbook is archived at `04_project_documentation/archives/urbanpulse_phase4_working_before_stage4.xlsx`.
- Stage 5 checkpoint: chart insertion and A4 print-layout work was attempted only in a disposable WPS copy. Chart placement was unstable, so the packaged Stage 4 native-PivotTable workbook remains unchanged. The safe artifact-tool companion and one-page A4 PDF were promoted separately; see `04_project_documentation/STAGE5_CURRENT_CHECKPOINT.md`.
- Stage 5 companion validation: `02_final_outputs/urbanpulse_phase5_dashboard.xlsx` contains three non-overlapping editable charts and visible summary tables sourced from SQLite. City/month totals are 1,491 records and 3,057,918 traffic units; zone totals are 1,462 records and 2,998,962 traffic units. The dashboard rendered cleanly, passed the formula-error scan, and now derives record-count labels and the unknown-zone scope note from the summary data. Native A4 print settings remain unverified.
- Stage 5 A4 output validation: `02_final_outputs/urbanpulse_phase5_dashboard_A4.pdf` is a one-page landscape A4 PDF. Rendered-page inspection found no clipping or overlap.
- Stage 6 controlled refresh validation: in disposable copies, a controlled row increased raw rows to 1,636, canonical rows to 1,601, and observed-only rows to 1,492. The separate sensitivity layer rebuilt to 1,601 rows with 135 imputation events, while the primary view remained observed-only. Dashboard labels and three charts refreshed coherently; SQLite integrity remained `ok`. The production raw workbook, database, and native-PivotTable workbook were not changed; the presentation companion was regenerated from the unchanged production database. Native `Refresh All` is blocked in the current workbook because no Power Query, query-table, or workbook connection links `tbl_raw` to the canonical and pivot-source tables.
- Rebuild regression validation: `apply_two_data_layers.py` completed successfully in a disposable project copy, emitted valid JSON status with string paths, produced 1,635 raw rows, 1,600 canonical rows, 1,491 observed rows, 1,462 zone-complete rows, and passed SQLite integrity.
- Phase 3 browser validation: six pages, city/zone/time/date/row-view filters, charts, and empty state tested successfully; optional dashboard hardening re-test cleared the previously recorded Vega and Streamlit deprecation warnings.
- College presentation: eight slides, native tables, native city chart with embedded literal-data workbook snapshot, speaker notes, package integrity, layout, and font checks passed; native PowerPoint application opening was not independently verified.

## SHA-256 fingerprints

These fingerprints identify the principal baseline artifacts in this package.

| Artifact | SHA-256 |
|---|---|
| `01_source_materials/02_SmartCities_UrbanPulse_RAW-2.xlsx` | `ae8ff0d3a0f96f8bfef80111c26d2d1f414db16d5e916b38bb75d644d01a0c55` |
| `02_final_outputs/urbanpulse_rdbms.sqlite` | `1a90610e0a3a1632efc3b75bd24ebcc7bf5fbcca63d6edaaa7ea740e23150319` |
| `04_project_documentation/archives/urbanpulse_rdbms_before_stage3.sqlite` | `a1425dfb4e2e910005878987e9e22fd7bd5a9a875f541e5d23b9020e33aa06c5` |
| `04_project_documentation/archives/urbanpulse_rdbms_before_zone_complete_primary.sqlite` | `d68fd2463fe98e4fd24de8660b10d174017582c8168dbb929e145587328b0f46` |
| `02_final_outputs/urbanpulse_step5a_imputation_sensitivity.md` | `abcf68b0dc7c24049acd76d7fb745e115c9f4787fb2e67ac3ecefe9ef00feb66` |
| `02_final_outputs/urbanpulse_step5a_imputation_summary.csv` | `a5b34ec2dab9203a1040ab702e4136bf241f4e6a3ae51dc255e84ac9c7db272d` |
| `02_final_outputs/urbanpulse_step5a_imputed_values.csv` | `f18eadc4936686291fa8f49fb91e4eacefca2cb36394e83ab5f0d2c8ba2b072b` |
| `03_reproducibility_scripts/run_step5a_imputation_sensitivity.py` | `f5d039418661ed3e1e7016bbf00c70fb17389471f7ee10eecdad03b0513329de` |
| `02_final_outputs/urbanpulse_step5_compact_dashboard.html` | `06722ada35908ad227c000a02744801a8da54eff67ceab7700c41a5019c8bdc5` |
| `02_final_outputs/urbanpulse_step9_fitness_decision.md` | `eff25a49a94dedb39a1ea8588ff41f1c152ae18bcf6ba641f52637430e3cb995` |
| `02_final_outputs/urbanpulse_analysis_report.pdf` | `78fb823aa6748c4cd8e24a2cd8591838e5c030ece7b40228b7324d0bb0021279` |
| `01_source_materials/urbanpulse_analysis_pivots_charts_source.xlsx` | `8314e530b971e7cd455da7972c1a32420ee3ab4878e283f353c5e9859fa9bd06` |
| `02_final_outputs/urbanpulse_analysis_pivots_charts.xlsx` | `9ed9fe1651fc8973ff866cc3dc5478ee868a603b237a1b339fe4772803c95b78` |
| `02_final_outputs/urbanpulse_refreshable.xlsx` | `412885c2bd75d14f17eae885b7cd17393e18d17ece57619041fd54b79063d730` |
| `02_final_outputs/urbanpulse_phase4_working.xlsx` | `9caf3ef3338515a50149bb26f3b6d98e6e24f57471c00fd26efbdb646ba3bf28` |
| `02_final_outputs/urbanpulse_phase5_dashboard.xlsx` | `4e5ec88e1f155eb36db3bf21c773e8362cfefa758a8fe6ce3aa8398bc9e5f879` |
| `02_final_outputs/urbanpulse_phase5_dashboard_A4.pdf` | `ecf106b4592bd2bc1b539fc44eb3e7ca090bba608c01802f921f73d60eecab27` |
| `04_project_documentation/archives/urbanpulse_phase4_working_before_stage4.xlsx` | `412885c2bd75d14f17eae885b7cd17393e18d17ece57619041fd54b79063d730` |
| `02_final_outputs/urbanpulse_data_layers.md` | `9b8d8f426a1543348910915c79b248f6d0af1dfcfa7f91201357bbd03aa01765` |
| `02_final_outputs/urbanpulse_data_contract.md` | `d060ba65736391cfc32d6e5bbcf32c18d6f87f455ba9f6ebffd37fc45d34193f` |
| `02_final_outputs/urbanpulse_schema.sql` | `7ecfbf037d8fb98dc86963af5f76750ae4a05aaa95ac5863443890ac9e23ac34` |
| `02_final_outputs/urbanpulse_data_layers_migration.sql` | `ad608d3248473b1a2ab95e6a9a4675bb6d81fc65a5e52574691d0002b73f83e2` |
| `02_final_outputs/UrbanPulse_College_Project_Presentation_v3.pptx` | `57b749a71ccd572a892e7127487dd98ed6dba3337ba3d599c1464e910d07f78b` |
| `AGENT_HANDOFF.md` | `5cb58ed7e836d00cd55344d9d4abf2d082852f519b6a42665c4c09485e7d2fdb` |
| `04_project_documentation/PHASE4_REFRESHABLE_WORKFLOW.md` | `e1da5c838d3d7bf1235d4f56091191c41d716ec2dc9fe60d73e1181c5f2cf5c0` |
| `04_project_documentation/STAGE5_CURRENT_CHECKPOINT.md` | `f690cbbbe72a89f52c696e4f0c1fd560283db35ef6c7b0d4189054165fc76de6` |
| `04_project_documentation/OPEN_ISSUES.md` | `8d16b19bb6e3dfe10da55989297d318d8adea06a13039104dbfbbef2c8150bd8` |
| `04_project_documentation/RUN_INSTRUCTIONS.md` | `f6c9b0c7ebfb9a334909770b321ecc900709a717ce0459bf036c001513b8724f` |
| `03_reproducibility_scripts/refresh_stage2_layers.py` | `b2dce0c17cb6892824321b445da82445294e66cc4360aad8cb2ad512c166d1da` |
| `03_reproducibility_scripts/apply_zone_complete_primary_policy.py` | `c92e1a5e15b771dbacd3705bce915229c850850f3a7e0ef58306b1c01c8fc8a1` |
| `03_reproducibility_scripts/apply_two_data_layers.py` | `270d6b413ce2ee506ac0fba0eda2536d5c00256e55ba418ad10ed4809e77c248` |
| `03_reproducibility_scripts/project_config.py` | `1acf5a65504af5b2c1cf44e86703ef28105d76c87332e2208d43a37567ee2c1b` |
| `03_reproducibility_scripts/build_stage5_dashboard.mjs` | `5445482a95e208223798a22518e18d638b0457e09f7c03ebeec2c3c505a01387` |
| `03_reproducibility_scripts/build_stage5_a4_pdf.py` | `5f63ffd30507390cc5bacf81da66009156bdfe7579c5b34914905af2f912c2ca` |
| `03_reproducibility_scripts/run_stage6_controlled_refresh.mjs` | `73ac8c296e3252c3f2a1e42e08fe0868fb98e9334a4cde067dbbc678176b59c9` |
| `04_project_documentation/STAGE5_6_COMPLETION_REPORT.md` | `c456544f56aba7bf34c60f8615f9fcf431dbf7fa9b8a8e0141a5e6d9d081d68d` |
| `README.md` | `3719028a653861bd169b5ab22189237ee9678576905d51a875a17bf5ca5f845e` |
| `04_project_documentation/PHASE2_DESIGN_AUDIT.md` | `3e8ecf835fbe31d51dfd38a8ad1ac81bb36cb4be3116249664c61bdbfd682bad` |
| `requirements.txt` | `f30f9af98c6e1746793e9f9af15608c0797a37ef517d166172abad37a78d6c6b` |
| `05_dashboard/urbanpulse_app.py` | `9e9ccfe17364b22f36703c01a829508b236093ce7b47b907e8c3cfd22834a023` |
| `05_dashboard/urbanpulse_data.py` | `d2dcde72f0e6fa4df3f168b01a367ac33b226c017ef2174f0ff12467b36d9c3d` |
| `05_dashboard/test_urbanpulse_data.py` | `7353c304c752e91efc8bde5022c7148634b33947631beebab84383ffc1c66538` |

## Baseline interpretation

This is a reproducible descriptive-analysis package. The raw workbook and raw database layer are preserved. The package is not an operational forecasting system, and the open issues register remains part of the baseline.
