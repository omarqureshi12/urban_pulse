# UrbanPulse Step 8: Provenance Check

## Scope and null model

The canonical observed layer (1,600 rows) was compared with 5,000 simulated datasets. Each simulation independently permuted observed non-missing values within each metric while preserving the exact row count, marginal distribution, missingness mask, timestamp grid, city labels, and zone labels. This breaks cross-field alignment, city/zone alignment, and temporal alignment while keeping the one-dimensional distributions unchanged.

Random seed: `20261008`. A diagnostic is flagged when the observed value falls outside the simulated 0.500%-99.500% interval.

## Results

- Total diagnostics: 81.
- Flagged under the null: 0 (0 pairwise, 0 group-alignment, 0 temporal, 0 marginal-structure).
- Marginal entropy and unique-value-rate diagnostics were fixed by construction and produced no provenance separation.
- Raw-layer exact duplicate count reported separately: 35; the canonical layer is deduplicated.

### Flagged diagnostics

No diagnostic fell outside the predeclared null interval.

## Interpretation boundary

A flag means the observed cross-field, group, or temporal alignment is unusual relative to this independent-permutation null model. It can be described as a synthetic-looking or structurally unusual signal under this test, but it is not proof that the data were synthetically generated. Real operational data can also create unusual patterns through collection design, aggregation, filtering, or leakage. Source documentation, collection metadata, and system provenance are required for a provenance conclusion.

The raw workbook and canonical values were not overwritten.
