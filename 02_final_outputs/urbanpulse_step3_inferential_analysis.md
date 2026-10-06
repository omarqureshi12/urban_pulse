# UrbanPulse Step 3: Inferential Analysis

The dataset is treated as an intentionally sampled stream. Results describe associations and distribution differences within this sample. They do not estimate a complete city-zone panel or establish causality.

## Statistical standard

Primary relationship method: Spearman rank correlation with Fisher 99% intervals. Group method: permutation eta-squared with 5,000 permutations. Holm correction was applied within each pre-specified family at alpha = 0.01.

## Pre-specified relationships

| ID | Relationship | Expected direction | Spearman rho | 99% CI | Holm-adjusted p | Decision |
|---|---|---|---:|---|---:|---|
| H1 | Traffic volume vs Average speed | negative | 0.014 | [-0.052, 0.080] | 1.000 | Not significant at 99% |
| H2 | Traffic volume vs Road incidents | positive | -0.016 | [-0.081, 0.049] | 1.000 | Not significant at 99% |
| H3 | Waterlogging reports vs Average speed | negative | -0.010 | [-0.076, 0.055] | 1.000 | Not significant at 99% |
| H4 | Waterlogging reports vs Road incidents | positive | 0.018 | [-0.047, 0.082] | 1.000 | Not significant at 99% |
| H5 | Temperature vs Power outage minutes | positive | 0.001 | [-0.064, 0.066] | 1.000 | Not significant at 99% |
| H6 | Temperature vs Citizen complaints | positive | 0.005 | [-0.061, 0.070] | 1.000 | Not significant at 99% |
| H7 | Power outage minutes vs Citizen complaints | positive | -0.032 | [-0.097, 0.032] | 1.000 | Not significant at 99% |
| H8 | Road incidents vs Average speed | negative | -0.013 | [-0.078, 0.053] | 1.000 | Not significant at 99% |

## Sampled-group effects

| Factor | Tests | Significant after Holm at 99% | Largest eta-squared |
|---|---:|---:|---:|
| city | 9 | 0 | 0.006 |
| hour | 9 | 0 | 0.008 |
| month | 9 | 0 | 0.012 |
| zone | 9 | 0 | 0.006 |

### Largest observed group effects

| Factor | Metric | Groups | n | Eta-squared | Holm-adjusted p | Decision |
|---|---|---:|---:|---:|---:|---|
| month | Citizen complaints | 9 | 1,600 | 0.012 | 0.153 | Not significant at 99% |
| month | Road incidents | 9 | 1,600 | 0.011 | 0.277 | Not significant at 99% |
| hour | Waterlogging reports | 6 | 1,600 | 0.008 | 0.216 | Not significant at 99% |
| month | Traffic volume | 9 | 1,568 | 0.007 | 1.000 | Not significant at 99% |
| city | Road incidents | 7 | 1,600 | 0.006 | 1.000 | Not significant at 99% |
| month | Public transport usage | 9 | 1,600 | 0.006 | 1.000 | Not significant at 99% |
| zone | Public transport usage | 5 | 1,568 | 0.006 | 0.441 | Not significant at 99% |
| city | Waterlogging reports | 7 | 1,600 | 0.006 | 1.000 | Not significant at 99% |
| city | Traffic volume | 7 | 1,568 | 0.006 | 1.000 | Not significant at 99% |
| month | Parking occupancy | 9 | 1,600 | 0.005 | 1.000 | Not significant at 99% |
| hour | Average speed | 6 | 1,551 | 0.005 | 1.000 | Not significant at 99% |
| hour | Traffic volume | 6 | 1,568 | 0.004 | 1.000 | Not significant at 99% |

## Step 3 conclusion

None of the eight pre-specified relationships reached the 99% threshold after Holm correction (0 of 8 significant). None of the 36 city, zone, month, or hour effects reached the 99% threshold after family-wise correction (0 of 36 significant).

The data support a cautious statement that no practically clear relationship was detected in this intentionally sampled stream at the chosen confidence standard. This is not proof of independence or causality. Forecasting and predictive validation should be treated as a separate step.

SQLite integrity check: `ok`.
