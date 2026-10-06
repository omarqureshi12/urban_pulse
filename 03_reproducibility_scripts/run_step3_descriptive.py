import csv
import math
import os
import sqlite3

import numpy as np

from project_config import DB_PATH, OUTPUT_DIR

REPORT_PATH = OUTPUT_DIR / "urbanpulse_descriptive_analysis.md"
CSV_PATH = OUTPUT_DIR / "urbanpulse_descriptive_summary.csv"
SEED = 20261003
BOOTSTRAP_REPS = 3000

METRICS = [
    "traffic_volume",
    "avg_speed_kmph",
    "public_transport_usage",
    "parking_occupancy_pct",
    "road_incidents",
    "waterlogging_reports",
    "power_outage_minutes",
    "citizen_complaints",
    "temperature_c",
]

LABELS = {
    "traffic_volume": "Traffic volume",
    "avg_speed_kmph": "Average speed (km/h)",
    "public_transport_usage": "Public transport usage",
    "parking_occupancy_pct": "Parking occupancy (%)",
    "road_incidents": "Road incidents",
    "waterlogging_reports": "Waterlogging reports",
    "power_outage_minutes": "Power outage (minutes)",
    "citizen_complaints": "Citizen complaints",
    "temperature_c": "Temperature (C)",
}


def valid(metric, value):
    if value is None:
        return False
    if metric == "avg_speed_kmph":
        return 0 <= float(value) <= 120
    return True


def bootstrap_ci(values, rng):
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return None, None
    batches = []
    for start in range(0, BOOTSTRAP_REPS, 500):
        size = min(500, BOOTSTRAP_REPS - start)
        samples = rng.choice(values, size=(size, len(values)), replace=True)
        batches.append(samples.mean(axis=1))
    boot = np.concatenate(batches)
    return tuple(float(x) for x in np.quantile(boot, [0.005, 0.995]))


def fmt(value, digits=2):
    if value is None:
        return "n/a"
    return f"{value:,.{digits}f}"


def summarize(values, rng):
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return [0, None, None, None, None, None, None, None, None]
    lower, upper = bootstrap_ci(values, rng)
    return [
        int(len(values)),
        float(values.mean()),
        float(np.median(values)),
        float(values.std(ddof=1)) if len(values) > 1 else 0.0,
        float(values.min()),
        float(np.quantile(values, 0.25)),
        float(np.quantile(values, 0.75)),
        float(values.max()),
        lower,
        upper,
    ]


def main():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS descriptive_summary (
            dimension TEXT NOT NULL,
            group_value TEXT NOT NULL,
            metric TEXT NOT NULL,
            n_observed INTEGER NOT NULL,
            mean REAL,
            median REAL,
            std_dev REAL,
            min_value REAL,
            q1 REAL,
            q3 REAL,
            max_value REAL,
            ci99_lower REAL,
            ci99_upper REAL,
            exclusion_rule TEXT NOT NULL,
            PRIMARY KEY (dimension, group_value, metric)
        )
    """)
    con.execute("DELETE FROM descriptive_summary")
    columns = [
        "record_id", "city", "zone_canonical", "month", "hour", "weekday", *METRICS
    ]
    rows = con.execute("SELECT " + ",".join(columns) + " FROM urbanpulse_clean").fetchall()
    indices = {name: i for i, name in enumerate(columns)}
    rng = np.random.default_rng(SEED)

    dimensions = {
        "overall": lambda row: "ALL",
        "city": lambda row: row[indices["city"]],
        "zone": lambda row: row[indices["zone_canonical"]] or "[UNKNOWN]",
        "month": lambda row: str(row[indices["month"]]),
        "hour": lambda row: str(row[indices["hour"]]).zfill(2) + ":00",
        "weekday": lambda row: str(row[indices["weekday"]]),
    }
    output_rows = []
    for dimension, get_group in dimensions.items():
        groups = {}
        for row in rows:
            groups.setdefault(str(get_group(row)), []).append(row)
        for group_value, group_rows in sorted(groups.items(), key=lambda item: item[0]):
            for metric in METRICS:
                metric_index = indices[metric]
                values = [float(row[metric_index]) for row in group_rows if valid(metric, row[metric_index])]
                summary = summarize(values, rng)
                output_rows.append((dimension, group_value, metric, *summary, "missing excluded; avg_speed_kmph additionally excludes values outside 0-120"))

    con.executemany("INSERT INTO descriptive_summary VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", output_rows)
    con.execute("INSERT OR REPLACE INTO analysis_run VALUES (?,?,?,?)", ("descriptive_step3", "Completed descriptive summaries by overall, city, zone, month, hour, and weekday using observed values only.", None, '{"confidence_level":0.99,"bootstrap_repetitions":3000,"seed":20261003}'))
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.commit()

    overall = con.execute("""
        SELECT metric,n_observed,mean,median,std_dev,min_value,q1,q3,max_value,ci99_lower,ci99_upper
        FROM descriptive_summary WHERE dimension='overall' ORDER BY metric
    """).fetchall()
    cities = con.execute("""
        SELECT metric,group_value,n_observed,mean,ci99_lower,ci99_upper
        FROM descriptive_summary WHERE dimension='city' ORDER BY metric,mean DESC
    """).fetchall()
    zones = con.execute("""
        SELECT metric,group_value,n_observed,mean,ci99_lower,ci99_upper
        FROM descriptive_summary WHERE dimension='zone' ORDER BY metric,mean DESC
    """).fetchall()
    month_counts = con.execute("SELECT CAST(month AS TEXT),COUNT(*) FROM urbanpulse_clean GROUP BY month ORDER BY month").fetchall()
    hour_counts = con.execute("SELECT printf('%02d:00',hour),COUNT(*) FROM urbanpulse_clean GROUP BY hour ORDER BY hour").fetchall()
    city_counts = con.execute("SELECT city,COUNT(*) FROM urbanpulse_clean GROUP BY city ORDER BY COUNT(*) DESC").fetchall()
    zone_counts = con.execute("SELECT COALESCE(zone_canonical,'[UNKNOWN]'),COUNT(*) FROM urbanpulse_clean GROUP BY zone_canonical ORDER BY COUNT(*) DESC").fetchall()
    con.close()

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["dimension", "group_value", "metric", "n_observed", "mean", "median", "std_dev", "min_value", "q1", "q3", "max_value", "ci99_lower", "ci99_upper", "exclusion_rule"])
        writer.writerows(output_rows)

    lines = [
        "# UrbanPulse Step 3: Descriptive Analysis",
        "",
        "This step describes the observed sampled data. It does not impute missing values, rank cities, or make inferential claims. Speed values below 0 or above 120 km/h are excluded from speed summaries only. Other flagged extremes are retained.",
        "",
        f"Bootstrap confidence intervals: 99% with {BOOTSTRAP_REPS:,} repetitions. Random seed: {SEED}.",
        "",
        "## Coverage profile",
        "",
        "### City counts",
        "",
        "| City | Observed rows |",
        "|---|---:|",
    ]
    lines.extend(f"| {city} | {count:,} |" for city, count in city_counts)
    lines += ["", "### Zone counts", "", "| Zone | Observed rows |", "|---|---:|"]
    lines.extend(f"| {zone} | {count:,} |" for zone, count in zone_counts)
    lines += ["", "### Time coverage", "", "| Month | Rows |", "|---:|---:|"]
    lines.extend(f"| {month} | {count:,} |" for month, count in month_counts)
    lines += ["", "| Hour | Rows |", "|---|---:|"]
    lines.extend(f"| {hour} | {count:,} |" for hour, count in hour_counts)
    lines += ["", "## Overall metric distributions", "", "| Metric | n | Mean | Median | SD | Min | Q1 | Q3 | Max | 99% CI for mean |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for metric, n, mean, median, sd, min_value, q1, q3, max_value, lower, upper in overall:
        lines.append(f"| {LABELS[metric]} | {n:,} | {fmt(mean)} | {fmt(median)} | {fmt(sd)} | {fmt(min_value)} | {fmt(q1)} | {fmt(q3)} | {fmt(max_value)} | [{fmt(lower)}, {fmt(upper)}] |")

    lines += ["", "## City descriptive ranges", "", "These are unadjusted descriptive means of sampled observations. They are not city rankings because the dataset is not a synchronized full panel.", "", "| Metric | Highest observed mean | Lowest observed mean | Range |", "|---|---|---|---:|"]
    for metric in METRICS:
        entries = [row for row in cities if row[0] == metric]
        high, low = entries[0], entries[-1]
        lines.append(f"| {LABELS[metric]} | {high[1]} ({fmt(high[3])}) | {low[1]} ({fmt(low[3])}) | {fmt(high[3]-low[3])} |")

    lines += ["", "## Zone descriptive ranges", "", "Zone means are shown for description only. The Unknown group remains separate, and the zone distribution is unbalanced.", "", "| Metric | Highest observed mean | Lowest observed mean | Range |", "|---|---|---|---:|"]
    for metric in METRICS:
        entries = [row for row in zones if row[0] == metric]
        high, low = entries[0], entries[-1]
        lines.append(f"| {LABELS[metric]} | {high[1]} ({fmt(high[3])}) | {low[1]} ({fmt(low[3])}) | {fmt(high[3]-low[3])} |")

    lines += ["", "## Descriptive conclusion", "", "The observed sample is broadly balanced across cities, uneven across zones, and evenly distributed across the four-hour schedule. The metric summaries show wide variation within the sample, but this step does not establish whether those differences are meaningful or causal. The next inferential step should remain conditional on confirmation of the intended row grain.", "", f"SQLite integrity check: `{integrity}`."]
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print({
        "report": REPORT_PATH,
        "csv": CSV_PATH,
        "descriptive_rows": len(output_rows),
        "overall_metrics": len(overall),
        "integrity": integrity,
    })


if __name__ == "__main__":
    main()
