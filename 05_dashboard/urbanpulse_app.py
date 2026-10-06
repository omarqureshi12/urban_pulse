"""UrbanPulse Streamlit dashboard.

The app reads the packaged SQLite database in read-only mode and never writes
to raw, canonical, or sensitivity layers.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import altair as alt


APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from urbanpulse_data import (  # noqa: E402
    METRICS,
    add_primary_metric_flags,
    available_options,
    completeness,
    connect,
    hourly_summary,
    load_contracts,
    load_filtered,
    load_provenance,
    load_quality_flags,
    monthly_summary,
)


st.set_page_config(
    page_title="UrbanPulse Smart-City Analytics",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def get_connection():
    return connect()


def metric_mean(frame: pd.DataFrame, column: str) -> float | None:
    valid = frame[column].notna()
    if column == "avg_speed_kmph":
        valid &= frame[column].between(0, 120, inclusive="both")
    if column == "temperature_c" and "temperature_primary_valid" in frame:
        valid &= frame["temperature_primary_valid"]
    values = frame.loc[valid, column]
    return float(values.mean()) if not values.empty else None


def fmt(value: float | int | None, digits: int = 1) -> str:
    if value is None:
        return "n.a."
    if isinstance(value, int) or float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.{digits}f}"


def grouped_summary(frame: pd.DataFrame, group_column: str, label: str) -> pd.DataFrame:
    records = []
    for group_value, group in frame.groupby(group_column, dropna=False):
        row = {label: group_value, "Rows": len(group)}
        for column, (metric_label, _) in METRICS.items():
            row[metric_label] = metric_mean(group, column)
        records.append(row)
    if not records:
        return pd.DataFrame(columns=[label, "Rows"] + [label for label, _ in METRICS.values()])
    return pd.DataFrame(records).sort_values(label).reset_index(drop=True)


def row_count_chart(frame: pd.DataFrame, group_column: str, label: str):
    chart_data = frame.groupby(group_column).size().reset_index(name="Rows")
    return (
        alt.Chart(chart_data)
        .mark_bar()
        .encode(
            x=alt.X(f"{group_column}:N", sort=None, title=label),
            y=alt.Y("Rows:Q", title="Rows", scale=alt.Scale(zero=True)),
            tooltip=[
                alt.Tooltip(f"{group_column}:N", title=label),
                alt.Tooltip("Rows:Q", format=",", title="Rows"),
            ],
        )
        .properties(height=280)
    )


def render_overview(frame: pd.DataFrame, flags: pd.DataFrame) -> None:
    st.header("Overview and coverage")
    st.caption("Descriptive results for the intentionally sampled UrbanPulse stream.")
    metric_cols = st.columns(4)
    metric_cols[0].metric("Filtered rows", f"{len(frame):,}")
    metric_cols[1].metric("Cities", f"{frame['city'].nunique():,}")
    metric_cols[2].metric("Zones", f"{frame['zone'].nunique():,}")
    metric_cols[3].metric("Filtered flags", f"{len(flags):,}")

    st.info(
        "Primary results use observed values only. Imputed values are not used here. "
        "This sample is not a complete city-zone-time panel and should not be used to produce official city rankings."
    )
    st.subheader("Completeness")
    st.dataframe(completeness(frame), hide_index=True, width="stretch")

    if frame.empty:
        st.warning("No rows match the current filters, so row-count charts are unavailable.")
    else:
        left, right = st.columns(2)
        with left:
            st.subheader("Rows by city")
            st.altair_chart(row_count_chart(frame, "city", "City"), width="stretch")
        with right:
            st.subheader("Rows by zone")
            st.altair_chart(row_count_chart(frame, "zone", "Zone"), width="stretch")


def render_comparisons(frame: pd.DataFrame) -> None:
    st.header("City and zone descriptive comparison")
    st.caption("Means are descriptive summaries of the selected sample, not official rankings.")
    st.subheader("City summary")
    st.dataframe(grouped_summary(frame, "city", "City"), hide_index=True, width="stretch")
    st.subheader("Zone summary")
    st.dataframe(grouped_summary(frame, "zone", "Zone"), hide_index=True, width="stretch")


def render_mobility(frame: pd.DataFrame) -> None:
    st.header("Traffic and mobility")
    st.caption("Speed summaries exclude missing and out-of-domain values. Parking remains a provisional source metric.")
    work = frame.copy()
    work.loc[~work["speed_primary_valid"], "avg_speed_kmph"] = pd.NA
    monthly = monthly_summary(
        work,
        ["traffic_volume", "public_transport_usage", "parking_occupancy_pct", "avg_speed_kmph"],
    )
    hourly = hourly_summary(
        work,
        ["traffic_volume", "public_transport_usage", "parking_occupancy_pct", "avg_speed_kmph"],
    )

    st.subheader("Monthly observed means")
    if monthly.empty:
        st.warning("No rows match the current filters.")
    else:
        st.line_chart(monthly[["traffic_volume", "public_transport_usage"]])
        st.line_chart(monthly[["avg_speed_kmph"]])
        st.dataframe(monthly, width="stretch")

    st.subheader("Four-hour slot means")
    if not hourly.empty:
        st.dataframe(hourly, width="stretch")


def render_environment(frame: pd.DataFrame) -> None:
    st.header("Incidents, environment, and outages")
    st.caption(
        "Power outage is treated as a partially confirmed four-hour zone average. "
        "The timestamp role remains pending confirmation."
    )
    work = frame.copy()
    work.loc[~work["temperature_primary_valid"], "temperature_c"] = pd.NA
    monthly = monthly_summary(
        work,
        [
            "road_incidents",
            "waterlogging_reports",
            "power_outage_minutes",
            "citizen_complaints",
            "temperature_c",
        ],
    )
    if monthly.empty:
        st.warning("No rows match the current filters.")
        return
    st.subheader("Monthly observed means")
    st.line_chart(
        monthly[["road_incidents", "waterlogging_reports", "citizen_complaints"]],
    )
    st.line_chart(monthly[["power_outage_minutes", "temperature_c"]])
    st.dataframe(monthly, width="stretch")
    st.markdown(
        "Parking definition: reported occupied capacity percentage, provisionally interpreted as "
        "occupied spaces divided by designated capacity. Values above 100% remain flagged."
    )


def render_quality(frame: pd.DataFrame, all_flags: pd.DataFrame) -> None:
    st.header("Data quality and provenance")
    filtered_ids = set(frame["record_id"])
    flags = all_flags[all_flags["record_id"].isin(filtered_ids)].copy()
    if flags.empty:
        st.info("No quality flags match the current filters.")
        return

    st.subheader("Flag summary")
    summary = (
        flags.groupby(["flag_type", "field_name"], as_index=False)
        .size()
        .rename(columns={"size": "Flag count"})
        .sort_values(["flag_type", "field_name"])
    )
    st.dataframe(summary, hide_index=True, width="stretch")

    st.subheader("Flag detail")
    flag_types = sorted(flags["flag_type"].dropna().unique().tolist())
    selected_types = st.multiselect("Flag types", flag_types, default=flag_types)
    detail = flags[flags["flag_type"].isin(selected_types)]
    st.dataframe(detail, hide_index=True, width="stretch")

    st.subheader("Primary-analysis policy")
    st.markdown(
        "- Missing numeric values remain missing in the primary layer.\n"
        "- Confirmed errors are corrected only when supported.\n"
        "- Valid extremes are retained and flagged.\n"
        "- Unknown values are preserved and excluded or analyzed separately.\n"
        "- Imputation flags belong to the sensitivity layer and do not replace primary results."
    )

    _, provenance = load_provenance(get_connection())
    st.subheader("Provenance simulation")
    if provenance.empty:
        st.warning("No provenance simulation record is available.")
    else:
        flagged = int(provenance["flagged"].sum())
        st.metric("Diagnostics flagged", flagged)
        st.dataframe(provenance[provenance["flagged"] == 1], hide_index=True, width="stretch")
        if flagged == 0:
            st.success("No diagnostics were unusual under the independent-permutation null. This is not proof of authenticity.")


def render_methodology(con) -> None:
    st.header("Definitions, methods, and limitations")
    st.info(
        "Final classification: Fit only for descriptive reporting. "
        "The project supports dashboards, training, and pipeline testing, not operational control, causal claims, or production forecasting."
    )
    st.subheader("Current data contract")
    contracts = load_contracts(con)
    st.dataframe(contracts, hide_index=True, width="stretch")

    st.subheader("Metric definitions used in this dashboard")
    st.markdown(
        "**Parking occupancy:** provisional reported occupied capacity percentage at the observation timestamp. "
        "Values above 100% are retained and flagged.\n\n"
        "**Power outage:** partially confirmed source-reported average outage duration in minutes for a zone during a four-hour window. "
        "Regular, planned, unplanned, and short interruptions are included, with overlapping durations added together. "
        "The timestamp role remains pending.\n\n"
        "**Temperature and speed:** primary summaries apply the recorded quality-screening rules. "
        "Unverified source or station semantics remain visible as limitations."
    )

    st.subheader("Provenance result")
    run, diagnostics = load_provenance(con)
    if not run.empty:
        latest = run.iloc[0]
        st.write(
            f"{int(latest['simulation_repetitions']):,} simulations completed with "
            f"{int(diagnostics['flagged'].sum()) if not diagnostics.empty else 0} flagged diagnostics."
        )
    st.subheader("Use limitations")
    st.markdown(
        "- The data are intentionally sampled and are not a complete city-zone-time panel.\n"
        "- City and zone summaries are descriptive only.\n"
        "- The absence of provenance flags does not prove the source is authentic.\n"
        "- Source documentation is still required for unresolved semantic questions."
    )


con = get_connection()
options = available_options(con)
all_flags = load_quality_flags(con)

st.sidebar.title("UrbanPulse")
st.sidebar.caption("Descriptive smart-city analytics")
if st.sidebar.button("Refresh database view"):
    st.cache_data.clear()
    st.rerun()

page = st.sidebar.radio(
    "Page",
    [
        "Overview",
        "City and zone comparison",
        "Traffic and mobility",
        "Incidents and environment",
        "Data quality and provenance",
        "Definitions and limitations",
    ],
)

st.sidebar.markdown("---")
selected_cities = st.sidebar.multiselect("City", options["cities"], default=options["cities"])
selected_zones = st.sidebar.multiselect("Zone", options["zones"], default=options["zones"])
date_value = st.sidebar.date_input(
    "Observation date range",
    value=(options["min_date"], options["max_date"]),
    min_value=options["min_date"],
    max_value=options["max_date"],
)
if isinstance(date_value, (tuple, list)) and len(date_value) == 2:
    start_date, end_date = date_value
else:
    start_date = end_date = date_value
selected_hours = st.sidebar.multiselect(
    "Observation time slot",
    options["hours"],
    default=options["hours"],
    format_func=lambda hour: f"{int(hour):02d}:00",
)
view_mode = st.sidebar.radio(
    "Row view",
    ["Canonical observed rows", "Primary-analysis eligible rows"],
)

primary_only = view_mode == "Primary-analysis eligible rows"
frame = load_filtered(
    con,
    cities=selected_cities,
    zones=selected_zones,
    start_date=start_date,
    end_date=end_date,
    hours=selected_hours,
    primary_only=primary_only,
)
frame = add_primary_metric_flags(frame, all_flags)

st.title("UrbanPulse Smart-City Analytics")
st.caption(
    "Database-backed descriptive dashboard. No imputation is used in primary views. "
    "The sample is intentionally sampled."
)

if page == "Definitions and limitations":
    render_methodology(con)
elif frame.empty:
    st.warning("No observations match the selected filters.")
else:
    if page == "Overview":
        render_overview(frame, all_flags[all_flags["record_id"].isin(set(frame["record_id"]))])
    elif page == "City and zone comparison":
        render_comparisons(frame)
    elif page == "Traffic and mobility":
        render_mobility(frame)
    elif page == "Incidents and environment":
        render_environment(frame)
    elif page == "Data quality and provenance":
        render_quality(frame, all_flags)
