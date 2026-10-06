import csv
import json
import math
import sqlite3
import statistics
from datetime import datetime, timezone
from pathlib import Path

from project_config import DB_PATH, OUTPUT_DIR

REPORT_PATH = OUTPUT_DIR / "urbanpulse_step5a_imputation_sensitivity.md"
SUMMARY_CSV_PATH = OUTPUT_DIR / "urbanpulse_step5a_imputation_summary.csv"
VALUES_CSV_PATH = OUTPUT_DIR / "urbanpulse_step5a_imputed_values.csv"


def fmt(value):
    if value is None:
        return "n.a."
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)) and float(value).is_integer():
        return f"{int(value):,}"
    return f"{float(value):,.4f}"


def sample_skewness(values):
    if len(values) < 3:
        return 0.0
    mean = statistics.mean(values)
    sd = statistics.stdev(values)
    if sd == 0:
        return 0.0
    n = len(values)
    return (n / ((n - 1) * (n - 2))) * sum(((value - mean) / sd) ** 3 for value in values)


def main():
    evaluated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM canonical_cleaned ORDER BY source_row_number").fetchall()

    # Use observed, quality-screened values to estimate missing values.
    valid_speed_ids = {
        row["record_id"] for row in rows
        if row["cleaned_avg_speed_kmph"] is not None and 0 <= row["cleaned_avg_speed_kmph"] <= 120
    }
    probable_temp_ids = {
        row["record_id"] for row in con.execute(
            "SELECT record_id FROM temperature_neighbor_validation WHERE final_decision='probable_error'"
        ).fetchall()
    }

    field_specs = [
        {
            "field_name": "traffic_volume",
            "column": "cleaned_traffic_volume",
            "variable_type": "numeric",
            "filter": lambda row: row["cleaned_traffic_volume"] is not None,
            "quality_filter": "Observed non-missing traffic values.",
        },
        {
            "field_name": "avg_speed_kmph",
            "column": "cleaned_avg_speed_kmph",
            "variable_type": "numeric",
            "filter": lambda row: row["record_id"] in valid_speed_ids,
            "quality_filter": "Observed speeds restricted to 0-120 km/h; -10, 150, and 200 are excluded from the estimate.",
        },
        {
            "field_name": "temperature_c",
            "column": "cleaned_temperature_c",
            "variable_type": "numeric",
            "filter": lambda row: row["cleaned_temperature_c"] is not None and row["record_id"] not in probable_temp_ids,
            "quality_filter": "Observed non-missing temperatures classified as not probable_error by the month-and-neighbor rule.",
        },
        {
            "field_name": "zone",
            "column": "cleaned_zone",
            "variable_type": "categorical",
            "filter": lambda row: row["cleaned_zone"] not in (None, ""),
            "quality_filter": "Observed non-missing canonical zones.",
        },
    ]

    methods = []
    estimates = {}
    for spec in field_specs:
        values = [row[spec["column"]] for row in rows if spec["filter"](row)]
        missing_count = sum(1 for row in rows if row[spec["column"]] in (None, ""))
        if spec["variable_type"] == "categorical":
            counts = {}
            for value in values:
                counts[value] = counts.get(value, 0) + 1
            estimate = sorted(counts.items(), key=lambda item: (-item[1], str(item[0])))[0][0]
            distribution_class = "categorical"
            method = "mode"
            skewness = None
            mean = None
            median = None
        else:
            values = [float(value) for value in values]
            mean = statistics.mean(values)
            median = statistics.median(values)
            skewness = sample_skewness(values)
            distribution_class = "normal_like" if abs(skewness) <= 0.5 else "skewed"
            method = "mean" if distribution_class == "normal_like" else "median"
            estimate = mean if method == "mean" else median
        estimates[spec["field_name"]] = estimate
        methods.append({
            "field_name": spec["field_name"],
            "variable_type": spec["variable_type"],
            "observed_n": len(values),
            "missing_n": missing_count,
            "mean": mean,
            "median": median,
            "skewness": skewness,
            "distribution_class": distribution_class,
            "method": method,
            "estimate_value": estimate,
            "quality_filter": spec["quality_filter"],
        })

    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS imputation_method (
            field_name TEXT PRIMARY KEY,
            variable_type TEXT NOT NULL,
            observed_n INTEGER NOT NULL,
            missing_n INTEGER NOT NULL,
            mean REAL,
            median REAL,
            skewness REAL,
            distribution_class TEXT NOT NULL,
            method TEXT NOT NULL CHECK (method IN ('mean','median','mode')),
            estimate_value TEXT NOT NULL,
            quality_filter TEXT NOT NULL,
            evaluated_at_utc TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS imputation_value (
            record_id TEXT NOT NULL,
            source_row_number INTEGER NOT NULL,
            field_name TEXT NOT NULL,
            original_value TEXT,
            imputed_value TEXT NOT NULL,
            method TEXT NOT NULL,
            distribution_class TEXT NOT NULL,
            estimate_value TEXT NOT NULL,
            primary_analysis_effect TEXT NOT NULL,
            evaluated_at_utc TEXT NOT NULL,
            PRIMARY KEY (record_id, field_name)
        );

        CREATE TABLE IF NOT EXISTS canonical_imputed_sensitivity (
            record_id TEXT PRIMARY KEY,
            source_row_number INTEGER NOT NULL,
            imputed_city TEXT,
            imputed_zone TEXT,
            imputed_timestamp_iso TEXT,
            observation_date TEXT,
            hour INTEGER,
            weekday INTEGER,
            month INTEGER,
            imputed_traffic_volume REAL,
            imputed_avg_speed_kmph REAL,
            imputed_public_transport_usage REAL,
            imputed_parking_occupancy_pct REAL,
            imputed_road_incidents REAL,
            imputed_waterlogging_reports REAL,
            imputed_power_outage_minutes REAL,
            imputed_citizen_complaints REAL,
            imputed_temperature_c REAL,
            imputation_count INTEGER NOT NULL,
            evaluated_at_utc TEXT NOT NULL
        );
        """
    )
    con.execute("DELETE FROM imputation_method")
    con.execute("DELETE FROM imputation_value")
    con.execute("DELETE FROM canonical_imputed_sensitivity")
    con.executemany(
        """
        INSERT INTO imputation_method
        (field_name, variable_type, observed_n, missing_n, mean, median, skewness, distribution_class, method, estimate_value, quality_filter, evaluated_at_utc)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        [
            (
                m["field_name"], m["variable_type"], m["observed_n"], m["missing_n"], m["mean"], m["median"], m["skewness"],
                m["distribution_class"], m["method"], str(m["estimate_value"]), m["quality_filter"], evaluated_at,
            )
            for m in methods
        ],
    )

    method_by_field = {m["field_name"]: m for m in methods}
    imputation_events = []
    imputed_rows = []
    for row in rows:
        values = {
            "city": row["cleaned_city"],
            "zone": row["cleaned_zone"],
            "timestamp_iso": row["cleaned_timestamp_iso"],
            "traffic_volume": row["cleaned_traffic_volume"],
            "avg_speed_kmph": row["cleaned_avg_speed_kmph"],
            "public_transport_usage": row["cleaned_public_transport_usage"],
            "parking_occupancy_pct": row["cleaned_parking_occupancy_pct"],
            "road_incidents": row["cleaned_road_incidents"],
            "waterlogging_reports": row["cleaned_waterlogging_reports"],
            "power_outage_minutes": row["cleaned_power_outage_minutes"],
            "citizen_complaints": row["cleaned_citizen_complaints"],
            "temperature_c": row["cleaned_temperature_c"],
        }
        original_by_field = dict(values)
        imputation_count = 0
        for field in ("zone", "traffic_volume", "avg_speed_kmph", "temperature_c"):
            if values[field] in (None, ""):
                method = method_by_field[field]
                values[field] = estimates[field]
                imputation_count += 1
                imputation_events.append(
                    (
                        row["record_id"], row["source_row_number"], field, original_by_field[field], str(values[field]), method["method"],
                        method["distribution_class"], str(method["estimate_value"]),
                        "Sensitivity analysis only; excluded from the primary observed-value analysis.", evaluated_at,
                    )
                )
        imputed_rows.append(
            (
                row["record_id"], row["source_row_number"], values["city"], values["zone"], values["timestamp_iso"], row["observation_date"], row["hour"], row["weekday"], row["month"],
                values["traffic_volume"], values["avg_speed_kmph"], values["public_transport_usage"], values["parking_occupancy_pct"], values["road_incidents"], values["waterlogging_reports"], values["power_outage_minutes"], values["citizen_complaints"], values["temperature_c"], imputation_count, evaluated_at,
            )
        )
    con.executemany("INSERT INTO imputation_value VALUES (?,?,?,?,?,?,?,?,?,?)", imputation_events)
    con.executemany("INSERT INTO canonical_imputed_sensitivity VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", imputed_rows)

    reason_prefix = "Step 5A sensitivity imputation:"
    con.execute("DELETE FROM quality_flag WHERE reason LIKE ?", (reason_prefix + "%",))
    con.executemany(
        """
        INSERT INTO quality_flag (record_id, source_row_number, field_name, flag_type, raw_value, cleaned_value, reason, primary_analysis_effect)
        VALUES (?,?,?,?,?,?,?,?)
        """,
        [
            (
                event[0], event[1], event[2], "imputed", event[3], event[4],
                f"{reason_prefix} {event[5]} used for {event[2]} based on {event[6]} screening.",
                "Sensitivity only; excluded from primary analysis.",
            )
            for event in imputation_events
        ],
    )
    con.execute("DELETE FROM quality_flag_summary")
    con.execute("INSERT INTO quality_flag_summary SELECT flag_type, field_name, COUNT(*) FROM quality_flag GROUP BY flag_type, field_name")
    con.execute("INSERT OR REPLACE INTO data_contract VALUES (?,?,?,?,?)", (
        "step5a_imputation_sensitivity",
        "Analysis",
        "Missing numeric values are estimated with mean for normal-like distributions and median for skewed distributions. Missing categorical values use mode. The imputed layer is sensitivity-only.",
        "COMPLETED_STEP_5A",
        "Do not use imputed values in the primary analysis. Use canonical observed values for the primary results.",
    ))
    con.execute("INSERT OR REPLACE INTO analysis_run VALUES (?,?,?,?)", (
        "step5a_imputation_sensitivity",
        "Statistical imputation sensitivity layer completed; canonical observed layer unchanged.",
        None,
        json.dumps({"imputation_events": len(imputation_events), "methods": {m["field_name"]: m["method"] for m in methods}, "primary_imputation": False}),
    ))
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.commit()
    con.close()

    with SUMMARY_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["field_name", "variable_type", "observed_n", "missing_n", "mean", "median", "skewness", "distribution_class", "method", "estimate_value", "quality_filter"])
        for m in methods:
            writer.writerow([m[k] for k in ["field_name", "variable_type", "observed_n", "missing_n", "mean", "median", "skewness", "distribution_class", "method", "estimate_value", "quality_filter"]])
    with VALUES_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["record_id", "source_row_number", "field_name", "original_value", "imputed_value", "method", "distribution_class", "estimate_value", "primary_analysis_effect"])
        for event in imputation_events:
            writer.writerow(event[:9])

    lines = [
        "# UrbanPulse Step 5A: Imputation Sensitivity Analysis",
        "",
        "This substep creates a separate imputed sensitivity layer. The immutable raw layer, canonical observed layer, and primary analysis remain unchanged.",
        "",
        "## Rules applied",
        "",
        "- Normal-like numeric distributions: mean.",
        "- Skewed numeric distributions: median.",
        "- Categorical variables: mode.",
        "- Distribution screening uses adjusted sample skewness. Absolute skewness at or below 0.5 is classified as normal-like. This is a screening rule, not a formal normality test.",
        "",
        "## Imputation methods",
        "",
        "| Field | Type | Observed n | Missing n | Skewness | Class | Method | Estimate |",
        "|---|---|---:|---:|---:|---|---|---:|",
    ]
    for m in methods:
        skew = "n.a." if m["skewness"] is None else f"{m['skewness']:.3f}"
        lines.append(f"| {m['field_name']} | {m['variable_type']} | {m['observed_n']:,} | {m['missing_n']:,} | {skew} | {m['distribution_class']} | {m['method']} | {fmt(m['estimate_value'])} |")
    lines += [
        "",
        f"Total imputation events: `{len(imputation_events):,}`.",
        "",
        "## Interpretation",
        "",
        "The missing numeric fields in this dataset were classified as normal-like under the screening rule, so their missing values use means. The missing zone values use the modal canonical zone. No skewed numeric field had missing values requiring median imputation in this dataset.",
        "",
        "The imputed layer is for sensitivity analysis only. The primary analysis uses observed canonical values and never uses imputed values. The primary view is not a global complete-case table: rows with unknown zone may remain for analyses that do not require zone; zone-based analyses must filter to observed zones. The original and canonical observed values are preserved.",
        "",
        f"SQLite integrity check: `{integrity}`.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(REPORT_PATH), "summary_csv": str(SUMMARY_CSV_PATH), "values_csv": str(VALUES_CSV_PATH), "imputation_events": len(imputation_events), "integrity": integrity, "methods": {m["field_name"]: m["method"] for m in methods}}, indent=2))


if __name__ == "__main__":
    main()
