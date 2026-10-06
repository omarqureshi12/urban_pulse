# UrbanPulse Step 6: Hypothesis Testing Results

Tests were run after the hypotheses and thresholds were predefined. The primary analysis uses the canonical observed layer only. The Step 5A imputed layer was not used.

The separate imputation sensitivity results are reported in [urbanpulse_step6_imputation_sensitivity.md](/Users/apple/Documents/Codex/2026-10-01/rea/outputs/urbanpulse_step6_imputation_sensitivity.md).

Statistical standard: alpha = 0.01; Holm correction within each family; group permutations = 5,000; seed = 20261006.

## Relationship hypotheses

| ID | Relationship | n | Spearman rho | 99% CI | Holm p | Practical gate | Statistical gate | Final |
|---|---|---:|---:|---|---:|---|---|---|
| H1 | Traffic volume vs Average speed | 1,520 | 0.014 | [-0.052, 0.080] | 1.000 | Fail | Fail | Not supported |
| H2 | Road incidents vs Waterlogging reports | 1,600 | 0.018 | [-0.047, 0.082] | 1.000 | Fail | Fail | Not supported |
| H3 | Temperature vs Power outage minutes | 1,327 | -0.013 | [-0.083, 0.058] | 1.000 | Fail | Fail | Not supported |

## City and zone differences

Meaningful effect requires eta-squared >= 0.06 and Holm-adjusted p < 0.01.

| Factor | Tests | Practical passes | Statistical passes | Both gates | Largest eta-squared |
|---|---:|---:|---:|---:|---:|
| city | 9 | 0 | 0 | 0 | 0.015 |
| zone | 9 | 0 | 0 | 0 | 0.006 |

## Temporal predictability

Useful prediction requires at least 10% MAE improvement over the city-month median baseline and R-squared >= 0.10 in at least 2 of 3 chronological holdouts.

| Metric | Folds | Useful folds | Mean baseline MAE | Mean model MAE | Mean MAE improvement | Mean model R² | Final |
|---|---:|---:|---:|---:|---:|---:|---|
| Traffic volume | 3 | 0 | 1094.201 | 981.005 | 10.0% | -0.103 | Not supported |
| Average speed | 3 | 0 | 10.896 | 9.941 | 7.6% | -0.021 | Not supported |
| Public transport usage | 3 | 0 | 634.140 | 607.390 | 3.4% | -0.051 | Not supported |
| Parking occupancy | 3 | 0 | 19.129 | 17.589 | 7.7% | -0.085 | Not supported |
| Road incidents | 3 | 0 | 1.119 | 1.110 | 0.9% | -0.060 | Not supported |
| Waterlogging reports | 3 | 0 | 0.810 | 0.846 | -4.7% | -0.053 | Not supported |
| Power outage minutes | 3 | 0 | 9.093 | 9.318 | -2.9% | -0.085 | Not supported |
| Citizen complaints | 3 | 0 | 2.448 | 2.176 | 11.1% | -0.031 | Not supported |
| Temperature | 3 | 0 | 5.268 | 4.629 | 8.4% | -0.127 | Not supported |

## Conclusion

Relationship hypotheses supported by both gates: 0 of 3.
City/zone metric tests supported by both gates: 0 of 18.
Predictive metric tests supported by the performance gate: 0 of 9.

A non-supported result means the predefined practical and statistical thresholds were not both met. It does not prove that no relationship exists. Results describe the intentionally sampled stream and should not be generalized to an unsampled full city-zone panel.

SQLite integrity check: `ok`.
