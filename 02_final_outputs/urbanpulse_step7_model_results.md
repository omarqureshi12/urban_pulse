# UrbanPulse Step 7: Fit-for-Purpose Model Results

Primary models use the canonical observed layer only. Missing values were not imputed. Effects are reported with 99% date-block bootstrap uncertainty intervals.

Bootstrap repetitions: `3,000`. Seed: `20261007`. SQLite integrity check: `ok`.

## Adjusted relationships

| Model | Relationship | n | Model | Effect | 99% interval | Standardized effect |
|---|---|---:|---|---:|---|---:|
| M3_relationship_traffic_speed | Traffic volume -> Average speed | 1,520 | huber | 0.1978 | [-0.4043, 0.7986] | 0.0184 |
| M4_relationship_incidents_waterlogging | Waterlogging reports -> Road incidents | 1,600 | poisson | IRR 1.0160 | [0.9669, 1.0643] | 0.0113 |
| M5_relationship_temperature_outage | Temperature -> Power outage minutes | 1,327 | huber | -0.0189 | [-0.1230, 0.0868] | -0.0090 |

## City and zone effects

The table reports the largest absolute adjusted contrast across groups for each target. Full group-level contrasts are in the CSV output.

| Factor | Target | Largest absolute native contrast | Range of 99% intervals | Largest standardized contrast |
|---|---|---:|---|---:|
| city | Average speed | 0.7761 | [-2.1966, 2.4616] | 0.0659 |
| city | Citizen complaints | 0.3220 | [-0.6986, 0.7251] | 0.1144 |
| city | Parking occupancy | 1.0395 | [-3.7980, 4.0706] | 0.0512 |
| city | Power outage minutes | 0.9076 | [-2.1547, 2.1821] | 0.0738 |
| city | Public transport usage | 60.5788 | [-148.5727, 193.6928] | 0.0874 |
| city | Road incidents | 0.2215 | [-0.3836, 0.4629] | 0.1584 |
| city | Temperature | 0.9282 | [-1.8626, 1.8127] | 0.1597 |
| city | Traffic volume | 143.6352 | [-324.5523, 325.4920] | 0.1305 |
| city | Waterlogging reports | 0.1547 | [-0.2236, 0.3335] | 0.1552 |
| zone | Average speed | 0.9179 | [-2.8923, 1.6716] | 0.0780 |
| zone | Citizen complaints | 0.2720 | [-0.7059, 0.7742] | 0.0966 |
| zone | Parking occupancy | 1.5394 | [-3.3746, 4.4738] | 0.0758 |
| zone | Power outage minutes | 0.8991 | [-2.0293, 1.3581] | 0.0731 |
| zone | Public transport usage | 79.1017 | [-179.4645, 197.6857] | 0.1142 |
| zone | Road incidents | 0.0644 | [-0.2746, 0.3290] | 0.0461 |
| zone | Temperature | 0.5524 | [-1.1688, 1.2231] | 0.0951 |
| zone | Traffic volume | 28.2409 | [-219.3969, 195.2631] | 0.0256 |
| zone | Waterlogging reports | 0.0240 | [-0.1708, 0.1732] | 0.0241 |

## Count-model selection

Poisson was used only when the observed dispersion ratio was at or below 1.5. Otherwise, negative binomial was used.

| Target | n | Selected model | Dispersion ratio | Mean count |
|---|---:|---|---:|---:|
| Citizen complaints | 1,568 | poisson | 0.991 | 7.955 |
| Public transport usage | 1,568 | negative_binomial | 372.228 | 1296.972 |
| Road incidents | 1,568 | poisson | 0.988 | 1.966 |
| Traffic volume | 1,537 | negative_binomial | 593.493 | 2053.001 |
| Waterlogging reports | 1,568 | poisson | 0.965 | 1.023 |

## Forecasting

Forecasts use three expanding chronological holdouts and are compared with a city-month median baseline.

| Metric | Mean baseline MAE | Mean model MAE | Mean improvement | Mean R² | Improvement interval range | R² interval range |
|---|---:|---:|---:|---:|---|---|
| Average speed | 10.754 | 9.877 | 7.1% | -0.032 | [-9.3%, 32.2%] | [-0.181, 0.085] |
| Citizen complaints | 2.404 | 5.709 | -137.6% | -4.560 | [-191.2%, -86.2%] | [-7.556, -3.096] |
| Parking occupancy | 18.990 | 17.478 | 7.6% | -0.075 | [-3.7%, 25.0%] | [-0.322, 0.026] |
| Power outage minutes | 9.141 | 8.870 | 2.8% | -0.087 | [-10.3%, 14.5%] | [-0.225, 0.036] |
| Public transport usage | 621.056 | 1264.300 | -106.8% | -3.458 | [-191.7%, -49.1%] | [-6.361, -2.285] |
| Road incidents | 1.097 | 1.358 | -24.4% | -0.725 | [-57.8%, 15.0%] | [-1.281, -0.274] |
| Temperature | 5.022 | 4.644 | 5.2% | -0.123 | [-24.3%, 34.6%] | [-0.508, 0.076] |
| Traffic volume | 1082.443 | 2104.534 | -96.4% | -3.766 | [-163.3%, -40.0%] | [-5.780, -2.488] |
| Waterlogging reports | 0.814 | 0.972 | -20.3% | -0.743 | [-59.7%, 13.6%] | [-1.337, -0.282] |

## Interpretation

The fitted models quantify adjusted effects and uncertainty for the sampled stream. They do not convert this intentional sample into a complete city-zone panel or establish causality. Any imputation-based model comparison remains a separate sensitivity task.

## Outputs

Group effects: `/Users/apple/Documents/Codex/2026-10-01/rea/outputs/urbanpulse_step7_group_effects.csv`
Adjusted relationships: `/Users/apple/Documents/Codex/2026-10-01/rea/outputs/urbanpulse_step7_adjusted_relationships.csv`
Count-model selection: `/Users/apple/Documents/Codex/2026-10-01/rea/outputs/urbanpulse_step7_count_models.csv`
Forecast results: `/Users/apple/Documents/Codex/2026-10-01/rea/outputs/urbanpulse_step7_forecast_results.csv`
