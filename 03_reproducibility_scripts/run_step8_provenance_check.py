#!/usr/bin/env python3
"""Run the locked UrbanPulse Step 8 provenance null simulation."""

from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from project_config import DB_PATH, OUTPUT_DIR

DB = DB_PATH
REPORT = OUTPUT_DIR / "urbanpulse_step8_provenance_check.md"
CSV = OUTPUT_DIR / "urbanpulse_step8_provenance_diagnostics.csv"

B = 5000
SEED = 20261008
LOW_Q = 0.005
HIGH_Q = 0.995

METRICS = [
    ("traffic_volume", "cleaned_traffic_volume", "continuous"),
    ("avg_speed_kmph", "cleaned_avg_speed_kmph", "continuous"),
    ("public_transport_usage", "cleaned_public_transport_usage", "discrete"),
    ("parking_occupancy_pct", "cleaned_parking_occupancy_pct", "continuous"),
    ("road_incidents", "cleaned_road_incidents", "discrete"),
    ("waterlogging_reports", "cleaned_waterlogging_reports", "discrete"),
    ("power_outage_minutes", "cleaned_power_outage_minutes", "continuous"),
    ("citizen_complaints", "cleaned_citizen_complaints", "discrete"),
    ("temperature_c", "cleaned_temperature_c", "continuous"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rank_average(values: np.ndarray) -> np.ndarray:
    """Average ranks, 1-based, for a one-dimensional finite vector."""
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    ranks_sorted = np.empty(values.size, dtype=float)
    start = 0
    while start < values.size:
        end = start + 1
        while end < values.size and sorted_values[end] == sorted_values[start]:
            end += 1
        ranks_sorted[start:end] = (start + 1 + end) / 2.0
        start = end
    ranks = np.empty(values.size, dtype=float)
    ranks[order] = ranks_sorted
    return ranks


def safe_corr(x: np.ndarray, y: np.ndarray) -> float:
    if x.size < 3:
        return float("nan")
    x0 = x - x.mean()
    y0 = y - y.mean()
    den = math.sqrt(float(np.dot(x0, x0) * np.dot(y0, y0)))
    if den == 0:
        return 0.0
    return float(np.dot(x0, y0) / den)


def eta_squared(values: np.ndarray, groups: np.ndarray, valid: np.ndarray) -> float:
    vals = values[valid]
    grps = groups[valid]
    if vals.size < 3 or np.var(vals) == 0:
        return 0.0
    overall = float(vals.mean())
    between = 0.0
    for group in np.unique(grps):
        gv = vals[grps == group]
        if gv.size:
            between += gv.size * float((gv.mean() - overall) ** 2)
    return float(between / (vals.size * float(np.var(vals))))


def within_city_lag1(values: np.ndarray, cities: np.ndarray, timestamps: np.ndarray, valid: np.ndarray) -> float:
    pairs_x = []
    pairs_y = []
    for city in np.unique(cities):
        idx = np.flatnonzero((cities == city) & valid)
        if idx.size < 3:
            continue
        idx = idx[np.argsort(timestamps[idx], kind="mergesort")]
        v = values[idx]
        if v.size >= 3:
            pairs_x.append(v[:-1])
            pairs_y.append(v[1:])
    if not pairs_x:
        return float("nan")
    return safe_corr(np.concatenate(pairs_x), np.concatenate(pairs_y))


def entropy(values: np.ndarray) -> float:
    if values.size == 0:
        return float("nan")
    _, counts = np.unique(values, return_counts=True)
    p = counts / counts.sum()
    return float(-np.sum(p * np.log2(p)))


def percentile_position(sorted_values: np.ndarray, observed: float) -> float:
    return float(np.searchsorted(sorted_values, observed, side="right") / sorted_values.size)


def main() -> None:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        SELECT record_id, cleaned_timestamp_iso, cleaned_city, cleaned_zone,
               cleaned_traffic_volume, cleaned_avg_speed_kmph,
               cleaned_public_transport_usage, cleaned_parking_occupancy_pct,
               cleaned_road_incidents, cleaned_waterlogging_reports,
               cleaned_power_outage_minutes, cleaned_citizen_complaints,
               cleaned_temperature_c
        FROM canonical_cleaned
        ORDER BY cleaned_timestamp_iso, record_id
        """
    ).fetchall()
    n = len(rows)
    timestamps = np.array([r["cleaned_timestamp_iso"] for r in rows], dtype=object)
    cities = np.array([r["cleaned_city"] or "(missing)" for r in rows], dtype=object)
    zones = np.array([r["cleaned_zone"] or "(missing)" for r in rows], dtype=object)

    values = {}
    valid = {}
    ranks = {}
    kinds = {}
    for name, col, kind in METRICS:
        arr = np.array([np.nan if r[col] is None else float(r[col]) for r in rows], dtype=float)
        ok = np.isfinite(arr)
        values[name] = arr
        valid[name] = ok
        kinds[name] = kind
        ranks[name] = np.full(n, np.nan, dtype=float)
        ranks[name][ok] = rank_average(arr[ok])

    diagnostics = []
    sim_store = {}

    def add_diag(category: str, x: str, y: str | None, grouping: str | None,
                 observed: float, sim_values: np.ndarray, method: str,
                 fixed_by_construction: bool = False) -> None:
        finite = sim_values[np.isfinite(sim_values)]
        ordered = np.sort(finite)
        q_low = float(np.quantile(finite, LOW_Q, method="linear"))
        q_high = float(np.quantile(finite, HIGH_Q, method="linear"))
        pct = percentile_position(ordered, observed)
        flag = (not fixed_by_construction) and (observed < q_low or observed > q_high)
        diagnostics.append({
            "category": category,
            "variable_x": x,
            "variable_y": y or "",
            "grouping": grouping or "",
            "observed_value": float(observed),
            "sim_q005": q_low,
            "sim_q995": q_high,
            "observed_sim_percentile": pct,
            "flagged": int(flag),
            "method": method,
            "interpretation": "unusual under the independent-permutation null; not proof of synthetic origin" if flag else "not unusual under the independent-permutation null",
        })

    # Observed rank correlations, with the exact missingness mask preserved in every draw.
    for i, (name_i, _, _) in enumerate(METRICS):
        for name_j, _, _ in METRICS[i + 1:]:
            both = valid[name_i] & valid[name_j]
            observed = abs(safe_corr(ranks[name_i][both], ranks[name_j][both]))
            sim_store[("spearman_abs", name_i, name_j)] = np.empty(B, dtype=float)
            add_diag("pairwise_abs_spearman", name_i, name_j, None, observed,
                     sim_store[("spearman_abs", name_i, name_j)],
                     "absolute Pearson correlation of field-level average ranks")

    groups = {"city": cities, "zone": zones}
    for name, _, _ in METRICS:
        for grouping, group_values in groups.items():
            observed = eta_squared(values[name], group_values, valid[name])
            key = ("eta_squared", grouping, name)
            sim_store[key] = np.empty(B, dtype=float)
            add_diag("group_alignment_eta_squared", name, None, grouping, observed,
                     sim_store[key], "between-group sum of squares / total sum of squares")

    for name, _, _ in METRICS:
        observed = within_city_lag1(values[name], cities, timestamps, valid[name])
        key = ("lag1", name)
        sim_store[key] = np.empty(B, dtype=float)
        add_diag("within_city_lag1_autocorrelation", name, None, "city", observed,
                 sim_store[key], "correlation of consecutive observed values within city")

    # Entropy/unique rates are expected to be identical because the null preserves marginals.
    for name, _, kind in METRICS:
        observed_values = values[name][valid[name]]
        observed_entropy = entropy(observed_values)
        observed_unique = float(np.unique(observed_values).size / observed_values.size) if observed_values.size else float("nan")
        for metric_name, observed_value in (("entropy_bits", observed_entropy), ("unique_rate", observed_unique)):
            sim_store[(metric_name, name)] = np.full(B, observed_value, dtype=float)
            add_diag(f"marginal_{metric_name}", name, None, None, observed_value,
                     sim_store[(metric_name, name)],
                     "exactly preserved by independent permutation; no provenance separation expected",
                     fixed_by_construction=True)

    # Re-run the simulation and populate the preallocated diagnostic arrays.
    rng = np.random.default_rng(SEED)
    metric_order = [m[0] for m in METRICS]
    for b in range(B):
        sim_ranks = {}
        sim_values = {}
        for name in metric_order:
            ok = valid[name]
            rank_vec = np.full(n, np.nan, dtype=float)
            rank_vec[ok] = rng.permutation(ranks[name][ok])
            sim_ranks[name] = rank_vec
            value_vec = np.full(n, np.nan, dtype=float)
            value_vec[ok] = rng.permutation(values[name][ok])
            sim_values[name] = value_vec

        for i, name_i in enumerate(metric_order):
            for name_j in metric_order[i + 1:]:
                both = valid[name_i] & valid[name_j]
                sim_store[("spearman_abs", name_i, name_j)][b] = abs(safe_corr(sim_ranks[name_i][both], sim_ranks[name_j][both]))
        for name in metric_order:
            for grouping, group_values in groups.items():
                sim_store[("eta_squared", grouping, name)][b] = eta_squared(sim_values[name], group_values, valid[name])
            sim_store[("lag1", name)][b] = within_city_lag1(sim_values[name], cities, timestamps, valid[name])

    # The diagnostics list was created before simulations; update their intervals and flags now.
    for row in diagnostics:
        if row["category"] == "pairwise_abs_spearman":
            key = ("spearman_abs", row["variable_x"], row["variable_y"])
        elif row["category"] == "group_alignment_eta_squared":
            key = ("eta_squared", row["grouping"], row["variable_x"])
        elif row["category"] == "within_city_lag1_autocorrelation":
            key = ("lag1", row["variable_x"])
        else:
            continue
        finite = sim_store[key][np.isfinite(sim_store[key])]
        ordered = np.sort(finite)
        row["sim_q005"] = float(np.quantile(finite, LOW_Q, method="linear"))
        row["sim_q995"] = float(np.quantile(finite, HIGH_Q, method="linear"))
        row["observed_sim_percentile"] = percentile_position(ordered, row["observed_value"])
        row["flagged"] = int(row["observed_value"] < row["sim_q005"] or row["observed_value"] > row["sim_q995"])
        row["interpretation"] = (
            "unusual under the independent-permutation null; not proof of synthetic origin"
            if row["flagged"] else "not unusual under the independent-permutation null"
        )

    now = utc_now()
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS provenance_run (
            run_id TEXT PRIMARY KEY,
            protocol_id TEXT NOT NULL,
            simulation_repetitions INTEGER NOT NULL,
            random_seed INTEGER NOT NULL,
            lower_quantile REAL NOT NULL,
            upper_quantile REAL NOT NULL,
            row_count INTEGER NOT NULL,
            status TEXT NOT NULL,
            source_documentation_required INTEGER NOT NULL,
            completed_at_utc TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS provenance_diagnostic (
            run_id TEXT NOT NULL,
            category TEXT NOT NULL,
            variable_x TEXT NOT NULL,
            variable_y TEXT NOT NULL,
            grouping TEXT NOT NULL,
            observed_value REAL,
            sim_q005 REAL,
            sim_q995 REAL,
            observed_sim_percentile REAL,
            flagged INTEGER NOT NULL,
            method TEXT NOT NULL,
            interpretation TEXT NOT NULL,
            PRIMARY KEY (run_id, category, variable_x, variable_y, grouping)
        );
        """
    )
    run_id = "step8_provenance_20261008"
    con.execute("DELETE FROM provenance_diagnostic WHERE run_id = ?", (run_id,))
    con.execute("DELETE FROM provenance_run WHERE run_id = ?", (run_id,))
    con.execute(
        "INSERT INTO provenance_run VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (run_id, "P1", B, SEED, LOW_Q, HIGH_Q, n, "COMPLETED", 1, now),
    )
    con.executemany(
        "INSERT INTO provenance_diagnostic VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (run_id, d["category"], d["variable_x"], d["variable_y"], d["grouping"],
             d["observed_value"], d["sim_q005"], d["sim_q995"], d["observed_sim_percentile"],
             d["flagged"], d["method"], d["interpretation"])
            for d in diagnostics
        ],
    )
    con.execute(
        "UPDATE data_contract SET current_status=?, action_required=? WHERE contract_key=?",
        ("COMPLETED_STEP_8_PROVENANCE_SIMULATION",
         "Review flagged diagnostics as provenance indicators only; source documentation is required before any provenance conclusion.",
         "step8_provenance_check"),
    )
    con.execute(
        "INSERT OR REPLACE INTO analysis_run(run_key, value_text, value_num, details_json) VALUES (?, ?, ?, ?)",
        ("step8_provenance_check", "Step 8 provenance simulation completed; flags are not proof of synthetic origin.", float(B),
         json.dumps({"protocol_id": "P1", "simulations": B, "seed": SEED, "interval": [LOW_Q, HIGH_Q],
                     "row_count": n, "simulation_started": True, "source_documentation_required": True})),
    )
    con.commit()

    CSV.parent.mkdir(parents=True, exist_ok=True)
    with CSV.open("w", encoding="utf-8") as f:
        headers = list(diagnostics[0].keys())
        f.write(",".join(headers) + "\n")
        for d in diagnostics:
            f.write(",".join(json.dumps(d[h], ensure_ascii=False) for h in headers) + "\n")

    flagged = [d for d in diagnostics if d["flagged"]]
    pair_flags = [d for d in flagged if d["category"] == "pairwise_abs_spearman"]
    group_flags = [d for d in flagged if d["category"] == "group_alignment_eta_squared"]
    lag_flags = [d for d in flagged if d["category"] == "within_city_lag1_autocorrelation"]
    marginal_flags = [d for d in flagged if d["category"].startswith("marginal_")]
    raw_dupes = con.execute("SELECT COUNT(*) FROM raw_urbanpulse").fetchone()[0] - con.execute("SELECT COUNT(DISTINCT record_id) FROM raw_urbanpulse").fetchone()[0]

    with REPORT.open("w", encoding="utf-8") as f:
        f.write("# UrbanPulse Step 8: Provenance Check\n\n")
        f.write("## Scope and null model\n\n")
        f.write(f"The canonical observed layer ({n:,} rows) was compared with {B:,} simulated datasets. Each simulation independently permuted observed non-missing values within each metric while preserving the exact row count, marginal distribution, missingness mask, timestamp grid, city labels, and zone labels. This breaks cross-field alignment, city/zone alignment, and temporal alignment while keeping the one-dimensional distributions unchanged.\n\n")
        f.write(f"Random seed: `{SEED}`. A diagnostic is flagged when the observed value falls outside the simulated {LOW_Q:.3%}-{HIGH_Q:.3%} interval.\n\n")
        f.write("## Results\n\n")
        f.write(f"- Total diagnostics: {len(diagnostics):,}.\n")
        f.write(f"- Flagged under the null: {len(flagged):,} ({len(pair_flags):,} pairwise, {len(group_flags):,} group-alignment, {len(lag_flags):,} temporal, {len(marginal_flags):,} marginal-structure).\n")
        f.write(f"- Marginal entropy and unique-value-rate diagnostics were fixed by construction and produced no provenance separation.\n")
        f.write(f"- Raw-layer exact duplicate count reported separately: {raw_dupes:,}; the canonical layer is deduplicated.\n\n")
        f.write("### Flagged diagnostics\n\n")
        if flagged:
            f.write("| Category | Variables | Group | Observed | Simulated interval | Simulated percentile |\n|---|---|---|---:|---:|---:|\n")
            for d in flagged:
                variables = d["variable_x"] + (f" vs {d['variable_y']}" if d["variable_y"] else "")
                interval = f"[{d['sim_q005']:.4g}, {d['sim_q995']:.4g}]"
                f.write(f"| {d['category']} | {variables} | {d['grouping'] or '—'} | {d['observed_value']:.4g} | {interval} | {d['observed_sim_percentile']:.4%} |\n")
        else:
            f.write("No diagnostic fell outside the predeclared null interval.\n")
        f.write("\n## Interpretation boundary\n\n")
        f.write("A flag means the observed cross-field, group, or temporal alignment is unusual relative to this independent-permutation null model. It can be described as a synthetic-looking or structurally unusual signal under this test, but it is not proof that the data were synthetically generated. Real operational data can also create unusual patterns through collection design, aggregation, filtering, or leakage. Source documentation, collection metadata, and system provenance are required for a provenance conclusion.\n\n")
        f.write("The raw workbook and canonical values were not overwritten.\n")

    con.close()
    print(json.dumps({
        "report": str(REPORT),
        "csv": str(CSV),
        "run_id": run_id,
        "simulations": B,
        "diagnostics": len(diagnostics),
        "flagged": len(flagged),
        "pairwise_flags": len(pair_flags),
        "group_flags": len(group_flags),
        "temporal_flags": len(lag_flags),
        "marginal_flags": len(marginal_flags),
    }, indent=2))


if __name__ == "__main__":
    main()
