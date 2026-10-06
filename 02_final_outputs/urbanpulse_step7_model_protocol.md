# UrbanPulse Step 7: Fit-for-Purpose Model Protocol

This protocol defines the models, estimands, inclusion rules, and uncertainty methods before fitting. It is designed for the intentionally sampled stream and does not assume a complete city-zone panel.

## Primary data rules

- Primary models use the canonical observed layer only.
- No imputation in primary models.
- Speed values outside 0-120 km/h are excluded from speed models.
- Temperature values classified as probable_error are excluded from temperature models.
- Unknown zones are excluded from zone contrasts, but may be represented explicitly in adjusted relationships.
- The Step 5A imputed layer is a separate sensitivity analysis.

## Model registry

| Model | Purpose | Model class | Main estimand | Uncertainty |
|---|---|---|---|---|
| M1_city_zone_continuous | City/zone comparisons | Huber robust regression with city and zone effects | Adjusted city and zone marginal contrasts versus the adjusted grand mean, in native units and standardized units. | 3,000 resamples of calendar dates with replacement; 99% percentile intervals; resample the whole date block. |
| M2_city_zone_counts | City/zone comparisons | Poisson GLM when dispersion <= 1.5; otherwise negative-binomial GLM | Adjusted incidence-rate ratio or multiplicative city/zone contrast versus the adjusted grand mean. | 3,000 calendar-date block bootstrap resamples; 99% percentile intervals for rate ratios and contrasts. |
| M3_relationship_traffic_speed | Adjusted relationship | Huber robust regression | Adjusted change in speed per 1,000-unit traffic increase, plus standardized coefficient. | 3,000 calendar-date block bootstrap resamples; 99% percentile interval for the adjusted coefficient. |
| M4_relationship_incidents_waterlogging | Adjusted relationship | Negative-binomial GLM with log link, if overdispersed | Adjusted incidence-rate ratio for one additional waterlogging report. | 3,000 calendar-date block bootstrap resamples; 99% percentile interval for the rate ratio. |
| M5_relationship_temperature_outage | Adjusted relationship | Huber robust regression | Adjusted change in outage minutes per 1°C increase, plus standardized coefficient. | 3,000 calendar-date block bootstrap resamples; 99% percentile interval for the adjusted coefficient. |
| M6_repeated_time_dependence | Repeated time observations | Date-block bootstrap wrapper around each fitted model | Uncertainty that respects same-date dependence and avoids treating every row as independent. | 3,000 date-block resamples; 99% percentile intervals for all reported effects. |
| M7_forecasting | Forecasting | Rolling time-based validation; robust regression for continuous targets and Poisson/negative-binomial model for counts | Out-of-sample MAE, RMSE, R-squared, and improvement versus a city-month median baseline. | Three expanding-window chronological holdouts; 99% date-block bootstrap intervals for error metrics and improvement. |

## Reporting standard

Every fitted model will report effect sizes in interpretable units, standardized effects where useful, and 99% uncertainty intervals. P-values will be secondary diagnostics rather than the only decision criterion.

Count-model selection will be based on observed dispersion: Poisson when the dispersion ratio is at or below 1.5, otherwise negative binomial. Forecast models will be evaluated only with chronological holdouts against a simple city-month median baseline.

Step 7 model fitting has not yet started. SQLite integrity check: `ok`.
