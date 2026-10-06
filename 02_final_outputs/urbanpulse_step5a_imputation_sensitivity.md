# UrbanPulse Step 5A: Imputation Sensitivity Analysis

This substep creates a separate imputed sensitivity layer. The immutable raw layer, canonical observed layer, and primary analysis remain unchanged.

## Rules applied

- Normal-like numeric distributions: mean.
- Skewed numeric distributions: median.
- Categorical variables: mode.
- Distribution screening uses adjusted sample skewness. Absolute skewness at or below 0.5 is classified as normal-like. This is a screening rule, not a formal normality test.

## Imputation methods

| Field | Type | Observed n | Missing n | Skewness | Class | Method | Estimate |
|---|---|---:|---:|---:|---|---|---:|
| traffic_volume | numeric | 1,568 | 32 | 0.076 | normal_like | mean | 2,050.9490 |
| avg_speed_kmph | numeric | 1,551 | 39 | 0.088 | normal_like | mean | 38.1629 |
| temperature_c | numeric | 1,327 | 32 | 0.053 | normal_like | mean | 28.5212 |
| zone | categorical | 1,568 | 32 | n.a. | categorical | mode | Central |

Total imputation events: `135`.

## Interpretation

The missing numeric fields in this dataset were classified as normal-like under the screening rule, so their missing values use means. The missing zone values use the modal canonical zone. No skewed numeric field had missing values requiring median imputation in this dataset.

The imputed layer is for sensitivity analysis only. The primary analysis uses observed canonical values and never uses imputed values. The primary view is not a global complete-case table: rows with unknown zone may remain for analyses that do not require zone; zone-based analyses must filter to observed zones. The original and canonical observed values are preserved.

SQLite integrity check: `ok`.
