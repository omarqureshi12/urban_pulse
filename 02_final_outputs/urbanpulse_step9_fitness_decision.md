# UrbanPulse Step 9: Fitness Decision

## Final classification

**Fit only for descriptive reporting**

This is the appropriate current-use classification for the dataset as loaded and documented through Steps 1–8. It is not classified as fit for operational analysis because the data are intentionally sampled, several semantic/source decisions remain unresolved, and model/forecast evidence does not establish reliable operational relationships or prediction.

## Evidence considered

- Canonical layer: 1,600 rows; 1,491 primary-analysis eligible and 109 not eligible under the quality rules.
- Raw layer: 1,635 rows and 35 duplicate record IDs retained in the audit trail; canonical deduplication is separate.
- Quality decisions: 465 confirmed-error items, 16 valid-extreme items, and 285 unknown-decision items.
- Step 6: 0 of 8 registered hypotheses supported at the predefined 99% threshold.
- Step 7: 3 of 3 adjusted relationship intervals included the null effect; mean forecast R² was -1.508.
- Step 8: 0 provenance diagnostics were flagged under the independent-permutation null. This is not proof of authentic or synthetic origin.

## Permitted use

Use for aggregate summaries, distributions, ranges, coverage, exploratory charts, and descriptive reporting with limitations disclosed. It may also support controlled training, dashboard prototyping, and pipeline testing, but those uses do not upgrade its operational fitness.

## Restrictions and upgrade conditions

Use for aggregate summaries, distributions, ranges, coverage, exploratory charts, and documented descriptive reporting. Do not use the current file alone for operational control, safety-critical decisions, KPI commitments, causal claims, or production forecasting. An upgrade to operational analysis requires sampling-frame/representativeness documentation, owner confirmation of speed/parking/outage/temperature/zone semantics, source or station metadata, and a repeat validation after remediation.

Raw and canonical layers remain unchanged.
