# Parking Measurement Definition

## Provisional project definition

`parking_occupancy_pct` is treated provisionally as the reported percentage of designated parking capacity occupied at the recorded observation timestamp.

Conceptually:

```text
parking occupancy (%) = occupied parking spaces / total designated capacity × 100
```

## Required metadata

- Numerator: occupied parking spaces
- Denominator: total designated parking capacity
- Unit: percent
- Time grain: the recorded timestamp or source observation window
- Geographic scope: the associated city and zone
- Missing values: preserve as missing
- Expected ordinary range: 0% to 100%

## Values above 100%

Values above 100% are retained in the raw and canonical layers and flagged. They are not automatically corrected. They may represent over-capacity operation, a utilization index with a different denominator, sensor or aggregation behavior, or a source error.

## Interpretation status

This definition is suitable for the college project as a transparent working definition. It is not a confirmed source definition. The data owner or source documentation must confirm the numerator, denominator, observation window, and whether values above 100% are meaningful before the field is used for operational decisions.
