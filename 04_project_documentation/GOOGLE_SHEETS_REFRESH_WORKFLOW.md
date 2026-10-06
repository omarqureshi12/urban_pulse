# Google Sheets Refresh Workflow

Status: verified on 2026-10-05.

This is a live cloud-workbook companion to the packaged UrbanPulse project. It was verified after completing the standard Google authorization prompt and running the linked Apps Script project. It does not replace the immutable local raw workbook, the native-PivotTable XLSX, or the portable SQLite/Python workflow.

## Access points

- Workbook: [UrbanPulse Google Sheet](https://docs.google.com/spreadsheets/d/1gZQSJngvZwvKNsy1FVyWOBwp_Rw6eQ4ceb-QSrDMV9U/edit)
- Apps Script project: [UrbanPulse Apps Script project](https://script.google.com/home/projects/18n2ExEh48ld4aF75GfK60qgTt_2LxX3wQbqnf4dTtDAglJ12qjabkZ-2/edit)
- Spreadsheet ID: `1gZQSJngvZwvKNsy1FVyWOBwp_Rw6eQ4ceb-QSrDMV9U`

## Verified operating rules

1. `Sheet1` is the raw input tab and must be treated as immutable.
2. The Apps Script rebuild reads the raw tab and writes derived/output tabs beginning with `Refresh_`, plus `Dashboard_Refresh` and `Refresh_Status`.
3. The primary analysis uses observed values only. Imputation is sensitivity-only.
4. Raw and cleaned values remain traceable through the canonical layer, quality flags, and change log.
5. The Google Sheets route does not use generic internet averages to overwrite temperature values. The approved month/neighbor rule and benchmark logic remain the governing quality decisions.

## Verified output tabs

- `Refresh_Canonical`
- `Refresh_Primary`
- `Refresh_Zone_Complete`
- `Refresh_Zone_Pivot_Source`
- `Refresh_Quality_Flags`
- `Refresh_Change_Log`
- `Refresh_Sensitivity`
- `Refresh_Imputation_Events`
- `Refresh_City`
- `Refresh_Zone`
- `Refresh_Month`
- `Dashboard_Refresh`
- `Refresh_Status`

Existing legacy/static tabs remain in the workbook for traceability, including `Canonical_Cleaned`, `Primary_Observed`, `Primary_Zone_Complete`, `Pivot_City`, `Pivot_Zone`, `Pivot_Month`, and `Zone_Pivot_Source`.

## Verification record

The successful refresh reported and the workbook displayed these counts:

| Measure | Count |
|---|---:|
| Raw rows | 1,635 |
| Canonical rows | 1,600 |
| Primary observed rows | 1,491 |
| Known-zone primary rows | 1,462 |
| Quality flags | 763 |
| Change-log entries | 465 |
| Sensitivity rows | 1,600 |
| Sensitivity imputation events | 135 |

`Dashboard_Refresh` was visually verified with city, zone, and month summary tables and charts. `Refresh_Status` confirmed the observed-only primary policy and the fact that the raw tab is never overwritten.

## Future refresh procedure

1. Open the Apps Script project and confirm the target spreadsheet is the workbook linked above.
2. Run `refreshUrbanPulse` to rebuild the derived layers from `Sheet1`.
3. Wait for execution completion.
4. Open `Refresh_Status` and confirm counts, policy text, and refresh timestamp.
5. Open `Dashboard_Refresh` and confirm summary tables and charts are present.
6. If the installable trigger is missing, run `setupUrbanPulse` once to recreate it and perform an initial refresh.

Do not claim a successful refresh until the execution completes and both `Refresh_Status` and `Dashboard_Refresh` have been checked.

## Limitation

The Apps Script source is hosted in Google Apps Script rather than duplicated in this local folder. This handoff preserves the live links, sheet names, verified counts, operating rules, and recovery procedure so another agent can continue the work. The local SQLite/Python scripts remain the preferred portable and reproducible implementation.
