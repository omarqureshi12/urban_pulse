# Power-Outage Measurement Definition

## Working project definition

`power_outage_minutes` is treated as the source-reported average outage duration, in minutes, for a city zone during each four-hour observation window.

## Confirmed rules

- Observation window: four hours
- Aggregation: average outage duration reported for the zone-window
- Geographic scope: zone-wise
- Event types: regular, planned, unplanned, and short interruptions are included
- Overlapping events: outage durations are added together
- Missing values: preserve as missing

## Timestamp limitation

The source definition still needs to state whether the recorded timestamp identifies the start, end, or label of the four-hour window. Until that is confirmed, the timestamp is treated only as the observation reference for the zone-window.

## Interpretation of values above 60 minutes

Values above 60 minutes are plausible under a four-hour window and are retained. They remain flagged in the quality layer for traceability, but they are not automatically classified as errors.
