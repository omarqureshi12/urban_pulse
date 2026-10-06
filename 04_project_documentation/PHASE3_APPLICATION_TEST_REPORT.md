# Phase 3 Application Test Report

## Test scope

- Application: `05_dashboard/urbanpulse_app.py`
- Test date: 2026-10-04
- Runtime: Python 3.14.6, Streamlit 1.65.0
- Database: packaged SQLite database opened through the application's read-only data layer
- Test mode: browser-level interaction against the local Streamlit server

## Results

### Page navigation

All six dashboard pages loaded without an exception or traceback:

- Overview
- City and zone comparison
- Traffic and mobility
- Incidents and environment
- Data quality and provenance
- Definitions and limitations

Non-empty pages rendered their expected tables and/or charts. Data-quality and definitions pages correctly used tables/text without requiring charts.

### Filter behavior

The following browser interactions produced the expected visible results:

| Test | Visible result | Status |
|---|---:|---|
| Default canonical observed view | 1,600 rows | Passed |
| City = Pune | 242 rows, 1 city, Pune chart bar = 242 | Passed |
| Zone = Unknown | 32 rows, 1 zone | Passed |
| Time slot = 00:00 | 267 rows | Passed |
| Date range = 2026-01-01 to 2026-01-01 | 6 rows | Passed |
| Primary-analysis eligible view | 1,491 rows | Passed |

The primary-analysis view did not introduce imputed records into the displayed row count.

### Charts

- Overview charts rendered for rows by city and rows by zone.
- Chart labels and values updated after city and row-view changes.
- City-filtered chart displayed Pune with 242 rows.
- Empty filtered results removed chart output instead of showing stale values.

### Empty state

A valid no-result combination was tested using Bhopal on 2026-01-01. The application displayed:

`No observations match the selected filters.`

No exception, traceback, or stale chart appeared.

### Console observations

No browser errors or exceptions were observed. The browser console emitted non-blocking Vega warnings, including scale-binding warnings and infinite-extent warnings while charts were refreshed or empty:

- `Scale bindings are currently only supported for scales with unbinned, continuous domains.`
- `Infinite extent for field ...: [Infinity, -Infinity]`

These warnings did not prevent correct page rendering or the empty-state message. They are recorded as `PROJECT-004` for optional chart-rendering hardening.

The Streamlit server log also emitted repeated deprecation warnings for `use_container_width`. The app continued to run normally. This is recorded as `PROJECT-005` for future compatibility maintenance.

## Optional hardening re-test

After the initial validation, the two overview count charts were changed from the convenience `st.bar_chart` wrapper to explicit Altair specifications with explicit categorical and quantitative encodings. Empty-filter handling was retained. All dataframe calls now use the current `width="stretch"` API.

A fresh browser tab was loaded after the patch. The dashboard again rendered the default overview, and the fresh browser console contained no warning or error entries. The Streamlit server log contained no `use_container_width` deprecation warnings. Existing filter, chart, and empty-state results remained unchanged.

## Conclusion

Browser-level validation passed for the requested pages, filters, charts, and empty state. Optional dashboard hardening also passed: the previously recorded Vega and deprecated-API warnings were not reproduced after the patch. The dashboard is functionally ready for Phase 3 sign-off.
