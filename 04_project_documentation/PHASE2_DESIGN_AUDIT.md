# Phase 2 Dashboard Design Audit

## Audit status

The design audit was completed, and the approved Streamlit implementation is now packaged in `05_dashboard/`. No database table, raw value, or canonical value was changed.

## Current dashboard evidence

The existing `urbanpulse_step5_compact_dashboard.html` is a compact static HTML report. It contains embedded SVG charts and tables, but no interactive selectors or live SQLite queries.

## Issues found before implementation

| ID | Issue | Impact | Proposed treatment |
|---|---|---|---|
| DESIGN-001 | The dashboard is static and embeds results at generation time. | Filters and refresh are unavailable; displayed values can become stale after database updates. | Build a database-backed application with explicit refresh behavior. |
| DESIGN-002 | The current speed distribution view displays raw observed extremes such as `-10` and `200`, while the primary descriptive summary excludes invalid speeds. | A reader may confuse quality-screened analytical results with raw observed ranges. | Label raw range and primary-valid range separately. |
| DESIGN-003 | Parking and power-outage definitions are not prominent in the current dashboard. | Values can be misinterpreted, especially parking values above 100% and outage values above 60 minutes. | Add metric definitions, provisional-status labels, and flag explanations beside the relevant views. |
| DESIGN-004 | Quality signals are combined in one compact panel. | Users cannot trace a flag to its source row, decision class, or primary-analysis treatment. | Add a dedicated data-quality page with counts, filters, and treatment rules. |
| DESIGN-005 | City and zone counts are shown, but there is no structured city/zone metric comparison view. | The dashboard does not fully support the intended college-project comparison use case. | Add descriptive city and zone summaries without rankings or causal language. |
| DESIGN-006 | The intentional-sample limitation is present but must remain visible on every analytical page. | Users could otherwise interpret the dashboard as a complete city-zone panel. | Use a persistent limitation banner and methodology page. |
| DESIGN-007 | The dashboard does not expose the observed-only primary policy versus imputation sensitivity results. | Users may not know which values drive the primary summaries. | Add an analysis-policy panel and clearly separate sensitivity outputs. |
| DESIGN-008 | The PDF appendix references `urbanpulse_analysis_pivots_charts.xlsx`, which was initially absent. | The dashboard/report package had an artifact traceability gap. | Resolved on 2026-10-04 by packaging the supplied workbook, preserving the original source copy, and documenting its static-snapshot limitation. |

## Implemented application design

The packaged application uses Streamlit connected to the packaged SQLite database in read-only mode.

### Pages

1. Overview and coverage
2. City and zone descriptive comparison
3. Traffic and mobility
4. Incidents, environment, and outages
5. Data quality and provenance
6. Definitions, methods, and limitations

### Global controls

- City
- Zone, including Unknown
- Date range
- Month
- Observation time slot
- Metric display policy: raw observed versus primary-valid where applicable

### Acceptance criteria

- All displayed values are queried from the packaged SQLite database.
- Filters update every affected table and chart.
- Raw and primary-valid views are clearly separated.
- Missing, unknown, outlier, corrected, and imputed states are visible.
- Parking and outage definitions appear beside their metrics.
- The intentional sample limitation remains visible.
- No official city ranking, causal claim, or operational forecast is presented.
- The application runs from the project folder using the documented dependencies.

## Major-work gate

The project owner approved the design, so the Streamlit application, dependency declaration, data-access module, and read-only smoke test were added. Streamlit 1.65.0 is now installed, the app launch health check passed, and Phase 3 browser-level validation passed for page navigation, filters, charts, and empty states. The optional hardening re-test cleared the previously observed Vega and deprecated Streamlit API warnings; the current status is recorded in `OPEN_ISSUES.md` and `PHASE3_APPLICATION_TEST_REPORT.md`.
