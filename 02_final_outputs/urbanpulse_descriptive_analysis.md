# UrbanPulse Step 3: Descriptive Analysis

This step describes the observed sampled data. It does not impute missing values, rank cities, or make inferential claims. Speed values below 0 or above 120 km/h are excluded from speed summaries only. Other flagged extremes are retained.

Bootstrap confidence intervals: 99% with 3,000 repetitions. Random seed: 20261003.

## Coverage profile

### City counts

| City | Observed rows |
|---|---:|
| Pune | 242 |
| Indore | 240 |
| Jaipur | 231 |
| Delhi | 231 |
| Nagpur | 229 |
| Bengaluru | 223 |
| Bhopal | 204 |

### Zone counts

| Zone | Observed rows |
|---|---:|
| Central | 449 |
| North | 437 |
| West | 238 |
| East | 237 |
| South | 207 |
| [UNKNOWN] | 32 |

### Time coverage

| Month | Rows |
|---:|---:|
| 1 | 186 |
| 2 | 168 |
| 3 | 186 |
| 4 | 180 |
| 5 | 186 |
| 6 | 180 |
| 7 | 186 |
| 8 | 186 |
| 9 | 142 |

| Hour | Rows |
|---|---:|
| 00:00 | 267 |
| 04:00 | 267 |
| 08:00 | 267 |
| 12:00 | 267 |
| 16:00 | 266 |
| 20:00 | 266 |

## Overall metric distributions

| Metric | n | Mean | Median | SD | Min | Q1 | Q3 | Max | 99% CI for mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Average speed (km/h) | 1,551 | 38.16 | 37.90 | 11.78 | 3.00 | 30.50 | 46.00 | 85.10 | [37.43, 38.90] |
| Citizen complaints | 1,600 | 7.95 | 8.00 | 2.80 | 1.00 | 6.00 | 10.00 | 17.00 | [7.78, 8.13] |
| Parking occupancy (%) | 1,600 | 68.14 | 67.90 | 20.32 | 5.00 | 53.85 | 82.10 | 110.00 | [66.83, 69.42] |
| Power outage (minutes) | 1,600 | 11.88 | 8.00 | 12.36 | 0.00 | 3.30 | 16.52 | 127.20 | [11.10, 12.69] |
| Public transport usage | 1,600 | 1,298.67 | 1,305.00 | 694.02 | 100.00 | 698.25 | 1,889.50 | 2,498.00 | [1,256.23, 1,341.63] |
| Road incidents | 1,600 | 1.96 | 2.00 | 1.39 | 0.00 | 1.00 | 3.00 | 8.00 | [1.87, 2.05] |
| Temperature (C) | 1,568 | 28.93 | 28.95 | 7.05 | 6.40 | 24.08 | 33.42 | 53.80 | [28.50, 29.42] |
| Traffic volume | 1,568 | 2,050.95 | 2,008.50 | 1,100.07 | 214.00 | 1,080.75 | 3,015.25 | 3,999.00 | [1,980.42, 2,119.73] |
| Waterlogging reports | 1,600 | 1.02 | 1.00 | 1.00 | 0.00 | 0.00 | 2.00 | 6.00 | [0.96, 1.09] |

## City descriptive ranges

These are unadjusted descriptive means of sampled observations. They are not city rankings because the dataset is not a synchronized full panel.

| Metric | Highest observed mean | Lowest observed mean | Range |
|---|---|---|---:|
| Traffic volume | Bhopal (2,184.23) | Delhi (1,926.68) | 257.55 |
| Average speed (km/h) | Bengaluru (38.79) | Nagpur (37.68) | 1.11 |
| Public transport usage | Bhopal (1,369.08) | Indore (1,257.50) | 111.58 |
| Parking occupancy (%) | Nagpur (69.51) | Delhi (67.38) | 2.13 |
| Road incidents | Nagpur (2.15) | Indore (1.80) | 0.35 |
| Waterlogging reports | Bengaluru (1.18) | Indore (0.95) | 0.23 |
| Power outage (minutes) | Pune (12.43) | Delhi (10.74) | 1.70 |
| Citizen complaints | Jaipur (8.13) | Indore (7.64) | 0.50 |
| Temperature (C) | Delhi (29.36) | Jaipur (28.67) | 0.69 |

## Zone descriptive ranges

Zone means are shown for description only. The Unknown group remains separate, and the zone distribution is unbalanced.

| Metric | Highest observed mean | Lowest observed mean | Range |
|---|---|---|---:|
| Traffic volume | North (2,079.29) | [UNKNOWN] (1,949.23) | 130.07 |
| Average speed (km/h) | North (38.69) | East (36.96) | 1.73 |
| Public transport usage | [UNKNOWN] (1,382.00) | West (1,219.00) | 163.00 |
| Parking occupancy (%) | East (69.51) | Central (67.05) | 2.46 |
| Road incidents | East (2.03) | [UNKNOWN] (1.62) | 0.41 |
| Waterlogging reports | South (1.05) | [UNKNOWN] (0.94) | 0.11 |
| Power outage (minutes) | [UNKNOWN] (13.89) | East (10.91) | 2.97 |
| Citizen complaints | South (8.17) | West (7.72) | 0.46 |
| Temperature (C) | South (29.22) | Central (28.47) | 0.76 |

## Descriptive conclusion

The observed sample is broadly balanced across cities, uneven across zones, and evenly distributed across the four-hour schedule. The metric summaries show wide variation within the sample, but this step does not establish whether those differences are meaningful or causal. The next inferential step should remain conditional on confirmation of the intended row grain.

SQLite integrity check: `ok`.
