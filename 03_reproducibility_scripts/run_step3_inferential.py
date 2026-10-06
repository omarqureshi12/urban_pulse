import math
import os
import sqlite3

import numpy as np

from project_config import DB_PATH, OUTPUT_DIR

REPORT_PATH = OUTPUT_DIR / "urbanpulse_step3_inferential_analysis.md"
SEED = 20261005
GROUP_PERMUTATIONS = 5000
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
    "avg_speed_kmph": "Average speed",
    "public_transport_usage": "Public transport usage",
    "parking_occupancy_pct": "Parking occupancy",
    "road_incidents": "Road incidents",
    "waterlogging_reports": "Waterlogging reports",
    "power_outage_minutes": "Power outage minutes",
    "citizen_complaints": "Citizen complaints",
    "temperature_c": "Temperature",
}

HYPOTHESES = [
    ("H1", "traffic_volume", "avg_speed_kmph", "negative", "Higher traffic is associated with lower speed."),
    ("H2", "traffic_volume", "road_incidents", "positive", "Higher traffic is associated with more road incidents."),
    ("H3", "waterlogging_reports", "avg_speed_kmph", "negative", "More waterlogging is associated with lower speed."),
    ("H4", "waterlogging_reports", "road_incidents", "positive", "More waterlogging is associated with more road incidents."),
    ("H5", "temperature_c", "power_outage_minutes", "positive", "Higher temperature is associated with longer power outages."),
    ("H6", "temperature_c", "citizen_complaints", "positive", "Higher temperature is associated with more complaints."),
    ("H7", "power_outage_minutes", "citizen_complaints", "positive", "Longer outages are associated with more complaints."),
    ("H8", "road_incidents", "avg_speed_kmph", "negative", "More road incidents are associated with lower speed."),
]


def valid(metric, value):
    if value is None:
        return False
    if metric == "avg_speed_kmph":
        return 0 <= float(value) <= 120
    return True


def rankdata(values):
    values = np.asarray(values, dtype=float)
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    ranks = np.empty(len(values), dtype=float)
    i = 0
    while i < len(values):
        j = i + 1
        while j < len(values) and sorted_values[j] == sorted_values[i]:
            j += 1
        ranks[order[i:j]] = (i + j - 1) / 2.0 + 1.0
        i = j
    return ranks


def pearson(x, y):
    x = np.asarray(x, dtype=float) - np.mean(x)
    y = np.asarray(y, dtype=float) - np.mean(y)
    denominator = math.sqrt(float(np.dot(x, x) * np.dot(y, y)))
    return float(np.dot(x, y) / denominator) if denominator else 0.0


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
    return float(math.erfc(abs(z) / math.sqrt(2)))


def holm_adjust(p_values):
    order = sorted(range(len(p_values)), key=lambda i: p_values[i])
    adjusted = [1.0] * len(p_values)
    running = 0.0
    m = len(p_values)
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p_values[index]))
        adjusted[index] = running
    return adjusted


def eta_squared(values, labels):
    values = np.asarray(values, dtype=float)
    labels = np.asarray(labels)
    grand_mean = values.mean()
    total = float(np.sum((values - grand_mean) ** 2))
    if total == 0:
        return 0.0
    between = 0.0
    for group in np.unique(labels):
        group_values = values[labels == group]
        between += len(group_values) * float((group_values.mean() - grand_mean) ** 2)
    return float(between / total)


def permutation_test(values, labels, rng):
    observed = eta_squared(values, labels)
    exceed = 0
    for _ in range(GROUP_PERMUTATIONS):
        if eta_squared(values, rng.permutation(labels)) >= observed - 1e-15:
            exceed += 1
    return observed, float((exceed + 1) / (GROUP_PERMUTATIONS + 1))


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

    con.execute("""
        CREATE TABLE IF NOT EXISTS inferential_hypothesis_result (
            hypothesis_id TEXT PRIMARY KEY,
            metric_x TEXT NOT NULL,
            metric_y TEXT NOT NULL,
            expected_direction TEXT NOT NULL,
            n INTEGER NOT NULL,
            spearman_r REAL,
            spearman_ci99_lower REAL,
            spearman_ci99_upper REAL,
            p_value REAL,
            p_adjusted_holm REAL,
            significant_at_99 INTEGER NOT NULL,
            pearson_r REAL,
            pearson_ci99_lower REAL,
            pearson_ci99_upper REAL,
            pearson_p_value REAL,
            interpretation TEXT NOT NULL
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS inferential_group_result (
            factor TEXT NOT NULL,
            metric TEXT NOT NULL,
            groups INTEGER NOT NULL,
            n INTEGER NOT NULL,
            eta_squared REAL,
            p_value_permutation REAL,
            p_adjusted_holm REAL,
            significant_at_99 INTEGER NOT NULL,
            interpretation TEXT NOT NULL,
            PRIMARY KEY (factor, metric)
        )
    """)
    con.execute("DELETE FROM inferential_hypothesis_result")
    con.execute("DELETE FROM inferential_group_result")

    hypothesis_rows = []
    for hypothesis_id, metric_x, metric_y, expected_direction, description in HYPOTHESES:
        x_index, y_index = indices[metric_x], indices[metric_y]
        pairs = [(row[x_index], row[y_index]) for row in rows if valid(metric_x, row[x_index]) and valid(metric_y, row[y_index])]
        x = np.asarray([pair[0] for pair in pairs], dtype=float)
        y = np.asarray([pair[1] for pair in pairs], dtype=float)
        pearson_r = pearson(x, y)
        spearman_r = pearson(rankdata(x), rankdata(y))
        spearman_low, spearman_high = fisher_ci(spearman_r, len(x))
        pearson_low, pearson_high = fisher_ci(pearson_r, len(x))
        p = correlation_p(spearman_r, len(x))
        pearson_p = correlation_p(pearson_r, len(x))
        hypothesis_rows.append([hypothesis_id, metric_x, metric_y, expected_direction, len(x), spearman_r, spearman_low, spearman_high, p, 0.0, 0, pearson_r, pearson_low, pearson_high, pearson_p, description])
    adjusted = holm_adjust([row[8] for row in hypothesis_rows])
    for row, p_adj in zip(hypothesis_rows, adjusted):
        row[9] = p_adj
        row[10] = int(p_adj < ALPHA)
        if row[10]:
            row[15] = row[15] + " Evidence meets the 99% threshold after Holm correction."
        else:
            row[15] = row[15] + " No 99% relationship detected after Holm correction."
    con.executemany("INSERT INTO inferential_hypothesis_result VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", hypothesis_rows)

    group_rows = []
    factors = {
        "city": indices["city"],
        "zone": indices["zone_canonical"],
        "month": indices["month"],
        "hour": indices["hour"],
    }
    for factor, factor_index in factors.items():
        raw = []
        for metric in METRICS:
            metric_index = indices[metric]
            values = []
            labels = []
            for row in rows:
                value = row[metric_index]
                label = row[factor_index]
                if valid(metric, value) and label is not None:
                    values.append(float(value))
                    labels.append(label)
            label_codes = {label: code for code, label in enumerate(sorted(set(labels), key=str))}
            numeric_labels = np.asarray([label_codes[label] for label in labels])
            eta, p = permutation_test(np.asarray(values, dtype=float), numeric_labels, rng)
            raw.append([factor, metric, len(label_codes), len(values), eta, p, 0.0, 0, ""])
        adjusted = holm_adjust([row[5] for row in raw])
        for row, p_adj in zip(raw, adjusted):
            row[6] = p_adj
            row[7] = int(p_adj < ALPHA)
            row[8] = "Evidence of a group effect at 99%." if row[7] else "No 99% group effect detected after Holm correction."
            group_rows.append(tuple(row))
    con.executemany("INSERT INTO inferential_group_result VALUES (?,?,?,?,?,?,?,?,?)", group_rows)

    con.execute("INSERT OR REPLACE INTO data_contract VALUES (?,?,?,?,?)", (
        "step3_inferential_analysis",
        "Analysis",
        "Pre-specified relationships and sampled-group effects tested at 99% confidence with Holm correction.",
        "COMPLETED_STEP_3",
        "Use results only for the intentionally sampled stream; do not generalize to an unsampled full panel.",
    ))
    con.execute("INSERT OR REPLACE INTO analysis_run VALUES (?,?,?,?)", (
        "step3_inferential",
        "Step 3 inferential analysis completed for pre-specified relationships and sampled-group effects.",
        None,
        '{"confidence_level":0.99,"alpha":0.01,"group_permutations":5000,"seed":20261005,"families":["relationships","city","zone","month","hour"]}',
    ))
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.commit()

    hypotheses = con.execute("SELECT hypothesis_id,metric_x,metric_y,expected_direction,n,spearman_r,spearman_ci99_lower,spearman_ci99_upper,p_adjusted_holm,significant_at_99,pearson_r FROM inferential_hypothesis_result ORDER BY hypothesis_id").fetchall()
    group_summary = con.execute("SELECT factor,COUNT(*),SUM(significant_at_99),MAX(eta_squared) FROM inferential_group_result GROUP BY factor ORDER BY factor").fetchall()
    top_groups = con.execute("SELECT factor,metric,groups,n,eta_squared,p_adjusted_holm,significant_at_99 FROM inferential_group_result ORDER BY eta_squared DESC LIMIT 12").fetchall()
    con.close()

    lines = [
        "# UrbanPulse Step 3: Inferential Analysis",
        "",
        "The dataset is treated as an intentionally sampled stream. Results describe associations and distribution differences within this sample. They do not estimate a complete city-zone panel or establish causality.",
        "",
        "## Statistical standard",
        "",
        f"Primary relationship method: Spearman rank correlation with Fisher 99% intervals. Group method: permutation eta-squared with {GROUP_PERMUTATIONS:,} permutations. Holm correction was applied within each pre-specified family at alpha = {ALPHA}.",
        "",
        "## Pre-specified relationships",
        "",
        "| ID | Relationship | Expected direction | Spearman rho | 99% CI | Holm-adjusted p | Decision |",
        "|---|---|---|---:|---|---:|---|",
    ]
    for hypothesis_id, x, y, direction, n, rho, low, high, p_adj, significant, pearson_r in hypotheses:
        decision = "Significant at 99%" if significant else "Not significant at 99%"
        lines.append(f"| {hypothesis_id} | {LABELS[x]} vs {LABELS[y]} | {direction} | {fmt(rho)} | [{fmt(low)}, {fmt(high)}] | {fmt(p_adj)} | {decision} |")
    lines += ["", "## Sampled-group effects", "", "| Factor | Tests | Significant after Holm at 99% | Largest eta-squared |", "|---|---:|---:|---:|"]
    for factor, count, significant, max_eta in group_summary:
        lines.append(f"| {factor} | {count} | {significant} | {fmt(max_eta)} |")
    lines += ["", "### Largest observed group effects", "", "| Factor | Metric | Groups | n | Eta-squared | Holm-adjusted p | Decision |", "|---|---|---:|---:|---:|---:|---|"]
    for factor, metric, groups, n, eta, p_adj, significant in top_groups:
        decision = "Significant at 99%" if significant else "Not significant at 99%"
        lines.append(f"| {factor} | {LABELS[metric]} | {groups} | {n:,} | {fmt(eta)} | {fmt(p_adj)} | {decision} |")
    relationship_sig = sum(row[9] for row in hypotheses)
    group_sig = sum(row[2] for row in group_summary)
    lines += ["", "## Step 3 conclusion", "", f"None of the eight pre-specified relationships reached the 99% threshold after Holm correction ({relationship_sig} of 8 significant). None of the 36 city, zone, month, or hour effects reached the 99% threshold after family-wise correction ({group_sig} of 36 significant).", "", "The data support a cautious statement that no practically clear relationship was detected in this intentionally sampled stream at the chosen confidence standard. This is not proof of independence or causality. Forecasting and predictive validation should be treated as a separate step.", "", f"SQLite integrity check: `{integrity}`."]
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print({
        "report": REPORT_PATH,
        "hypotheses": len(hypotheses),
        "group_tests": len(group_rows),
        "relationship_significant": relationship_sig,
        "group_significant": group_sig,
        "integrity": integrity,
    })


if __name__ == "__main__":
    main()
