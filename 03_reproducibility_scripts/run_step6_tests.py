import csv
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from project_config import DB_PATH, OUTPUT_DIR

REPORT_PATH = OUTPUT_DIR / "urbanpulse_step6_testing_results.md"
REL_CSV_PATH = OUTPUT_DIR / "urbanpulse_step6_relationship_results.csv"
GROUP_CSV_PATH = OUTPUT_DIR / "urbanpulse_step6_group_results.csv"
PRED_CSV_PATH = OUTPUT_DIR / "urbanpulse_step6_predictive_results.csv"

ALPHA = 0.01
Z99 = 2.5758293035489004
GROUP_PERMUTATIONS = 5000
SEED = 20261006
PREDICTIVE_IMPROVEMENT_THRESHOLD = 0.10
PREDICTIVE_R2_THRESHOLD = 0.10

METRICS = [
    "traffic_volume", "avg_speed_kmph", "public_transport_usage", "parking_occupancy_pct",
    "road_incidents", "waterlogging_reports", "power_outage_minutes", "citizen_complaints", "temperature_c",
]
LABELS = {
    "traffic_volume": "Traffic volume", "avg_speed_kmph": "Average speed", "public_transport_usage": "Public transport usage",
    "parking_occupancy_pct": "Parking occupancy", "road_incidents": "Road incidents", "waterlogging_reports": "Waterlogging reports",
    "power_outage_minutes": "Power outage minutes", "citizen_complaints": "Citizen complaints", "temperature_c": "Temperature",
}


def valid(metric, row, probable_temp_ids):
    value = row[metric]
    if value is None:
        return False
    if metric == "avg_speed_kmph" and not (0 <= float(value) <= 120):
        return False
    if metric == "temperature_c" and row["record_id"] in probable_temp_ids:
        return False
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


def build_features(rows, vocab):
    city_levels, zone_levels, month_levels, hour_levels, weekday_levels = vocab
    features = []
    for row in rows:
        vector = [1.0]
        vector.extend(1.0 if row["city"] == level else 0.0 for level in city_levels[1:])
        vector.extend(1.0 if row["zone"] == level else 0.0 for level in zone_levels[1:])
        vector.extend(1.0 if row["month"] == level else 0.0 for level in month_levels[1:])
        vector.extend(1.0 if row["hour"] == level else 0.0 for level in hour_levels[1:])
        vector.extend(1.0 if row["weekday"] == level else 0.0 for level in weekday_levels[1:])
        features.append(vector)
    return np.asarray(features, dtype=float)


def ridge_predict(train_rows, test_rows, metric, vocab):
    x_train = build_features(train_rows, vocab)
    x_test = build_features(test_rows, vocab)
    y_train = np.asarray([float(row[metric]) for row in train_rows], dtype=float)
    regularization = np.eye(x_train.shape[1]) * 1.0
    regularization[0, 0] = 0.0
    try:
        beta = np.linalg.solve(x_train.T @ x_train + regularization, x_train.T @ y_train)
    except np.linalg.LinAlgError:
        beta = np.linalg.lstsq(x_train, y_train, rcond=None)[0]
    return x_test @ beta


def baseline_predict(train_rows, test_rows, metric):
    by_city_month = {}
    by_city = {}
    all_values = []
    for row in train_rows:
        value = float(row[metric])
        by_city_month.setdefault((row["city"], row["month"]), []).append(value)
        by_city.setdefault(row["city"], []).append(value)
        all_values.append(value)
    medians_cm = {key: float(np.median(values)) for key, values in by_city_month.items()}
    medians_city = {key: float(np.median(values)) for key, values in by_city.items()}
    overall = float(np.median(all_values))
    return np.asarray([medians_cm.get((row["city"], row["month"]), medians_city.get(row["city"], overall)) for row in test_rows], dtype=float)


def mae(actual, predicted):
    return float(np.mean(np.abs(np.asarray(actual) - np.asarray(predicted))))


def r_squared(actual, predicted):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    total = float(np.sum((actual - np.mean(actual)) ** 2))
    return float(1 - np.sum((actual - predicted) ** 2) / total) if total else 0.0


def main():
    evaluated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = [dict(row) for row in con.execute(
        "SELECT record_id, source_row_number, cleaned_city AS city, COALESCE(cleaned_zone,'[UNKNOWN]') AS zone, month, hour, weekday, cleaned_timestamp_iso AS timestamp, observation_date, " + ",".join("cleaned_" + metric + " AS " + metric for metric in METRICS) + " FROM canonical_cleaned ORDER BY cleaned_timestamp_iso"
    ).fetchall()]
    probable_temp_ids = {row["record_id"] for row in con.execute("SELECT record_id FROM temperature_neighbor_validation WHERE final_decision='probable_error'").fetchall()}
    rng = np.random.default_rng(SEED)

    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS step6_relationship_result (
            hypothesis_id TEXT PRIMARY KEY,
            metric_x TEXT NOT NULL,
            metric_y TEXT NOT NULL,
            expected_direction TEXT NOT NULL,
            n INTEGER NOT NULL,
            spearman_r REAL NOT NULL,
            ci99_lower REAL,
            ci99_upper REAL,
            p_value REAL NOT NULL,
            p_adjusted_holm REAL NOT NULL,
            practical_threshold_met INTEGER NOT NULL,
            statistically_significant INTEGER NOT NULL,
            supported_by_both_gates INTEGER NOT NULL,
            interpretation TEXT NOT NULL,
            evaluated_at_utc TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS step6_group_result (
            hypothesis_id TEXT NOT NULL,
            factor TEXT NOT NULL,
            metric TEXT NOT NULL,
            groups INTEGER NOT NULL,
            n INTEGER NOT NULL,
            eta_squared REAL NOT NULL,
            p_value_permutation REAL NOT NULL,
            p_adjusted_holm REAL NOT NULL,
            practical_threshold_met INTEGER NOT NULL,
            statistically_significant INTEGER NOT NULL,
            supported_by_both_gates INTEGER NOT NULL,
            interpretation TEXT NOT NULL,
            evaluated_at_utc TEXT NOT NULL,
            PRIMARY KEY (factor, metric)
        );
        CREATE TABLE IF NOT EXISTS step6_predictive_result (
            metric TEXT PRIMARY KEY,
            folds INTEGER NOT NULL,
            useful_folds INTEGER NOT NULL,
            mean_baseline_mae REAL,
            mean_model_mae REAL,
            mean_mae_improvement REAL,
            mean_model_r2 REAL,
            supported_by_both_gates INTEGER NOT NULL,
            fold_details_json TEXT NOT NULL,
            interpretation TEXT NOT NULL,
            evaluated_at_utc TEXT NOT NULL
        );
        """
    )
    con.execute("DELETE FROM step6_relationship_result")
    con.execute("DELETE FROM step6_group_result")
    con.execute("DELETE FROM step6_predictive_result")

    # H1-H3: relationship family.
    relationship_specs = [
        ("H1", "traffic_volume", "avg_speed_kmph", "negative"),
        ("H2", "road_incidents", "waterlogging_reports", "positive"),
        ("H3", "temperature_c", "power_outage_minutes", "positive"),
    ]
    relationship_rows = []
    for hypothesis_id, x_name, y_name, expected in relationship_specs:
        pairs = [(float(row[x_name]), float(row[y_name])) for row in rows if valid(x_name, row, probable_temp_ids) and valid(y_name, row, probable_temp_ids)]
        x = np.asarray([pair[0] for pair in pairs], dtype=float)
        y = np.asarray([pair[1] for pair in pairs], dtype=float)
        rho = pearson(rankdata(x), rankdata(y))
        low, high = fisher_ci(rho, len(x))
        p = correlation_p(rho, len(x))
        direction_ok = (rho < 0 if expected == "negative" else rho > 0)
        practical = int(abs(rho) >= 0.20 and direction_ok)
        relationship_rows.append([hypothesis_id, x_name, y_name, expected, len(x), rho, low, high, p, 0.0, practical, 0, 0, "", evaluated_at])
    adjusted = holm_adjust([row[8] for row in relationship_rows])
    for row, p_adj in zip(relationship_rows, adjusted):
        row[9] = p_adj
        row[11] = int(p_adj < ALPHA)
        row[12] = int(row[10] and row[11])
        row[13] = "Meets both the practical and statistical gates." if row[12] else "Does not meet both the practical and statistical gates."
    con.executemany("INSERT INTO step6_relationship_result VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", relationship_rows)

    # H4_city and H4_zone: all nine descriptive metrics, with invalid/unknown values excluded per field.
    group_rows = []
    for factor, hypothesis_id, allowed_label in [("city", "H4_city", None), ("zone", "H4_zone", "[UNKNOWN]")]:
        raw = []
        for metric in METRICS:
            values, labels = [], []
            for row in rows:
                if allowed_label is not None and row[factor] == allowed_label:
                    continue
                if valid(metric, row, probable_temp_ids) and row[factor] is not None:
                    values.append(float(row[metric]))
                    labels.append(row[factor])
            label_codes = {label: code for code, label in enumerate(sorted(set(labels), key=str))}
            numeric_labels = np.asarray([label_codes[label] for label in labels])
            eta, p = permutation_test(np.asarray(values, dtype=float), numeric_labels, rng)
            raw.append([hypothesis_id, factor, metric, len(label_codes), len(values), eta, p, 0.0, int(eta >= 0.06), 0, 0, "", evaluated_at])
        adjusted = holm_adjust([row[6] for row in raw])
        for row, p_adj in zip(raw, adjusted):
            row[7] = p_adj
            row[9] = int(p_adj < ALPHA)
            row[10] = int(row[8] and row[9])
            row[11] = "Meets both the practical and statistical gates." if row[10] else "Does not meet both the practical and statistical gates."
            group_rows.append(tuple(row))
    con.executemany("INSERT INTO step6_group_result VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", group_rows)

    # H5: three chronological holdouts for each metric.
    predictive_rows = []
    for metric in METRICS:
        target_rows = [row for row in rows if valid(metric, row, probable_temp_ids)]
        n = len(target_rows)
        vocab = (
            sorted(set(row["city"] for row in target_rows), key=str),
            sorted(set(row["zone"] for row in target_rows), key=str),
            sorted(set(row["month"] for row in target_rows)),
            sorted(set(row["hour"] for row in target_rows)),
            sorted(set(row["weekday"] for row in target_rows)),
        )
        fold_details = []
        for fold_number, (train_end_fraction, test_end_fraction) in enumerate(((0.50, 0.60), (0.60, 0.70), (0.70, 0.80)), start=1):
            train_end = max(10, int(n * train_end_fraction))
            test_end = max(train_end + 2, int(n * test_end_fraction))
            train_rows = target_rows[:train_end]
            test_rows = target_rows[train_end:test_end]
            actual = np.asarray([float(row[metric]) for row in test_rows], dtype=float)
            baseline = baseline_predict(train_rows, test_rows, metric)
            prediction = ridge_predict(train_rows, test_rows, metric, vocab)
            baseline_mae = mae(actual, baseline)
            model_mae = mae(actual, prediction)
            improvement = (baseline_mae - model_mae) / baseline_mae if baseline_mae else 0.0
            model_r2 = r_squared(actual, prediction)
            useful = int(improvement >= PREDICTIVE_IMPROVEMENT_THRESHOLD and model_r2 >= PREDICTIVE_R2_THRESHOLD)
            fold_details.append({"fold": fold_number, "train_n": len(train_rows), "test_n": len(test_rows), "baseline_mae": baseline_mae, "model_mae": model_mae, "mae_improvement": improvement, "model_r2": model_r2, "useful": useful})
        useful_folds = sum(detail["useful"] for detail in fold_details)
        support = int(useful_folds >= 2)
        predictive_rows.append((metric, len(fold_details), useful_folds, float(np.mean([d["baseline_mae"] for d in fold_details])), float(np.mean([d["model_mae"] for d in fold_details])), float(np.mean([d["mae_improvement"] for d in fold_details])), float(np.mean([d["model_r2"] for d in fold_details])), support, json.dumps(fold_details), "Meets the temporal performance gate." if support else "Does not meet the temporal performance gate.", evaluated_at))
    con.executemany("INSERT INTO step6_predictive_result VALUES (?,?,?,?,?,?,?,?,?,?,?)", predictive_rows)

    # Lock the tested status without altering the preregistered rules.
    con.execute("UPDATE hypothesis_registry SET status='tested_primary' WHERE hypothesis_id IN ('H1','H2','H3','H4_city','H4_zone','H5')")
    con.execute("INSERT OR REPLACE INTO data_contract VALUES (?,?,?,?,?)", (
        "step6_hypothesis_protocol",
        "Analysis",
        "Step 6 hypotheses and practical thresholds were predefined and then tested on the primary observed layer.",
        "COMPLETED_STEP_6_PRIMARY_TESTING",
        "Run imputed sensitivity tests only as a separate follow-up; do not replace primary results.",
    ))
    relationship_supported = sum(row[12] for row in relationship_rows)
    group_supported = sum(row[10] for row in group_rows)
    predictive_supported = sum(row[7] for row in predictive_rows)
    con.execute("INSERT OR REPLACE INTO analysis_run VALUES (?,?,?,?)", (
        "step6_testing",
        "Step 6 primary hypothesis testing completed with preregistered thresholds.",
        None,
        json.dumps({"alpha": ALPHA, "holm_correction": True, "group_permutations": GROUP_PERMUTATIONS, "relationship_supported": relationship_supported, "group_supported": group_supported, "predictive_supported": predictive_supported, "imputation_used": False}),
    ))
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.commit()
    con.close()

    with REL_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["hypothesis_id", "metric_x", "metric_y", "expected_direction", "n", "spearman_r", "ci99_lower", "ci99_upper", "p_value", "p_adjusted_holm", "practical_threshold_met", "statistically_significant", "supported_by_both_gates"])
        writer.writerows([row[:13] for row in relationship_rows])
    with GROUP_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["hypothesis_id", "factor", "metric", "groups", "n", "eta_squared", "p_value_permutation", "p_adjusted_holm", "practical_threshold_met", "statistically_significant", "supported_by_both_gates"])
        writer.writerows([row[:11] for row in group_rows])
    with PRED_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "folds", "useful_folds", "mean_baseline_mae", "mean_model_mae", "mean_mae_improvement", "mean_model_r2", "supported_by_both_gates"])
        writer.writerows([row[:8] for row in predictive_rows])

    lines = [
        "# UrbanPulse Step 6: Hypothesis Testing Results",
        "",
        "Tests were run after the hypotheses and thresholds were predefined. The primary analysis uses the canonical observed layer only. The Step 5A imputed layer was not used.",
        "",
        f"Statistical standard: alpha = {ALPHA}; Holm correction within each family; group permutations = {GROUP_PERMUTATIONS:,}; seed = {SEED}.",
        "",
        "## Relationship hypotheses",
        "",
        "| ID | Relationship | n | Spearman rho | 99% CI | Holm p | Practical gate | Statistical gate | Final |",
        "|---|---|---:|---:|---|---:|---|---|---|",
    ]
    for row in relationship_rows:
        final = "Supported" if row[12] else "Not supported"
        practical = "Pass" if row[10] else "Fail"
        statistical = "Pass" if row[11] else "Fail"
        lines.append(f"| {row[0]} | {LABELS[row[1]]} vs {LABELS[row[2]]} | {row[4]:,} | {row[5]:.3f} | [{row[6]:.3f}, {row[7]:.3f}] | {row[9]:.3f} | {practical} | {statistical} | {final} |")
    lines += [
        "",
        "## City and zone differences",
        "",
        "Meaningful effect requires eta-squared >= 0.06 and Holm-adjusted p < 0.01.",
        "",
        "| Factor | Tests | Practical passes | Statistical passes | Both gates | Largest eta-squared |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for factor in ("city", "zone"):
        subset = [row for row in group_rows if row[1] == factor]
        largest = max(row[5] for row in subset)
        lines.append(f"| {factor} | {len(subset)} | {sum(row[8] for row in subset)} | {sum(row[9] for row in subset)} | {sum(row[10] for row in subset)} | {largest:.3f} |")
    lines += [
        "",
        "## Temporal predictability",
        "",
        "Useful prediction requires at least 10% MAE improvement over the city-month median baseline and R-squared >= 0.10 in at least 2 of 3 chronological holdouts.",
        "",
        "| Metric | Folds | Useful folds | Mean baseline MAE | Mean model MAE | Mean MAE improvement | Mean model R² | Final |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in predictive_rows:
        lines.append(f"| {LABELS[row[0]]} | {row[1]} | {row[2]} | {row[3]:.3f} | {row[4]:.3f} | {row[5]:.1%} | {row[6]:.3f} | {'Supported' if row[7] else 'Not supported'} |")
    lines += [
        "",
        "## Conclusion",
        "",
        f"Relationship hypotheses supported by both gates: {relationship_supported} of {len(relationship_rows)}.",
        f"City/zone metric tests supported by both gates: {group_supported} of {len(group_rows)}.",
        f"Predictive metric tests supported by the performance gate: {predictive_supported} of {len(predictive_rows)}.",
        "",
        "A non-supported result means the predefined practical and statistical thresholds were not both met. It does not prove that no relationship exists. Results describe the intentionally sampled stream and should not be generalized to an unsampled full city-zone panel.",
        "",
        f"SQLite integrity check: `{integrity}`.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(REPORT_PATH), "relationships": len(relationship_rows), "groups": len(group_rows), "predictive_metrics": len(predictive_rows), "relationship_supported": relationship_supported, "group_supported": group_supported, "predictive_supported": predictive_supported, "integrity": integrity}, indent=2))


if __name__ == "__main__":
    main()
