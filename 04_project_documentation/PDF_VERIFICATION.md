# PDF Verification Record

## Source reviewed

- File: `02_final_outputs/urbanpulse_analysis_report.pdf`
- Pages: 11
- Title: `UrbanPulse Smart-City Analysis Report`
- Observed period stated in the PDF: 2026-01-01 to 2026-09-24
- Review date: 2026-10-03

## Verified from the PDF and cross-checked against the packaged RDBMS

- Final classification: fit only for descriptive reporting
- Raw rows: 1,635
- Canonical rows: 1,600
- Primary-analysis eligible rows: 1,491
- Provenance flags: 0
- Intentional sample interpretation and non-panel limitation
- Raw/canonical two-layer design and observed-values-only primary analysis
- Separate imputation sensitivity layer
- Eight registered hypotheses with no support at the predefined 99% threshold
- Forecasting did not establish useful generalization
- Thirty-five raw duplicate rows retained in the audit trail
- Parking readings above 100% and temperature flags require domain context
- Power-outage readings above 60 minutes were retained and flagged

The rendered pages were visually reviewed. Headings, tables, charts, page numbering, and section transitions were legible with no obvious clipping or overlap at the rendered page overview.

## Not verified by this PDF

The PDF explicitly states that it does not provide the original project objective, official field definitions, original sampling narrative, external source documentation, original charts, or original conclusions. These remain unresolved unless supplied elsewhere.

The PDF also does not verify:

- Parking numerator, denominator, or source observation window
- Power-outage timestamp role
- Speed source system and road scope
- Temperature station/source metadata
- Zone ownership and authoritative mapping

The current project therefore keeps those items open or provisional. The more recent user-provided power-outage definition is retained as a partially confirmed project definition, not attributed to this PDF.

## Pivot/chart companion artifact

The previously missing `urbanpulse_analysis_pivots_charts.xlsx` was supplied on 2026-10-04. The original supplied workbook is preserved as `01_source_materials/urbanpulse_analysis_pivots_charts_source.xlsx`; the cleaned presentation copy is packaged as `02_final_outputs/urbanpulse_analysis_pivots_charts.xlsx`.

The workbook contains seven sheets, nine Excel Tables, and six charts. It does not contain native PivotTable or pivot-cache XML, so it is a static snapshot rather than a refreshable pivot workbook. Its headline counts, city counts, metric summaries, and quality-flag totals reconcile with the packaged SQLite database. No raw or canonical database values were changed.

The cleaned workbook hides gridlines, compacts numeric formats, widens long text columns, and preserves all six charts. The final workbook also embeds A4 print settings: each sheet selects portrait or landscape orientation based on fit, uses an explicit print area, fits to one page wide, and uses a one-page or two-page height where needed. Final PDF verification produced seven A4 pages—one per sheet—with tables and charts complete and no clipping observed. This remains a static snapshot rather than a refreshable PivotTable workbook.
