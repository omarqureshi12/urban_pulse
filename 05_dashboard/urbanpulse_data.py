"""SQLite-backed data access and descriptive transformations for UrbanPulse."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "02_final_outputs" / "urbanpulse_rdbms.sqlite"

METRICS = {
    "traffic_volume": ("Traffic volume", "count"),
    "avg_speed_kmph": ("Average speed", "km/h"),
    "public_transport_usage": ("Public transport usage", "count"),
    "parking_occupancy_pct": ("Parking occupancy", "%"),
    "road_incidents": ("Road incidents", "count"),
    "waterlogging_reports": ("Waterlogging reports", "count"),
    "power_outage_minutes": ("Power outage", "minutes"),
    "citizen_complaints": ("Citizen complaints", "count"),
    "temperature_c": ("Temperature", "°C"),
}

DISPLAY_TO_COLUMN = {
    "Traffic volume": "traffic_volume",
    "Average speed": "avg_speed_kmph",
    "Public transport usage": "public_transport_usage",
    "Parking occupancy": "parking_occupancy_pct",
    "Road incidents": "road_incidents",
    "Waterlogging reports": "waterlogging_reports",
    "Power outage": "power_outage_minutes",
    "Citizen complaints": "citizen_complaints",
    "Temperature": "temperature_c",
}


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open the packaged database read-only at the application layer."""
    uri = f"file:{db_path}?mode=ro"
    return sqlite3.connect(uri, uri=True, check_same_thread=False)


def _in_clause(values: Iterable[str]) -> tuple[str, list[str]]:
    values = list(values)
    return ",".join("?" for _ in values), values


def available_options(con: sqlite3.Connection) -> dict[str, list]:
    cities = pd.read_sql_query(
        "SELECT DISTINCT cleaned_city AS value FROM canonical_cleaned WHERE cleaned_city IS NOT NULL ORDER BY value",
        con,
    )["value"].tolist()
    zones = pd.read_sql_query(
        """
        SELECT DISTINCT COALESCE(NULLIF(cleaned_zone, ''), 'Unknown') AS value
        FROM canonical_cleaned
        ORDER BY value
        """,
        con,
    )["value"].tolist()
    hours = pd.read_sql_query(
        "SELECT DISTINCT hour AS value FROM canonical_cleaned WHERE hour IS NOT NULL ORDER BY value",
        con,
    )["value"].astype(int).tolist()
    dates = pd.read_sql_query(
        "SELECT MIN(observation_date) AS min_date, MAX(observation_date) AS max_date FROM canonical_cleaned",
        con,
    ).iloc[0]
    return {
        "cities": cities,
        "zones": zones,
        "hours": hours,
        "min_date": pd.to_datetime(dates["min_date"]).date(),
        "max_date": pd.to_datetime(dates["max_date"]).date(),
    }


def load_filtered(
    con: sqlite3.Connection,
    cities: list[str] | None = None,
    zones: list[str] | None = None,
    start_date=None,
    end_date=None,
    hours: list[int] | None = None,
    primary_only: bool = False,
) -> pd.DataFrame:
    """Load canonical observed rows using explicit user-selected filters."""
    query = """
        SELECT
            record_id, cleaned_city AS city,
            COALESCE(NULLIF(cleaned_zone, ''), 'Unknown') AS zone,
            cleaned_timestamp_iso AS timestamp,
            observation_date, hour, weekday, month,
            cleaned_traffic_volume AS traffic_volume,
            cleaned_avg_speed_kmph AS avg_speed_kmph,
            cleaned_public_transport_usage AS public_transport_usage,
            cleaned_parking_occupancy_pct AS parking_occupancy_pct,
            cleaned_road_incidents AS road_incidents,
            cleaned_waterlogging_reports AS waterlogging_reports,
            cleaned_power_outage_minutes AS power_outage_minutes,
            cleaned_citizen_complaints AS citizen_complaints,
            cleaned_temperature_c AS temperature_c,
            row_quality_status,
            primary_analysis_eligible
        FROM canonical_cleaned
        WHERE 1=1
    """
    params: list = []
    if cities:
        clause, values = _in_clause(cities)
        query += f" AND cleaned_city IN ({clause})"
        params.extend(values)
    if zones:
        clause, values = _in_clause(zones)
        query += f" AND COALESCE(NULLIF(cleaned_zone, ''), 'Unknown') IN ({clause})"
        params.extend(values)
    if start_date is not None:
        query += " AND observation_date >= ?"
        params.append(str(start_date))
    if end_date is not None:
        query += " AND observation_date <= ?"
        params.append(str(end_date))
    if hours:
        clause, values = _in_clause([str(hour) for hour in hours])
        query += f" AND hour IN ({clause})"
        params.extend(hours)
    if primary_only:
        query += " AND primary_analysis_eligible = 1"
    query += " ORDER BY timestamp, record_id"
    frame = pd.read_sql_query(query, con, params=params)
    if not frame.empty:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"])
        frame["observation_date"] = pd.to_datetime(frame["observation_date"])
    return frame


def load_quality_flags(con: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        """
        SELECT flag_id, record_id, source_row_number, field_name, flag_type,
               raw_value, cleaned_value, reason, primary_analysis_effect
        FROM quality_flag
        ORDER BY flag_id
        """,
        con,
    )


def load_contracts(con: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        "SELECT contract_key, category, specification, current_status, action_required FROM data_contract ORDER BY contract_key",
        con,
    )


def load_provenance(con: sqlite3.Connection) -> tuple[pd.DataFrame, pd.DataFrame]:
    run = pd.read_sql_query(
        "SELECT run_id, protocol_id, simulation_repetitions, random_seed, row_count, status, completed_at_utc FROM provenance_run ORDER BY completed_at_utc DESC LIMIT 1",
        con,
    )
    diagnostics = pd.read_sql_query(
        """
        SELECT category, variable_x, variable_y, grouping, observed_value,
               sim_q005, sim_q995, observed_sim_percentile, flagged, interpretation
        FROM provenance_diagnostic
        WHERE run_id = (SELECT run_id FROM provenance_run ORDER BY completed_at_utc DESC LIMIT 1)
        ORDER BY flagged DESC, category, variable_x, variable_y
        """,
        con,
    )
    return run, diagnostics


def add_primary_metric_flags(frame: pd.DataFrame, flags: pd.DataFrame) -> pd.DataFrame:
    """Add metric-specific primary-analysis validity without changing values."""
    out = frame.copy()
    out["speed_primary_valid"] = out["avg_speed_kmph"].between(0, 120, inclusive="both")
    out["speed_primary_valid"] &= out["avg_speed_kmph"].notna()
    temp_outlier_ids = set(
        flags.loc[(flags["field_name"] == "temperature_c") & (flags["flag_type"] == "outlier"), "record_id"]
    )
    out["temperature_primary_valid"] = out["temperature_c"].notna()
    out["temperature_primary_valid"] &= ~out["record_id"].isin(temp_outlier_ids)
    return out


def completeness(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    fields = ["city", "zone", "timestamp"] + list(METRICS.keys())
    for field in fields:
        observed = int(frame[field].notna().sum())
        total = len(frame)
        rows.append({
            "Field": METRICS.get(field, (field.replace("_", " ").title(), ""))[0],
            "Observed": observed,
            "Missing": total - observed,
            "Complete (%)": round(100 * observed / total, 1) if total else 0.0,
        })
    return pd.DataFrame(rows)


def monthly_summary(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    work = frame.copy()
    work["Month"] = work["observation_date"].dt.to_period("M").astype(str)
    return work.groupby("Month", as_index=True)[columns].mean(numeric_only=True).round(2)


def hourly_summary(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    result = frame.groupby("hour", as_index=True)[columns].mean(numeric_only=True).round(2)
    result.index = [f"{int(hour):02d}:00" for hour in result.index]
    return result

