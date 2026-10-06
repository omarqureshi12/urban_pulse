import csv
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from project_config import DB_PATH, OUTPUT_DIR

REPORT_PATH = OUTPUT_DIR / "urbanpulse_step7_model_results.md"
GROUP_CSV_PATH = OUTPUT_DIR / "urbanpulse_step7_group_effects.csv"
REL_CSV_PATH = OUTPUT_DIR / "urbanpulse_step7_adjusted_relationships.csv"
COUNT_CSV_PATH = OUTPUT_DIR / "urbanpulse_step7_count_models.csv"
FORECAST_CSV_PATH = OUTPUT_DIR / "urbanpulse_step7_forecast_results.csv"

BOOTSTRAP_REPS = 3000
SEED = 20261007
ALPHA = 0.01
HUBER_K = 1.345
FORECAST_FOLDS = ((0.50, 0.60), (0.60, 0.70), (0.70, 0.80))

METRICS = [
    "traffic_volume", "avg_speed_kmph", "public_transport_usage", "parking_occupancy_pct",
    "road_incidents", "waterlogging_reports", "power_outage_minutes", "citizen_complaints", "temperature_c",
]
LABELS = {
    "traffic_volume": "Traffic volume", "avg_speed_kmph": "Average speed", "public_transport_usage": "Public transport usage",
    "parking_occupancy_pct": "Parking occupancy", "road_incidents": "Road incidents", "waterlogging_reports": "Waterlogging reports",
    "power_outage_minutes": "Power outage minutes", "citizen_complaints": "Citizen complaints", "temperature_c": "Temperature",
}
COUNT_METRICS = {"traffic_volume", "public_transport_usage", "road_incidents", "waterlogging_reports", "citizen_complaints"}


def q(value, low=0.005, high=0.995):
    return float(np.quantile(np.asarray(value, dtype=float), [low, high])[0]), float(np.quantile(np.asarray(value, dtype=float), [low, high])[1])


def valid(metric, row, probable_temp_ids):
    value = row.get(metric)
    if value is None:
        return False
    if metric == "avg_speed_kmph" and not (0 <= float(value) <= 120):
        return False
    if metric == "temperature_c" and row["record_id"] in probable_temp_ids:
        return False
    return True


def wls(X, z, weights, ridge=1e-8):
    weights = np.asarray(weights, dtype=float)
    xtw = X.T * weights
    gram = xtw @ X
    scale = max(float(np.trace(gram)) / max(gram.shape[0], 1), 1.0)
    gram = gram + np.eye(gram.shape[0]) * ridge * scale
    try:
        return np.linalg.solve(gram, xtw @ z)
    except np.linalg.LinAlgError:
        return np.linalg.lstsq(gram, xtw @ z, rcond=None)[0]


def fit_huber(X, y, max_iter=40):
    beta = wls(X, y, np.ones(len(y)))
    robust_weights = np.ones(len(y))
    for _ in range(max_iter):
        residual = y - X @ beta
        scale = 1.4826 * np.median(np.abs(residual - np.median(residual)))
        if not np.isfinite(scale) or scale <= 1e-8:
            scale = max(float(np.std(residual)), 1.0)
        u = residual / (HUBER_K * scale)
        robust_weights = np.where(np.abs(u) <= 1, 1.0, 1.0 / np.maximum(np.abs(u), 1e-12))
        new_beta = wls(X, y, robust_weights)
        if np.max(np.abs(new_beta - beta)) < 1e-7:
            beta = new_beta
            break
        beta = new_beta
    return beta, robust_weights, y.copy(), scale


def fit_glm(X, y, family, alpha_nb=0.0, max_iter=60):
    mean_y = max(float(np.mean(y)), 1e-6)
    beta = np.zeros(X.shape[1], dtype=float)
    beta[0] = math.log(mean_y)
    for _ in range(max_iter):
        eta = np.clip(X @ beta, -20, 20)
        mu = np.exp(eta)
        variance = mu if family == "poisson" else mu + alpha_nb * mu * mu
        weights = np.maximum(mu * mu / np.maximum(variance, 1e-10), 1e-10)
        z = eta + (y - mu) / np.maximum(mu, 1e-10)
        new_beta = wls(X, z, weights)
        if np.max(np.abs(new_beta - beta)) < 1e-7:
            beta = new_beta
            break
        beta = new_beta
    eta = np.clip(X @ beta, -20, 20)
    mu = np.exp(eta)
    variance = mu if family == "poisson" else mu + alpha_nb * mu * mu
    weights = np.maximum(mu * mu / np.maximum(variance, 1e-10), 1e-10)
    z = eta + (y - mu) / np.maximum(mu, 1e-10)
    dispersion = float(np.sum((y - mu) ** 2 / np.maximum(mu, 1e-10)) / max(len(y) - X.shape[1], 1))
    return beta, weights, z, dispersion, mu


def design_rows(rows, numeric=None, categories=None):
    numeric = numeric or []
    categories = categories or {}
    out = []
    for row in rows:
        vector = [1.0]
        for name, scale in numeric:
            vector.append(float(row[name]) / scale)
        for name in ("city", "zone", "month", "hour", "weekday"):
            levels = categories.get(name, [])
            for level in levels[1:]:
                vector.append(1.0 if row[name] == level else 0.0)
        out.append(vector)
    return np.asarray(out, dtype=float)


def categories_for(rows):
    return {
        "city": sorted(set(row["city"] for row in rows), key=str),
        "zone": sorted(set(row["zone"] for row in rows), key=str),
        "month": sorted(set(row["month"] for row in rows)),
        "hour": sorted(set(row["hour"] for row in rows)),
        "weekday": sorted(set(row["weekday"] for row in rows)),
    }


def date_block_bootstrap_beta(X, target, dates, working_weights, working_response, rng):
    date_values, date_codes = np.unique(np.asarray(dates), return_inverse=True)
    date_count = len(date_values)
    p = X.shape[1]
    gram_by_date = np.zeros((date_count, p, p), dtype=float)
    rhs_by_date = np.zeros((date_count, p), dtype=float)
    for code in range(date_count):
        mask = date_codes == code
        x_d = X[mask]
        w_d = working_weights[mask]
        z_d = working_response[mask]
        gram_by_date[code] = (x_d.T * w_d) @ x_d
        rhs_by_date[code] = x_d.T @ (w_d * z_d)
    counts = rng.multinomial(date_count, np.full(date_count, 1 / date_count), size=BOOTSTRAP_REPS)
    grams = np.einsum("bd,dij->bij", counts, gram_by_date)
    rhs = np.einsum("bd,di->bi", counts, rhs_by_date)
    scale = np.maximum(np.trace(grams, axis1=1, axis2=2) / max(p, 1), 1.0)
    grams += np.eye(p)[None, :, :] * (1e-8 * scale[:, None, None])
    try:
        return np.linalg.solve(grams, rhs[..., None])[..., 0]
    except np.linalg.LinAlgError:
        return np.asarray([np.linalg.lstsq(grams[i], rhs[i], rcond=None)[0] for i in range(len(rhs))])


def effect_interval(samples):
    return q(samples)


def marginal_group_effects(beta, beta_samples, base_rows, categories, factor, groups, numeric=None, log_link=False):
    numeric = numeric or []
    base_predictions = []
    group_pred_matrices = {}
    group_points = {}
    for group in groups:
        modified = [dict(row, **{factor: group}) for row in base_rows]
        Xg = design_rows(modified, numeric=numeric, categories=categories)
        group_pred_matrices[group] = Xg
        point_predictions = Xg @ beta
        group_points[group] = float(np.mean(np.exp(point_predictions) if log_link else point_predictions))
    counts = {group: sum(1 for row in base_rows if row[factor] == group) for group in groups}
    total_n = sum(counts.values()) or 1
    grand = sum(counts[group] * group_points[group] for group in groups) / total_n
    results = []
    for group in groups:
        point = group_points[group] - grand
        sample_linear = group_pred_matrices[group] @ beta_samples.T
        sample_group = np.mean(np.exp(sample_linear) if log_link else sample_linear, axis=0)
        sample_group_by_group = {}
        for g in groups:
            linear = group_pred_matrices[g] @ beta_samples.T
            sample_group_by_group[g] = np.mean(np.exp(linear) if log_link else linear, axis=0)
        sample_grand = sum(counts[g] * sample_group_by_group[g] for g in groups) / total_n
        low, high = effect_interval(sample_group - sample_grand)
        results.append((group, point, low, high, float(np.std(sample_group - sample_grand))))
    return results


def select_count_family(X, y):
    poisson_beta, poisson_w, poisson_z, dispersion, mu = fit_glm(X, y, "poisson")
    if dispersion <= 1.5:
        return "poisson", 0.0, poisson_beta, poisson_w, poisson_z, dispersion
    variance = float(np.var(y, ddof=1))
    mean_y = max(float(np.mean(y)), 1e-8)
    alpha_nb = max((variance - mean_y) / (mean_y * mean_y), 1e-6)
    beta, weights, z, nb_dispersion, _ = fit_glm(X, y, "negative_binomial", alpha_nb=alpha_nb)
    return "negative_binomial", alpha_nb, beta, weights, z, dispersion


def fit_model(rows, target, numeric=None, count=False):
    cats = categories_for(rows)
    X = design_rows(rows, numeric=numeric, categories=cats)
    y = np.asarray([float(row[target]) for row in rows], dtype=float)
    if count:
        family, alpha_nb, beta, weights, z, dispersion = select_count_family(X, y)
        return {"X": X, "y": y, "categories": cats, "beta": beta, "weights": weights, "z": z, "family": family, "alpha_nb": alpha_nb, "dispersion": dispersion, "scale": None}
    beta, weights, z, scale = fit_huber(X, y)
    return {"X": X, "y": y, "categories": cats, "beta": beta, "weights": weights, "z": z, "family": "huber", "alpha_nb": None, "dispersion": None, "scale": scale}


def bootstrap_model(model, rows, numeric=None, rng=None):
    rng = rng or np.random.default_rng(SEED)
    return date_block_bootstrap_beta(model["X"], model["y"], [row["observation_date"] for row in rows], model["weights"], model["z"], rng)


def add_lag(rows, metric):
    prior = {}
    output = []
    for row in rows:
        copy = dict(row)
        copy["lag_value"] = prior.get(row["city"])
        if valid_value(row.get(metric), metric):
            prior[row["city"]] = float(row[metric])
        output.append(copy)
    return output


def valid_value(value, metric):
    if value is None:
        return False
    if metric == "avg_speed_kmph" and not (0 <= float(value) <= 120):
        return False
    return True


def forecast_features(rows, categories, metric_scale):
    return design_rows(rows, numeric=[("lag_value", metric_scale)], categories=categories)


def forecast_bootstrap(test_rows, actual, baseline, model_prediction, rng):
    dates = np.asarray([row["observation_date"] for row in test_rows])
    unique_dates, codes = np.unique(dates, return_inverse=True)
    n_dates = len(unique_dates)
    n_by_date = np.bincount(codes, minlength=n_dates)
    abs_base = np.bincount(codes, weights=np.abs(actual - baseline), minlength=n_dates)
    abs_model = np.bincount(codes, weights=np.abs(actual - model_prediction), minlength=n_dates)
    sq_base = np.bincount(codes, weights=(actual - baseline) ** 2, minlength=n_dates)
    sq_model = np.bincount(codes, weights=(actual - model_prediction) ** 2, minlength=n_dates)
    sum_y = np.bincount(codes, weights=actual, minlength=n_dates)
    sum_y2 = np.bincount(codes, weights=actual * actual, minlength=n_dates)
    counts = rng.multinomial(n_dates, np.full(n_dates, 1 / n_dates), size=BOOTSTRAP_REPS)
    n = counts @ n_by_date
    base_mae = (counts @ abs_base) / n
    model_mae = (counts @ abs_model) / n
    improvement = (base_mae - model_mae) / np.maximum(base_mae, 1e-12)
    model_sse = counts @ sq_model
    yy = counts @ sum_y
    yy2 = counts @ sum_y2
    sst = yy2 - (yy * yy) / np.maximum(n, 1)
    model_r2 = 1 - model_sse / np.maximum(sst, 1e-12)
    return {
        "baseline_mae_ci": effect_interval(base_mae),
        "model_mae_ci": effect_interval(model_mae),
        "improvement_ci": effect_interval(improvement),
        "r2_ci": effect_interval(model_r2),
    }


def main():
    evaluated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = [dict(row) for row in con.execute(
        "SELECT record_id, source_row_number, cleaned_city AS city, COALESCE(cleaned_zone,'[UNKNOWN]') AS zone, month, hour, weekday, observation_date, cleaned_timestamp_iso AS timestamp, " + ",".join("cleaned_" + metric + " AS " + metric for metric in METRICS) + " FROM canonical_cleaned ORDER BY cleaned_timestamp_iso"
    ).fetchall()]
    probable_temp_ids = {row["record_id"] for row in con.execute("SELECT record_id FROM temperature_neighbor_validation WHERE final_decision='probable_error'").fetchall()}
    rng = np.random.default_rng(SEED)

    con.executescript(
        """
        DROP TABLE IF EXISTS step7_group_effect;
        DROP TABLE IF EXISTS step7_relationship_effect;
        DROP TABLE IF EXISTS step7_count_model;
        DROP TABLE IF EXISTS step7_forecast_result;
        """
    )
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS step7_group_effect (
            model_id TEXT NOT NULL, factor TEXT NOT NULL, target_metric TEXT NOT NULL, group_value TEXT NOT NULL,
            n INTEGER NOT NULL, model_family TEXT NOT NULL, effect_native REAL NOT NULL, ci99_lower REAL NOT NULL,
            ci99_upper REAL NOT NULL, effect_standardized REAL, dispersion_ratio REAL, practical_effect_threshold TEXT NOT NULL,
            evaluated_at_utc TEXT NOT NULL, PRIMARY KEY (model_id, factor, target_metric, group_value)
        );
        CREATE TABLE IF NOT EXISTS step7_relationship_effect (
            model_id TEXT PRIMARY KEY, target_metric TEXT NOT NULL, predictor_metric TEXT NOT NULL, model_family TEXT NOT NULL,
            n INTEGER NOT NULL, effect_native REAL NOT NULL, ci99_lower REAL NOT NULL, ci99_upper REAL NOT NULL,
            effect_standardized REAL, rate_ratio REAL, rate_ratio_ci99_lower REAL, rate_ratio_ci99_upper REAL,
            dispersion_ratio REAL, evaluated_at_utc TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS step7_count_model (
            model_id TEXT NOT NULL, target_metric TEXT NOT NULL, n INTEGER NOT NULL, selected_family TEXT NOT NULL,
            dispersion_ratio REAL NOT NULL, nb_alpha REAL, mean_count REAL, effect_summary TEXT NOT NULL,
            evaluated_at_utc TEXT NOT NULL, PRIMARY KEY (model_id, target_metric)
        );
        CREATE TABLE IF NOT EXISTS step7_forecast_result (
            metric TEXT NOT NULL, fold INTEGER NOT NULL, model_family TEXT NOT NULL, train_n INTEGER NOT NULL, test_n INTEGER NOT NULL,
            baseline_mae REAL NOT NULL, model_mae REAL NOT NULL, mae_improvement REAL NOT NULL, model_r2 REAL NOT NULL,
            baseline_mae_ci99_lower REAL, baseline_mae_ci99_upper REAL, model_mae_ci99_lower REAL, model_mae_ci99_upper REAL,
            improvement_ci99_lower REAL, improvement_ci99_upper REAL, r2_ci99_lower REAL, r2_ci99_upper REAL,
            evaluated_at_utc TEXT NOT NULL, PRIMARY KEY (metric, fold)
        );
        """
    )
    con.execute("DELETE FROM step7_group_effect")
    con.execute("DELETE FROM step7_relationship_effect")
    con.execute("DELETE FROM step7_count_model")
    con.execute("DELETE FROM step7_forecast_result")

    group_results = []
    count_results = []
    # M1/M2: city/zone comparisons. Unknown zones are excluded from contrasts.
    for metric in METRICS:
        model_rows = [row for row in rows if valid(metric, row, probable_temp_ids) and row["zone"] != "[UNKNOWN]"]
        if len(model_rows) < 50:
            continue
        model = fit_model(model_rows, metric, count=metric in COUNT_METRICS)
        beta_samples = bootstrap_model(model, model_rows, rng=rng)
        for factor in ("city", "zone"):
            groups = sorted(set(row[factor] for row in model_rows), key=str)
            effects = marginal_group_effects(model["beta"], beta_samples, model_rows, model["categories"], factor, groups, log_link=(metric in COUNT_METRICS))
            for group, effect, low, high, spread in effects:
                observed_sd = float(np.std(model["y"], ddof=1)) or 1.0
                group_results.append((
                    "M2_city_zone_counts" if metric in COUNT_METRICS else "M1_city_zone_continuous", factor, metric, str(group), sum(1 for row in model_rows if row[factor] == group), model["family"], effect, low, high, effect / observed_sd, model["dispersion"],
                    "eta-squared >= 0.06 equivalent; interval reported for adjusted contrast.", evaluated_at,
                ))
        if metric in COUNT_METRICS:
            count_results.append(("M2_city_zone_counts", metric, len(model_rows), model["family"], model["dispersion"], model["alpha_nb"], float(np.mean(model["y"])), "Adjusted city/zone contrasts stored in step7_group_effect.", evaluated_at))
    con.executemany("INSERT INTO step7_group_effect VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", group_results)
    con.executemany("INSERT INTO step7_count_model VALUES (?,?,?,?,?,?,?,?,?)", count_results)

    relationship_results = []
    # M3: traffic -> speed, M4: waterlogging -> incidents, M5: temperature -> outage.
    rel_specs = [
        ("M3_relationship_traffic_speed", "avg_speed_kmph", "traffic_volume", "huber", [("traffic_volume", 1000.0)]),
        ("M4_relationship_incidents_waterlogging", "road_incidents", "waterlogging_reports", "count", [("waterlogging_reports", 1.0)]),
        ("M5_relationship_temperature_outage", "power_outage_minutes", "temperature_c", "huber", [("temperature_c", 1.0)]),
    ]
    for model_id, target, predictor, model_type, numeric in rel_specs:
        model_rows = [row for row in rows if valid(target, row, probable_temp_ids) and valid(predictor, row, probable_temp_ids)]
        model = fit_model(model_rows, target, numeric=numeric, count=(model_type == "count"))
        beta_samples = bootstrap_model(model, model_rows, numeric=numeric, rng=rng)
        predictor_index = 1
        effect = float(model["beta"][predictor_index])
        effect_samples = beta_samples[:, predictor_index]
        low, high = effect_interval(effect_samples)
        y_sd = float(np.std(model["y"], ddof=1)) or 1.0
        x_sd = float(np.std([float(row[predictor]) for row in model_rows], ddof=1)) or 1.0
        predictor_scale = numeric[0][1]
        standardized = effect * (x_sd / predictor_scale) / y_sd
        if model["family"] == "huber":
            relationship_results.append((model_id, target, predictor, model["family"], len(model_rows), effect, low, high, standardized, None, None, None, None, evaluated_at))
        else:
            irr = math.exp(effect)
            irr_low, irr_high = math.exp(low), math.exp(high)
            relationship_results.append((model_id, target, predictor, model["family"], len(model_rows), effect, low, high, standardized, irr, irr_low, irr_high, model["dispersion"], evaluated_at))
    con.executemany("INSERT INTO step7_relationship_effect VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", relationship_results)

    # M7: rolling time validation against a city-month median baseline.
    forecast_results = []
    for metric in METRICS:
        target_rows = [row for row in rows if valid(metric, row, probable_temp_ids)]
        # Add a lagged same-city target using only earlier observations.
        prior = {}
        lagged = []
        for row in target_rows:
            copy = dict(row)
            copy["lag_value"] = prior.get(row["city"])
            prior[row["city"]] = float(row[metric])
            lagged.append(copy)
        target_rows = [row for row in lagged if row["lag_value"] is not None]
        if len(target_rows) < 100:
            continue
        metric_scale = max(float(np.std([row["lag_value"] for row in target_rows])), 1.0)
        for fold, (train_fraction, test_fraction) in enumerate(FORECAST_FOLDS, start=1):
            train_end = max(20, int(len(target_rows) * train_fraction))
            test_end = max(train_end + 2, int(len(target_rows) * test_fraction))
            train_rows = target_rows[:train_end]
            test_rows = target_rows[train_end:test_end]
            cats = categories_for(target_rows)
            X_train = forecast_features(train_rows, cats, metric_scale)
            y_train = np.asarray([float(row[metric]) for row in train_rows])
            if metric in COUNT_METRICS:
                family, alpha_nb, beta, w_fit, z_fit, dispersion = select_count_family(X_train, y_train)
                model = {"family": family, "beta": beta}
            else:
                beta, w_fit, z_fit, scale = fit_huber(X_train, y_train)
                model = {"family": "huber", "beta": beta}
            X_test = forecast_features(test_rows, cats, metric_scale)
            prediction = X_test @ model["beta"]
            # Count predictions must remain non-negative.
            prediction = np.maximum(prediction, 0.0) if metric in COUNT_METRICS else prediction
            by_cm = {}
            by_city = {}
            all_train = []
            for row in train_rows:
                value = float(row[metric]); all_train.append(value); by_cm.setdefault((row["city"], row["month"]), []).append(value); by_city.setdefault(row["city"], []).append(value)
            baseline = np.asarray([np.median(by_cm.get((row["city"], row["month"]), by_city.get(row["city"], all_train))) for row in test_rows])
            actual = np.asarray([float(row[metric]) for row in test_rows])
            base_mae = float(np.mean(np.abs(actual - baseline)))
            model_mae = float(np.mean(np.abs(actual - prediction)))
            improvement = (base_mae - model_mae) / base_mae if base_mae else 0.0
            total = float(np.sum((actual - np.mean(actual)) ** 2))
            r2 = float(1 - np.sum((actual - prediction) ** 2) / total) if total else 0.0
            boot = forecast_bootstrap(test_rows, actual, baseline, prediction, rng)
            forecast_results.append((metric, fold, model["family"], len(train_rows), len(test_rows), base_mae, model_mae, improvement, r2, boot["baseline_mae_ci"][0], boot["baseline_mae_ci"][1], boot["model_mae_ci"][0], boot["model_mae_ci"][1], boot["improvement_ci"][0], boot["improvement_ci"][1], boot["r2_ci"][0], boot["r2_ci"][1], evaluated_at))
    con.executemany("INSERT INTO step7_forecast_result VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", forecast_results)

    con.execute("UPDATE model_registry SET status='fitted_primary' WHERE status='predefined'")
    con.execute("UPDATE data_contract SET current_status='COMPLETED_STEP_7_PRIMARY_FITTING', action_required='Primary fit-for-purpose models fitted with date-block uncertainty intervals. Run imputation sensitivity models separately if required.' WHERE contract_key='step7_model_protocol'")
    group_count = len(group_results)
    relationship_count = len(relationship_results)
    forecast_count = len(forecast_results)
    con.execute("INSERT OR REPLACE INTO analysis_run VALUES (?,?,?,?)", (
        "step7_model_fitting",
        "Step 7 primary fit-for-purpose models fitted with effect sizes and 99% date-block uncertainty intervals.",
        None,
        json.dumps({"group_effect_rows": group_count, "relationship_rows": relationship_count, "forecast_rows": forecast_count, "bootstrap_repetitions": BOOTSTRAP_REPS, "seed": SEED, "imputation_used": False}),
    ))
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.commit()
    con.close()

    with GROUP_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f); writer.writerow(["model_id", "factor", "target_metric", "group_value", "n", "model_family", "effect_native", "ci99_lower", "ci99_upper", "effect_standardized", "dispersion_ratio"]); writer.writerows(group_results)
    with REL_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f); writer.writerow(["model_id", "target_metric", "predictor_metric", "model_family", "n", "effect_native", "ci99_lower", "ci99_upper", "effect_standardized", "rate_ratio", "rate_ratio_ci99_lower", "rate_ratio_ci99_upper", "dispersion_ratio"]); writer.writerows(relationship_results)
    with COUNT_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f); writer.writerow(["model_id", "target_metric", "n", "selected_family", "dispersion_ratio", "nb_alpha", "mean_count"]); writer.writerows([row[:7] for row in count_results])
    with FORECAST_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f); writer.writerow(["metric", "fold", "model_family", "train_n", "test_n", "baseline_mae", "model_mae", "mae_improvement", "model_r2", "improvement_ci99_lower", "improvement_ci99_upper", "r2_ci99_lower", "r2_ci99_upper"]); writer.writerows([row[:9] + row[13:17] for row in forecast_results])

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    relationship_rows = con.execute("SELECT * FROM step7_relationship_effect ORDER BY model_id").fetchall()
    group_summary = con.execute("SELECT factor,target_metric,MAX(ABS(effect_native)) AS max_abs_effect, MIN(ci99_lower) AS min_ci, MAX(ci99_upper) AS max_ci, MAX(ABS(effect_standardized)) AS max_std FROM step7_group_effect GROUP BY factor,target_metric ORDER BY factor,target_metric").fetchall()
    count_rows = con.execute("SELECT * FROM step7_count_model ORDER BY target_metric").fetchall()
    forecast_summary = con.execute("SELECT metric,AVG(baseline_mae),AVG(model_mae),AVG(mae_improvement),AVG(model_r2),MIN(improvement_ci99_lower),MAX(improvement_ci99_upper),MIN(r2_ci99_lower),MAX(r2_ci99_upper) FROM step7_forecast_result GROUP BY metric ORDER BY metric").fetchall()
    con.close()

    lines = [
        "# UrbanPulse Step 7: Fit-for-Purpose Model Results",
        "",
        "Primary models use the canonical observed layer only. Missing values were not imputed. Effects are reported with 99% date-block bootstrap uncertainty intervals.",
        "",
        f"Bootstrap repetitions: `{BOOTSTRAP_REPS:,}`. Seed: `{SEED}`. SQLite integrity check: `{integrity}`.",
        "",
        "## Adjusted relationships",
        "",
        "| Model | Relationship | n | Model | Effect | 99% interval | Standardized effect |",
        "|---|---|---:|---|---:|---|---:|",
    ]
    for row in relationship_rows:
        effect = row[5]
        interval = f"[{row[6]:.4f}, {row[7]:.4f}]"
        label = f"{LABELS[row[2]]} -> {LABELS[row[1]]}"
        if row[9] is not None:
            effect_text = f"IRR {row[9]:.4f}"
            interval = f"[{row[10]:.4f}, {row[11]:.4f}]"
        else:
            effect_text = f"{effect:.4f}"
        lines.append(f"| {row[0]} | {label} | {row[4]:,} | {row[3]} | {effect_text} | {interval} | {row[8]:.4f} |")
    lines += [
        "",
        "## City and zone effects",
        "",
        "The table reports the largest absolute adjusted contrast across groups for each target. Full group-level contrasts are in the CSV output.",
        "",
        "| Factor | Target | Largest absolute native contrast | Range of 99% intervals | Largest standardized contrast |",
        "|---|---|---:|---|---:|",
    ]
    for row in group_summary:
        lines.append(f"| {row[0]} | {LABELS[row[1]]} | {row[2]:.4f} | [{row[3]:.4f}, {row[4]:.4f}] | {row[5]:.4f} |")
    lines += [
        "",
        "## Count-model selection",
        "",
        "Poisson was used only when the observed dispersion ratio was at or below 1.5. Otherwise, negative binomial was used.",
        "",
        "| Target | n | Selected model | Dispersion ratio | Mean count |",
        "|---|---:|---|---:|---:|",
    ]
    for row in count_rows:
        lines.append(f"| {LABELS[row[1]]} | {row[2]:,} | {row[3]} | {row[4]:.3f} | {row[6]:.3f} |")
    lines += [
        "",
        "## Forecasting",
        "",
        "Forecasts use three expanding chronological holdouts and are compared with a city-month median baseline.",
        "",
        "| Metric | Mean baseline MAE | Mean model MAE | Mean improvement | Mean R² | Improvement interval range | R² interval range |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for row in forecast_summary:
        lines.append(f"| {LABELS[row[0]]} | {row[1]:.3f} | {row[2]:.3f} | {row[3]:.1%} | {row[4]:.3f} | [{row[5]:.1%}, {row[6]:.1%}] | [{row[7]:.3f}, {row[8]:.3f}] |")
    lines += [
        "",
        "## Interpretation",
        "",
        "The fitted models quantify adjusted effects and uncertainty for the sampled stream. They do not convert this intentional sample into a complete city-zone panel or establish causality. Any imputation-based model comparison remains a separate sensitivity task.",
        "",
        "## Outputs",
        "",
        f"Group effects: `{GROUP_CSV_PATH}`",
        f"Adjusted relationships: `{REL_CSV_PATH}`",
        f"Count-model selection: `{COUNT_CSV_PATH}`",
        f"Forecast results: `{FORECAST_CSV_PATH}`",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(REPORT_PATH), "group_effect_rows": group_count, "relationship_rows": relationship_count, "forecast_rows": forecast_count, "integrity": integrity}, indent=2))


if __name__ == "__main__":
    main()
