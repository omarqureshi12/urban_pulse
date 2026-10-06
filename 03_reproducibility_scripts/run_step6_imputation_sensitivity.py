import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from run_step6_tests import (
    ALPHA,
    GROUP_PERMUTATIONS,
    LABELS,
    METRICS,
    PREDICTIVE_IMPROVEMENT_THRESHOLD,
    PREDICTIVE_R2_THRESHOLD,
    SEED,
    baseline_predict,
    build_features,
    correlation_p,
    eta_squared,
    fisher_ci,
    holm_adjust,
    mae,
    pearson,
    permutation_test,
    rankdata,
    ridge_predict,
    r_squared,
)

from project_config import DB_PATH, OUTPUT_DIR

REPORT_PATH = OUTPUT_DIR / "urbanpulse_step6_imputation_sensitivity.md"
REL_CSV_PATH = OUTPUT_DIR / "urbanpulse_step6_imputed_relationship_results.csv"
GROUP_CSV_PATH = OUTPUT_DIR / "urbanpulse_step6_imputed_group_results.csv"
PRED_CSV_PATH = OUTPUT_DIR / "urbanpulse_step6_imputed_predictive_results.csv"


def main():
    evaluated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    raw = con.execute(
        "SELECT record_id, source_row_number, imputed_city AS city, imputed_zone AS zone, month, hour, weekday, imputed_traffic_volume AS traffic_volume, imputed_avg_speed_kmph AS avg_speed_kmph, imputed_public_transport_usage AS public_transport_usage, imputed_parking_occupancy_pct AS parking_occupancy_pct, imputed_road_incidents AS road_incidents, imputed_waterlogging_reports AS waterlogging_reports, imputed_power_outage_minutes AS power_outage_minutes, imputed_citizen_complaints AS citizen_complaints, imputed_temperature_c AS temperature_c FROM canonical_imputed_sensitivity ORDER BY imputed_timestamp_iso"
    ).fetchall()
    rows = [dict(row) for row in raw]
    probable_temp_ids = {row["record_id"] for row in con.execute("SELECT record_id FROM temperature_neighbor_validation WHERE final_decision='probable_error'").fetchall()}

    def valid(metric, row):
        if row[metric] is None:
            return False
        if metric == "avg_speed_kmph" and not (0 <= float(row[metric]) <= 120):
            return False
        if metric == "temperature_c" and row["record_id"] in probable_temp_ids:
            return False
        return True

    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS step6_sensitivity_relationship_result (
            hypothesis_id TEXT PRIMARY KEY, metric_x TEXT NOT NULL, metric_y TEXT NOT NULL, expected_direction TEXT NOT NULL,
            n INTEGER NOT NULL, spearman_r REAL NOT NULL, ci99_lower REAL, ci99_upper REAL, p_value REAL NOT NULL,
            p_adjusted_holm REAL NOT NULL, practical_threshold_met INTEGER NOT NULL, statistically_significant INTEGER NOT NULL,
            supported_by_both_gates INTEGER NOT NULL, interpretation TEXT NOT NULL, evaluated_at_utc TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS step6_sensitivity_group_result (
            hypothesis_id TEXT NOT NULL, factor TEXT NOT NULL, metric TEXT NOT NULL, groups INTEGER NOT NULL, n INTEGER NOT NULL,
            eta_squared REAL NOT NULL, p_value_permutation REAL NOT NULL, p_adjusted_holm REAL NOT NULL, practical_threshold_met INTEGER NOT NULL,
            statistically_significant INTEGER NOT NULL, supported_by_both_gates INTEGER NOT NULL, interpretation TEXT NOT NULL, evaluated_at_utc TEXT NOT NULL,
            PRIMARY KEY (factor, metric)
        );
        CREATE TABLE IF NOT EXISTS step6_sensitivity_predictive_result (
            metric TEXT PRIMARY KEY, folds INTEGER NOT NULL, useful_folds INTEGER NOT NULL, mean_baseline_mae REAL, mean_model_mae REAL,
            mean_mae_improvement REAL, mean_model_r2 REAL, supported_by_both_gates INTEGER NOT NULL, fold_details_json TEXT NOT NULL,
            interpretation TEXT NOT NULL, evaluated_at_utc TEXT NOT NULL
        );
        """
    )
    con.execute("DELETE FROM step6_sensitivity_relationship_result")
    con.execute("DELETE FROM step6_sensitivity_group_result")
    con.execute("DELETE FROM step6_sensitivity_predictive_result")
    rng = np.random.default_rng(SEED + 1)

    relationship_specs = [("H1", "traffic_volume", "avg_speed_kmph", "negative"), ("H2", "road_incidents", "waterlogging_reports", "positive"), ("H3", "temperature_c", "power_outage_minutes", "positive")]
    rel_rows = []
    for h_id, x_name, y_name, expected in relationship_specs:
        pairs = [(float(row[x_name]), float(row[y_name])) for row in rows if valid(x_name, row) and valid(y_name, row)]
        x = np.asarray([p[0] for p in pairs], dtype=float)
        y = np.asarray([p[1] for p in pairs], dtype=float)
        rho = pearson(rankdata(x), rankdata(y))
        low, high = fisher_ci(rho, len(x))
        p = correlation_p(rho, len(x))
        direction_ok = rho < 0 if expected == "negative" else rho > 0
        practical = int(abs(rho) >= 0.20 and direction_ok)
        rel_rows.append([h_id, x_name, y_name, expected, len(x), rho, low, high, p, 0.0, practical, 0, 0, "", evaluated_at])
    for row, p_adj in zip(rel_rows, holm_adjust([row[8] for row in rel_rows])):
        row[9] = p_adj
        row[11] = int(p_adj < ALPHA)
        row[12] = int(row[10] and row[11])
        row[13] = "Meets both gates." if row[12] else "Does not meet both gates."
    con.executemany("INSERT INTO step6_sensitivity_relationship_result VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rel_rows)

    group_rows = []
    for factor, hypothesis_id, unknown in [("city", "H4_city", None), ("zone", "H4_zone", "[UNKNOWN]")]:
        raw_group = []
        for metric in METRICS:
            values, labels = [], []
            for row in rows:
                if unknown is not None and row[factor] == unknown:
                    continue
                if valid(metric, row):
                    values.append(float(row[metric]))
                    labels.append(row[factor])
            label_codes = {label: code for code, label in enumerate(sorted(set(labels), key=str))}
            eta, p = permutation_test(np.asarray(values), np.asarray([label_codes[label] for label in labels]), rng)
            raw_group.append([hypothesis_id, factor, metric, len(label_codes), len(values), eta, p, 0.0, int(eta >= 0.06), 0, 0, "", evaluated_at])
        for row, p_adj in zip(raw_group, holm_adjust([row[6] for row in raw_group])):
            row[7] = p_adj
            row[9] = int(p_adj < ALPHA)
            row[10] = int(row[8] and row[9])
            row[11] = "Meets both gates." if row[10] else "Does not meet both gates."
            group_rows.append(tuple(row))
    con.executemany("INSERT INTO step6_sensitivity_group_result VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", group_rows)

    pred_rows = []
    for metric in METRICS:
        target_rows = [row for row in rows if valid(metric, row)]
        n = len(target_rows)
        vocab = (sorted(set(row["city"] for row in target_rows), key=str), sorted(set(row["zone"] for row in target_rows), key=str), sorted(set(row["month"] for row in target_rows)), sorted(set(row["hour"] for row in target_rows)), sorted(set(row["weekday"] for row in target_rows)))
        details = []
        for fold, (train_frac, test_frac) in enumerate(((0.50, 0.60), (0.60, 0.70), (0.70, 0.80)), start=1):
            train_end = max(10, int(n * train_frac))
            test_end = max(train_end + 2, int(n * test_frac))
            train_rows, test_rows = target_rows[:train_end], target_rows[train_end:test_end]
            actual = np.asarray([float(row[metric]) for row in test_rows])
            base = baseline_predict(train_rows, test_rows, metric)
            model = ridge_predict(train_rows, test_rows, metric, vocab)
            base_mae, model_mae = mae(actual, base), mae(actual, model)
            improvement = (base_mae - model_mae) / base_mae if base_mae else 0.0
            model_r2 = r_squared(actual, model)
            useful = int(improvement >= PREDICTIVE_IMPROVEMENT_THRESHOLD and model_r2 >= PREDICTIVE_R2_THRESHOLD)
            details.append({"fold": fold, "train_n": len(train_rows), "test_n": len(test_rows), "baseline_mae": base_mae, "model_mae": model_mae, "mae_improvement": improvement, "model_r2": model_r2, "useful": useful})
        useful_folds = sum(d["useful"] for d in details)
        support = int(useful_folds >= 2)
        pred_rows.append((metric, 3, useful_folds, float(np.mean([d["baseline_mae"] for d in details])), float(np.mean([d["model_mae"] for d in details])), float(np.mean([d["mae_improvement"] for d in details])), float(np.mean([d["model_r2"] for d in details])), support, json.dumps(details), "Meets the temporal performance gate." if support else "Does not meet the temporal performance gate.", evaluated_at))
    con.executemany("INSERT INTO step6_sensitivity_predictive_result VALUES (?,?,?,?,?,?,?,?,?,?,?)", pred_rows)

    rel_supported = sum(row[12] for row in rel_rows)
    group_supported = sum(row[10] for row in group_rows)
    pred_supported = sum(row[7] for row in pred_rows)
    con.execute("INSERT OR REPLACE INTO analysis_run VALUES (?,?,?,?)", (
        "step6_imputation_sensitivity",
        "Step 6 imputation sensitivity testing completed after primary observed-value testing.",
        None,
        json.dumps({"relationship_supported": rel_supported, "group_supported": group_supported, "predictive_supported": pred_supported, "imputation_used": True}),
    ))
    con.execute("UPDATE analysis_run SET value_text=?, details_json=? WHERE run_key='step6_hypothesis_protocol'", (
        "Step 6 hypotheses predefined and tested on primary observed values, with imputation sensitivity completed separately.",
        json.dumps({"alpha": ALPHA, "holm_correction": True, "testing_started": True, "primary_completed": True, "sensitivity_completed": True}),
    ))
    con.execute("UPDATE data_contract SET current_status='COMPLETED_STEP_6_PRIMARY_AND_SENSITIVITY', action_required='Primary tests use observed values. Imputation sensitivity results are separate and do not replace primary conclusions.' WHERE contract_key='step6_hypothesis_protocol'")
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.commit()
    con.close()

    with REL_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f); writer.writerow(["hypothesis_id", "metric_x", "metric_y", "expected_direction", "n", "spearman_r", "ci99_lower", "ci99_upper", "p_value", "p_adjusted_holm", "practical_threshold_met", "statistically_significant", "supported_by_both_gates"]); writer.writerows([row[:13] for row in rel_rows])
    with GROUP_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f); writer.writerow(["hypothesis_id", "factor", "metric", "groups", "n", "eta_squared", "p_value_permutation", "p_adjusted_holm", "practical_threshold_met", "statistically_significant", "supported_by_both_gates"]); writer.writerows([row[:11] for row in group_rows])
    with PRED_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f); writer.writerow(["metric", "folds", "useful_folds", "mean_baseline_mae", "mean_model_mae", "mean_mae_improvement", "mean_model_r2", "supported_by_both_gates"]); writer.writerows([row[:8] for row in pred_rows])

    lines = [
        "# UrbanPulse Step 6: Imputation Sensitivity Results",
        "",
        "This is a sensitivity analysis using the Step 5A imputed layer. It does not replace the primary observed-value results.",
        "",
        "| Test family | Supported primary hypotheses | Supported imputed hypotheses |",
        "|---|---:|---:|",
        f"| Relationships | see primary report | {rel_supported} of {len(rel_rows)} |",
        f"| City/zone differences | see primary report | {group_supported} of {len(group_rows)} |",
        f"| Temporal prediction | see primary report | {pred_supported} of {len(pred_rows)} |",
        "",
        "The imputation sensitivity results do not alter the primary conclusion if they agree with the observed-value results. Any difference is reported as sensitivity, not substituted into the primary analysis.",
        "",
        f"SQLite integrity check: `{integrity}`.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(REPORT_PATH), "relationship_supported": rel_supported, "group_supported": group_supported, "predictive_supported": pred_supported, "integrity": integrity}, indent=2))


if __name__ == "__main__":
    main()
