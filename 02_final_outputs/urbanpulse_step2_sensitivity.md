# UrbanPulse Step 2: Sensitivity Analysis

This analysis is counted under Step 2. It tests whether the descriptive and relationship conclusions depend on the conservative cleaning policy.

## Scenarios

| Scenario | Treatment |
|---|---|
| primary_observed | Missing values excluded; speed values outside 0-120 excluded. |
| flagged_values_included | Missing values excluded; all non-null raw numeric values included, including flagged speeds. |
| city_month_median_imputed | Missing values and invalid speeds filled with city-month medians, falling back to the overall median. |

## Metric stability

| Metric | Primary mean | Flagged-values mean | Imputed mean | Primary 99% CI |
|---|---:|---:|---:|---:|
| Traffic volume | 2,050.949 | 2,050.949 | 2,048.040 | [1,981.841, 2,115.939] |
| Average speed (km/h) | 38.163 | 38.431 | 38.159 | [37.385, 38.977] |
| Public transport usage | 1,298.672 | 1,298.672 | 1,298.672 | [1,254.655, 1,346.435] |
| Parking occupancy (%) | 68.137 | 68.137 | 68.137 | [66.778, 69.321] |
| Road incidents | 1.959 | 1.959 | 1.959 | [1.869, 2.050] |
| Waterlogging reports | 1.021 | 1.021 | 1.021 | [0.957, 1.087] |
| Power outage (minutes) | 11.875 | 11.875 | 11.875 | [11.110, 12.679] |
| Citizen complaints | 7.953 | 7.953 | 7.953 | [7.772, 8.131] |
| Temperature (C) | 28.932 | 28.932 | 28.925 | [28.464, 29.404] |

## Relationship stability

| Scenario | Correlation pairs | Significant after Holm at 99% | Largest absolute correlation |
|---|---:|---:|---:|
| city_month_median_imputed | 36 | 0 | 0.050 |
| flagged_values_included | 36 | 0 | 0.043 |
| primary_observed | 36 | 0 | 0.050 |

## Group-effect stability

| Scenario | Group tests | Significant after Holm at 99% | Largest eta-squared |
|---|---:|---:|---:|
| city_month_median_imputed | 45 | 0 | 0.012 |
| flagged_values_included | 45 | 0 | 0.012 |
| primary_observed | 45 | 0 | 0.012 |

## Step 2 conclusion

The main conclusions are stable across the three scenarios: no Pearson correlation and no city, zone, month, hour, or weekday group effect survives Holm correction at 99%. Including flagged speeds or applying city-month median imputation changes point estimates slightly but does not change the decision. The primary observed-data scenario remains the authoritative result.

SQLite integrity check: `ok`.
