# UrbanPulse Step 6: Hypothesis Protocol

This is the preregistration layer for Step 6. Hypotheses and practical thresholds are locked before testing. No test results are used to choose these thresholds.

## Statistical standard

- Primary alpha: 0.01, corresponding to the 99% confidence standard.
- Holm correction: applied within each testing family.
- Primary data: canonical observed layer only. No imputation.
- Sensitivity data: Step 5A imputed layer, used only after the primary tests.
- Unknown values are excluded from the affected primary test and remain available for separate review.

## Predefined hypotheses

| ID | Hypothesis | Method | Practical threshold | Statistical/performance threshold |
|---|---|---|---|---|
| H1 | Traffic volume is associated with average speed. | Spearman rank correlation with a 99% confidence interval. | Meaningful association requires absolute rho >= 0.20 and the observed sign must be negative. | Two-sided Holm-adjusted p < 0.01 within the relationship family. |
| H2 | Road incidents are associated with waterlogging reports. | Spearman rank correlation with a 99% confidence interval. | Meaningful association requires absolute rho >= 0.20 and the observed sign must be positive. | Two-sided Holm-adjusted p < 0.01 within the relationship family. |
| H3 | Temperature is associated with power outage minutes. | Spearman rank correlation with a 99% confidence interval. | Meaningful association requires absolute rho >= 0.20 and the observed sign must be positive. | Two-sided Holm-adjusted p < 0.01 within the relationship family. |
| H4_city | Cities differ materially on the selected operational metrics. | Permutation group test with eta-squared effect size and 99% confidence-compatible decision rule. | Meaningful city difference requires eta-squared >= 0.06, equivalent to at least 6% between-city variance; pairwise follow-up requires absolute standardized difference >= 0.50. | Holm-adjusted permutation p < 0.01 within the city-group family, plus the practical effect threshold. |
| H4_zone | Zones differ materially on the selected operational metrics. | Permutation group test with eta-squared effect size and 99% confidence-compatible decision rule. | Meaningful zone difference requires eta-squared >= 0.06, equivalent to at least 6% between-zone variance; pairwise follow-up requires absolute standardized difference >= 0.50. | Holm-adjusted permutation p < 0.01 within the zone-group family. |
| H5 | The sampled metrics have useful temporal predictability. | Blocked time-series validation using three chronological holdouts; compare a simple feature model with a city-month median baseline. | Useful prediction requires at least 10% lower out-of-sample MAE than baseline and out-of-sample R-squared >= 0.10 in at least 2 of 3 holdouts. | A performance gate is used instead of a p-value; no random train/test split. |

## Testing boundaries

For H1-H3, a result is a supported relationship only if it has the expected sign, meets the practical correlation threshold, and passes Holm-adjusted p < 0.01.

For H4, a city or zone difference is material only if it passes the corrected p-value threshold and reaches eta-squared >= 0.06. Pairwise follow-up is only relevant after that gate and requires an absolute standardized difference >= 0.50.

For H5, temporal predictability is useful only when the feature model improves out-of-sample MAE by at least 10% over the city-month median baseline and reaches out-of-sample R-squared >= 0.10 in at least two of three chronological holdouts.

Step 6 testing was completed after this protocol was locked. Results are reported separately in [urbanpulse_step6_testing_results.md](/Users/apple/Documents/Codex/2026-10-01/rea/outputs/urbanpulse_step6_testing_results.md). SQLite integrity check: `ok`.
