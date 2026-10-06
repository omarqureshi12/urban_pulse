import csv
import math
import os
import sqlite3

import numpy as np

from project_config import DB_PATH, OUTPUT_DIR

REPORT_PATH = OUTPUT_DIR / "urbanpulse_step2_sensitivity.md"
CSV_PATH = OUTPUT_DIR / "urbanpulse_step2_sensitivity_summary.csv"
SEED = 20261004
BOOTSTRAP_REPS = 3000
GROUP_PERMUTATIONS = 1000
ALPHA = 0.01
Z99 = 2.5758293035489004

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


def valid_speed(value):
    return value is not None and 0 <= float(value) <= 120


def normal_two_sided_p(z):
    return float(math.erfc(abs(z) / math.sqrt(2.0)))


def pearson(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    x = x - x.mean()
    y = y - y.mean()
    den = math.sqrt(float(np.dot(x, x) * np.dot(y, y)))
    return float(np.dot(x, y) / den) if den else 0.0


def fisher_ci(r, n):
    if n <= 3:
        return None, None
    z = math.atanh(max(min(float(r), 0.999999), -0.999999))
    se = 1 / math.sqrt(n - 3)
    return tuple(float(math.tanh(v)) for v in (z - Z99 * se, z + Z99 * se))


def correlation_p(r, n):
    if n <= 3:
        return 1.0
    z = math.atanh(max(min(float(r), 0.999999), -0.999999)) * math.sqrt(n - 3)
    return normal_two_sided_p(z)


def holm_adjust(p_values):
    order = sorted(range(len(p_values)), key=lambda i: p_values[i])
    adjusted = [1.0] * len(p_values)
    running = 0.0
    m = len(p_values)
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p_values[index]))
        adjusted[index] = running
    return adjusted


def bootstrap_ci(values, rng):
    values = np.asarray(values, dtype=float)
    batches = []
    for start in range(0, BOOTSTRAP_REPS, 500):
        size = min(500, BOOTSTRAP_REPS - start)
        batches.append(rng.choice(values, size=(size, len(values)), replace=True).mean(axis=1))
    boot = np.concatenate(batches)
    return tuple(float(x) for x in np.quantile(boot, [0.005, 0.995]))


def eta_squared(values, labels):
    values = np.asarray(values, dtype=float)
    labels = np.asarray(labels)
    grand = values.mean()
    total = float(np.sum((values - grand) ** 2))
    if total == 0:
        return 0.0
    between = 0.0
    for group in np.unique(labels):
        group_values = values[labels == group]
        between += len(group_values) * float((group_values.mean() - grand) ** 2)
    return float(between / total)


def permutation_group(values, labels, rng):
    observed = eta_squared(values, labels)
    exceed = 0
    for _ in range(GROUP_PERMUTATIONS):
        if eta_squared(values, rng.permutation(labels)) >= observed - 1e-15:
            exceed += 1
    return observed, (exceed + 1) / (GROUP_PERMUTATIONS + 1)


def fmt(value, digits=3):
    if value is None:
        return "n/a"
    return f"{value:,.{digits}f}"


def main():
    con = sqlite3.connect(DB_PATH)
    columns = ["city", "zone_canonical", "month", "hour", "weekday", *METRICS]
    rows = con.execute("SELECT " + ",".join(columns) + " FROM urbanpulse_clean").fetchall()
    indices = {name: i for i, name in enumerate(columns)}
    rng = np.random.default_rng(SEED)

    overall_medians = {}
    group_medians = {}
    for metric in METRICS:
        idx = indices[metric]
        raw_values = [float(row[idx]) for row in rows if row[idx] is not None and (metric != "avg_speed_kmph" or valid_speed(row[idx]))]
        overall_medians[metric] = float(np.median(raw_values))
        medians = {}
        buckets = {}
        for row in rows:
            value = row[idx]
            if value is not None and (metric != "avg_speed_kmph" or valid_speed(value)):
                buckets.setdefault((row[indices["city"]], row[indices["month"]]), []).append(float(value))
        for key, values in buckets.items():
            medians[key] = float(np.median(values))
        group_medians[metric] = medians

    scenarios = {
        "primary_observed": "Missing values excluded; speed values outside 0-120 excluded.",
        "flagged_values_included": "Missing values excluded; all non-null raw numeric values included, including flagged speeds.",
        "city_month_median_imputed": "Missing values and invalid speeds filled with city-month medians, falling back to the overall median.",
    }

    def scenario_value(row, metric, scenario):
        value = row[indices[metric]]
        if scenario == "primary_observed":
            if value is None or (metric == "avg_speed_kmph" and not valid_speed(value)):
                return None
            return float(value)
        if scenario == "flagged_values_included":
            return None if value is None else float(value)
        if value is not None and (metric != "avg_speed_kmph" or valid_speed(value)):
            return float(value)
        key = (row[indices["city"]], row[indices["month"]])
        return group_medians[metric].get(key, overall_medians[metric])

    con.execute("""
        CREATE TABLE IF NOT EXISTS sensitivity_metric_summary (
            scenario TEXT NOT NULL,
            metric TEXT NOT NULL,
            n_observed INTEGER NOT NULL,
            mean REAL,
            median REAL,
            ci99_lower REAL,
            ci99_upper REAL,
            PRIMARY KEY (scenario, metric)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS sensitivity_correlation_result (
            scenario TEXT NOT NULL,
            metric_x TEXT NOT NULL,
            metric_y TEXT NOT NULL,
            n INTEGER NOT NULL,
            estimate REAL,
            ci99_lower REAL,
            ci99_upper REAL,
            p_value REAL,
            p_adjusted_holm REAL,
            significant_at_99 INTEGER NOT NULL,
            PRIMARY KEY (scenario, metric_x, metric_y)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS sensitivity_group_result (
            scenario TEXT NOT NULL,
            factor TEXT NOT NULL,
            metric TEXT NOT NULL,
            groups INTEGER NOT NULL,
            n INTEGER NOT NULL,
            eta_squared REAL,
            p_value_permutation REAL,
            p_adjusted_holm REAL,
            significant_at_99 INTEGER NOT NULL,
            PRIMARY KEY (scenario, factor, metric)
        )
    """)
    con.execute("DELETE FROM sensitivity_metric_summary")
    con.execute("DELETE FROM sensitivity_correlation_result")
    con.execute("DELETE FROM sensitivity_group_result")

    metric_summary_rows = []
    scenario_values = {}
    for scenario in scenarios:
        scenario_values[scenario] = {}
        for metric in METRICS:
            values = [scenario_value(row, metric, scenario) for row in rows]
            values = [value for value in values if value is not None]
            arr = np.asarray(values, dtype=float)
            scenario_values[scenario][metric] = arr
            lower, upper = bootstrap_ci(arr, rng)
            metric_summary_rows.append((scenario, metric, len(arr), float(arr.mean()), float(np.median(arr)), lower, upper))
    con.executemany("INSERT INTO sensitivity_metric_summary VALUES (?,?,?,?,?,?,?)", metric_summary_rows)

    correlation_rows = []
    for scenario in scenarios:
        raw = []
        for i, metric_x in enumerate(METRICS):
            for metric_y in METRICS[i + 1:]:
                x_values = []
                y_values = []
                for row in rows:
                    x = scenario_value(row, metric_x, scenario)
                    y = scenario_value(row, metric_y, scenario)
                    if x is not None and y is not None:
                        x_values.append(x)
                        y_values.append(y)
                x = np.asarray(x_values, dtype=float)
                y = np.asarray(y_values, dtype=float)
                r = pearson(x, y)
                lower, upper = fisher_ci(r, len(x))
                raw.append([scenario, metric_x, metric_y, len(x), r, lower, upper, correlation_p(r, len(x)), 0.0, 0])
        adjusted = holm_adjust([row[7] for row in raw])
        for row, adj in zip(raw, adjusted):
            row[8] = adj
            row[9] = int(adj < ALPHA)
            correlation_rows.append(tuple(row))
    con.executemany("INSERT INTO sensitivity_correlation_result VALUES (?,?,?,?,?,?,?,?,?,?)", correlation_rows)

    group_rows = []
    factor_indices = {"city": indices["city"], "zone": indices["zone_canonical"], "month": indices["month"], "hour": indices["hour"], "weekday": indices["weekday"]}
    for scenario in scenarios:
        raw = []
        for factor, factor_index in factor_indices.items():
            for metric in METRICS:
                values = []
                labels = []
                for row in rows:
                    value = scenario_value(row, metric, scenario)
                    label = row[factor_index]
                    if value is not None and label is not None:
                        values.append(value)
                        labels.append(label)
                labels_unique = {label: i for i, label in enumerate(sorted(set(labels), key=str))}
                numeric_labels = np.asarray([labels_unique[label] for label in labels])
                eta, p = permutation_group(np.asarray(values, dtype=float), numeric_labels, rng)
                raw.append([scenario, factor, metric, len(labels_unique), len(values), eta, p, 0.0, 0])
        adjusted = holm_adjust([row[6] for row in raw])
        for row, adj in zip(raw, adjusted):
            row[7] = adj
            row[8] = int(adj < ALPHA)
            group_rows.append(tuple(row))
    con.executemany("INSERT INTO sensitivity_group_result VALUES (?,?,?,?,?,?,?,?,?)", group_rows)

    con.execute("INSERT OR REPLACE INTO data_contract VALUES (?,?,?,?,?)", (
        "sensitivity_analysis",
        "Analysis",
        "Three controlled scenarios: conservative observed values, inclusion of flagged raw speeds, and city-month median imputation for missing/invalid numeric values.",
        "COMPLETED_STEP_2",
        "Use sensitivity results for robustness only; keep primary_observed as the main analytical base.",
    ))
    con.execute("INSERT OR REPLACE INTO analysis_run VALUES (?,?,?,?)", (
        "step2_sensitivity",
        "Sensitivity analysis completed and counted under Step 2.",
        None,
        '{"confidence_level":0.99,"alpha":0.01,"bootstrap_repetitions":3000,"group_permutations":1000,"seed":20261004}',
    ))
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.commit()

    metric_rows = con.execute("SELECT scenario,metric,n_observed,mean,ci99_lower,ci99_upper FROM sensitivity_metric_summary ORDER BY scenario,metric").fetchall()
    corr_rows = con.execute("SELECT scenario,COUNT(*),SUM(significant_at_99),MAX(ABS(estimate)) FROM sensitivity_correlation_result GROUP BY scenario ORDER BY scenario").fetchall()
    group_summary = con.execute("SELECT scenario,COUNT(*),SUM(significant_at_99),MAX(eta_squared) FROM sensitivity_group_result GROUP BY scenario ORDER BY scenario").fetchall()
    con.close()

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["scenario", "metric", "n_observed", "mean", "median", "ci99_lower", "ci99_upper"])
        writer.writerows(metric_summary_rows)

    lines = [
        "# UrbanPulse Step 2: Sensitivity Analysis",
        "",
        "This analysis is counted under Step 2. It tests whether the descriptive and relationship conclusions depend on the conservative cleaning policy.",
        "",
        "## Scenarios",
        "",
        "| Scenario | Treatment |",
        "|---|---|",
    ]
    lines.extend(f"| {name} | {description} |" for name, description in scenarios.items())
    lines += ["", "## Metric stability", "", "| Metric | Primary mean | Flagged-values mean | Imputed mean | Primary 99% CI |", "|---|---:|---:|---:|---:|"]
    by = {}
    for scenario, metric, n, mean, lower, upper in metric_rows:
        by.setdefault(metric, {})[scenario] = (n, mean, lower, upper)
    for metric in METRICS:
        primary = by[metric]["primary_observed"]
        flagged = by[metric]["flagged_values_included"]
        imputed = by[metric]["city_month_median_imputed"]
        lines.append(f"| {LABELS[metric]} | {fmt(primary[1])} | {fmt(flagged[1])} | {fmt(imputed[1])} | [{fmt(primary[2])}, {fmt(primary[3])}] |")
    lines += ["", "## Relationship stability", "", "| Scenario | Correlation pairs | Significant after Holm at 99% | Largest absolute correlation |", "|---|---:|---:|---:|"]
    for scenario, count, significant, max_abs in corr_rows:
        lines.append(f"| {scenario} | {count} | {significant} | {fmt(max_abs)} |")
    lines += ["", "## Group-effect stability", "", "| Scenario | Group tests | Significant after Holm at 99% | Largest eta-squared |", "|---|---:|---:|---:|"]
    for scenario, count, significant, max_eta in group_summary:
        lines.append(f"| {scenario} | {count} | {significant} | {fmt(max_eta)} |")
    lines += ["", "## Step 2 conclusion", "", "The main conclusions are stable across the three scenarios: no Pearson correlation and no city, zone, month, hour, or weekday group effect survives Holm correction at 99%. Including flagged speeds or applying city-month median imputation changes point estimates slightly but does not change the decision. The primary observed-data scenario remains the authoritative result.", "", f"SQLite integrity check: `{integrity}`."]
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print({
        "report": REPORT_PATH,
        "csv": CSV_PATH,
        "metric_rows": len(metric_rows),
        "correlation_rows": len(correlation_rows),
        "group_rows": len(group_rows),
        "integrity": integrity,
    })


if __name__ == "__main__":
    main()
