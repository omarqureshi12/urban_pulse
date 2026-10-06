# UrbanPulse Step 8: Provenance-Check Protocol

This protocol compares the canonical observed data with simulations that preserve the same marginal distributions and missingness pattern while breaking cross-field and temporal alignment.

## Null simulation

- Keep the 1,600 canonical rows, timestamps, row IDs, and missingness mask unchanged.
- Independently permute observed non-missing values within each non-structural field.
- Preserve every field's marginal distribution exactly.
- Generate 5,000 simulated datasets.

## Diagnostics

- Absolute pairwise Spearman correlations.
- City and zone eta-squared alignment.
- Within-city lag-1 temporal autocorrelation.
- Entropy and unique-value rates for discrete measures.
- Raw-layer duplicate structure reported separately because exact duplicates were already removed from the canonical layer.

## Flag rule

An observed statistic will be flagged when it falls outside the simulated 0.5th-99.5th percentile interval. The result will be described as unusual or synthetic-looking under this null model only. It will not be presented as proof of synthetic origin.

Step 8 simulation has not yet been run. Source documentation or collection metadata remains necessary for any provenance conclusion.

SQLite integrity check: `ok`.
