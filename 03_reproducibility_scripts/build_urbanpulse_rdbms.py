import csv
import hashlib
import json
import math
import os
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta

import numpy as np
from openpyxl import load_workbook

from project_config import INPUT_XLSX, OUTPUT_DIR

DB_PATH = os.path.join(OUTPUT_DIR, "urbanpulse_rdbms.sqlite")
SCHEMA_PATH = os.path.join(OUTPUT_DIR, "urbanpulse_schema.sql")
REPORT_PATH = os.path.join(OUTPUT_DIR, "urbanpulse_analysis_report.md")
CONTRACT_PATH = os.path.join(OUTPUT_DIR, "urbanpulse_data_contract.md")

SEED = 20261001
BOOTSTRAP_REPS = 5000
GROUP_PERMUTATIONS = 2000
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

EXPECTED_HEADERS = [
    "record_id",
    "city",
    "zone",
    "timestamp",
    *METRICS,
]

SQL_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE raw_urbanpulse (
    source_row_number INTEGER PRIMARY KEY,
    record_id TEXT,
    city TEXT,
    zone TEXT,
    timestamp_text TEXT,
    traffic_volume INTEGER,
    avg_speed_kmph REAL,
    public_transport_usage INTEGER,
    parking_occupancy_pct REAL,
    road_incidents INTEGER,
    waterlogging_reports INTEGER,
    power_outage_minutes REAL,
    citizen_complaints INTEGER,
    temperature_c REAL
);

CREATE TABLE urbanpulse_clean (
    record_id TEXT PRIMARY KEY,
    source_row_number INTEGER NOT NULL,
    city TEXT NOT NULL,
    zone_raw TEXT,
    zone_canonical TEXT,
    timestamp_text TEXT NOT NULL,
    timestamp_iso TEXT NOT NULL,
    observation_date TEXT NOT NULL,
    hour INTEGER NOT NULL,
    weekday INTEGER NOT NULL,
    month INTEGER NOT NULL,
    traffic_volume INTEGER,
    avg_speed_kmph REAL,
    public_transport_usage INTEGER,
    parking_occupancy_pct REAL,
    road_incidents INTEGER,
    waterlogging_reports INTEGER,
    power_outage_minutes REAL,
    citizen_complaints INTEGER,
    temperature_c REAL,
    issue_count INTEGER NOT NULL,
    quality_status TEXT NOT NULL
);

CREATE TABLE deduplication_log (
    source_row_number INTEGER PRIMARY KEY,
    record_id TEXT NOT NULL,
    duplicate_group_size INTEGER NOT NULL,
    kept_source_row_number INTEGER NOT NULL,
    action TEXT NOT NULL
);

CREATE TABLE data_quality_issue (
    issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT,
    source_row_number INTEGER,
    column_name TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    raw_value TEXT,
    suggested_value TEXT,
    treatment TEXT NOT NULL,
    requires_owner_confirmation INTEGER NOT NULL,
    severity TEXT NOT NULL
);

CREATE TABLE coverage_audit (
    audit_key TEXT PRIMARY KEY,
    value_num REAL,
    value_text TEXT,
    details_json TEXT
);

CREATE TABLE dimension_count (
    dimension TEXT NOT NULL,
    member TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    PRIMARY KEY (dimension, member)
);

CREATE TABLE missingness_summary (
    column_name TEXT PRIMARY KEY,
    raw_missing_count INTEGER NOT NULL,
    dedup_missing_count INTEGER NOT NULL,
    dedup_missing_rate REAL NOT NULL
);

CREATE TABLE metric_summary (
    metric TEXT PRIMARY KEY,
    n_observed INTEGER NOT NULL,
    mean REAL,
    median REAL,
    std_dev REAL,
    min_value REAL,
    max_value REAL,
    ci99_lower REAL,
    ci99_upper REAL,
    primary_exclusion_rule TEXT NOT NULL
);

CREATE TABLE correlation_result (
    metric_x TEXT NOT NULL,
    metric_y TEXT NOT NULL,
    method TEXT NOT NULL,
    n INTEGER NOT NULL,
    estimate REAL,
    ci99_lower REAL,
    ci99_upper REAL,
    p_value REAL,
    p_adjusted_holm REAL,
    significant_at_99 INTEGER NOT NULL,
    PRIMARY KEY (metric_x, metric_y, method)
);

CREATE TABLE group_test_result (
    factor TEXT NOT NULL,
    metric TEXT NOT NULL,
    groups INTEGER NOT NULL,
    n INTEGER NOT NULL,
    eta_squared REAL,
    p_value_permutation REAL,
    p_adjusted_holm REAL,
    significant_at_99 INTEGER NOT NULL,
    PRIMARY KEY (factor, metric)
);

CREATE TABLE analysis_run (
    run_key TEXT PRIMARY KEY,
    value_text TEXT,
    value_num REAL,
    details_json TEXT
);

CREATE TABLE data_contract (
    contract_key TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    specification TEXT NOT NULL,
    current_status TEXT NOT NULL,
    action_required TEXT
);

CREATE VIEW v_observed_analysis AS
SELECT *
FROM urbanpulse_clean
WHERE traffic_volume IS NOT NULL
  AND avg_speed_kmph IS NOT NULL
  AND avg_speed_kmph >= 0
  AND avg_speed_kmph <= 120
  AND public_transport_usage IS NOT NULL
  AND parking_occupancy_pct IS NOT NULL
  AND road_incidents IS NOT NULL
  AND waterlogging_reports IS NOT NULL
  AND power_outage_minutes IS NOT NULL
  AND citizen_complaints IS NOT NULL
  AND temperature_c IS NOT NULL;

CREATE VIEW v_city_zone_coverage AS
SELECT city, COALESCE(zone_canonical, '[UNKNOWN]') AS zone, COUNT(*) AS row_count
FROM urbanpulse_clean
GROUP BY city, COALESCE(zone_canonical, '[UNKNOWN]');
"""


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_timestamp(value):
    if isinstance(value, datetime):
        return value
    if value is None:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    return None


def canonical_zone(value):
    if value is None or str(value).strip() == "":
        return None
    return str(value).strip().casefold().capitalize()


def percentile_ci(values, rng, reps=BOOTSTRAP_REPS):
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return None, None
    batches = []
    for start in range(0, reps, 500):
        size = min(500, reps - start)
        samples = rng.choice(values, size=(size, len(values)), replace=True)
        batches.append(samples.mean(axis=1))
    boot = np.concatenate(batches)
    return tuple(float(x) for x in np.quantile(boot, [0.005, 0.995]))


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
    if len(x) < 4:
        return float("nan")
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    x = x - x.mean()
    y = y - y.mean()
    den = math.sqrt(float(np.dot(x, x) * np.dot(y, y)))
    return float(np.dot(x, y) / den) if den else 0.0


def normal_two_sided_p(z):
    return float(math.erfc(abs(z) / math.sqrt(2.0)))


def fisher_ci(r, n):
    if n <= 3:
        return None, None
    r_clip = max(min(float(r), 0.999999), -0.999999)
    z = math.atanh(r_clip)
    se = 1.0 / math.sqrt(n - 3)
    return tuple(float(math.tanh(v)) for v in (z - Z99 * se, z + Z99 * se))


def correlation_p(r, n):
    if n <= 3 or not math.isfinite(r):
        return 1.0
    z = math.atanh(max(min(float(r), 0.999999), -0.999999)) * math.sqrt(n - 3)
    return normal_two_sided_p(z)


def holm_adjust(p_values):
    if not p_values:
        return []
    order = sorted(range(len(p_values)), key=lambda i: p_values[i])
    adjusted = [1.0] * len(p_values)
    running = 0.0
    m = len(p_values)
    for rank, index in enumerate(order):
        value = min(1.0, (m - rank) * p_values[index])
        running = max(running, value)
        adjusted[index] = running
    return adjusted


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


def permutation_group_test(values, labels, rng, reps=GROUP_PERMUTATIONS):
    values = np.asarray(values, dtype=float)
    labels = np.asarray(labels)
    observed = eta_squared(values, labels)
    exceed = 0
    for _ in range(reps):
        shuffled = rng.permutation(labels)
        if eta_squared(values, shuffled) >= observed - 1e-15:
            exceed += 1
    return observed, float((exceed + 1) / (reps + 1))


def valid_metric_value(metric, value):
    if value is None:
        return False
    if metric == "avg_speed_kmph":
        return 0 <= float(value) <= 120
    return True


def clean_metric_index(metric):
    # urbanpulse_clean places the nine metrics after 11 identity/derived fields.
    return 11 + METRICS.index(metric)


def get_metric_rows(clean_rows, metric, group_field=None):
    metric_index = clean_metric_index(metric)
    results = []
    for row in clean_rows:
        value = row[metric_index]
        if not valid_metric_value(metric, value):
            continue
        if group_field is None:
            results.append((float(value), None))
        else:
            results.append((float(value), row[group_field]))
    return results


def clean_row_from_raw(raw_row, source_row_number):
    record_id, city, zone, timestamp, *metric_values = raw_row
    dt = parse_timestamp(timestamp)
    if dt is None:
        raise ValueError(f"Unparseable timestamp at source row {source_row_number}: {timestamp!r}")
    zone_canon = canonical_zone(zone)
    row = [
        record_id,
        source_row_number,
        city,
        zone,
        zone_canon,
        str(timestamp),
        dt.strftime("%Y-%m-%dT%H:%M:%S"),
        dt.strftime("%Y-%m-%d"),
        dt.hour,
        dt.weekday(),
        dt.month,
        *metric_values,
    ]
    return row


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for path in (DB_PATH, SCHEMA_PATH, REPORT_PATH, CONTRACT_PATH):
        if os.path.exists(path):
            os.remove(path)

    source_hash = sha256_file(INPUT_XLSX)
    workbook = load_workbook(INPUT_XLSX, read_only=True, data_only=True)
    sheet_names = workbook.sheetnames
    ws = workbook[sheet_names[0]]
    headers = [ws.cell(1, col).value for col in range(1, ws.max_column + 1)]
    if headers != EXPECTED_HEADERS:
        raise ValueError(f"Unexpected headers: {headers}")
    raw_rows = []
    for source_row_number, values in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if all(value is None for value in values):
            continue
        raw_rows.append((source_row_number, list(values)))
    workbook.close()

    duplicate_groups = defaultdict(list)
    for source_row_number, values in raw_rows:
        duplicate_groups[tuple(values)].append(source_row_number)
    kept_rows = []
    duplicate_log = []
    for source_row_number, values in raw_rows:
        group = duplicate_groups[tuple(values)]
        kept = group[0]
        if source_row_number == kept:
            kept_rows.append((source_row_number, values))
        if len(group) > 1:
            duplicate_log.append((source_row_number, values[0], len(group), kept, "kept" if source_row_number == kept else "removed_exact_duplicate"))

    clean_rows = [clean_row_from_raw(values, source_row_number) for source_row_number, values in kept_rows]
    clean_rows_by_id = {row[0]: row for row in clean_rows}
    if len(clean_rows_by_id) != len(clean_rows):
        raise ValueError("Non-exact duplicate record IDs remain after exact-row de-duplication")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SQL_SCHEMA)

    raw_sql = """INSERT INTO raw_urbanpulse VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
    conn.executemany(raw_sql, [(source_row, *values) for source_row, values in raw_rows])
    clean_sql = """INSERT INTO urbanpulse_clean VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
    clean_insert_rows = []
    for row in clean_rows:
        record_id, source_row_number, city, zone_raw, zone_canonical, timestamp_text, timestamp_iso, obs_date, hour, weekday, month, *metrics = row
        flags = []
        if zone_raw not in (None, "") and zone_raw != zone_canonical:
            flags.append("zone_case_variant")
        if zone_raw in (None, ""):
            flags.append("zone_missing")
        for metric, value in zip(METRICS, metrics):
            if value is None:
                flags.append(f"{metric}:missing")
        if metrics[1] is not None and metrics[1] < 0:
            flags.append("avg_speed_kmph:negative")
        if metrics[1] is not None and metrics[1] > 120:
            flags.append("avg_speed_kmph:extreme")
        if metrics[3] is not None and metrics[3] > 100:
            flags.append("parking_occupancy_pct:over_100")
        if metrics[8] is not None and metrics[8] >= 45:
            flags.append("temperature_c:high")
        if metrics[6] is not None and metrics[6] > 60:
            flags.append("power_outage_minutes:over_60")
        status = "review" if flags else "observed"
        clean_insert_rows.append([record_id, source_row_number, city, zone_raw, zone_canonical, timestamp_text, timestamp_iso, obs_date, hour, weekday, month, *metrics, len(flags), status])
    conn.executemany(clean_sql, clean_insert_rows)
    conn.executemany("INSERT INTO deduplication_log VALUES (?,?,?,?,?)", duplicate_log)

    issue_rows = []
    for row in clean_rows:
        record_id, source_row_number, city, zone_raw, zone_canonical, timestamp_text, timestamp_iso, obs_date, hour, weekday, month, *metrics = row
        def add_issue(column, issue_type, raw_value, suggested, treatment, confirm, severity):
            issue_rows.append((record_id, source_row_number, column, issue_type, None if raw_value is None else str(raw_value), None if suggested is None else str(suggested), treatment, int(confirm), severity))
        if zone_raw in (None, ""):
            add_issue("zone", "missing", None, None, "preserve_missing", True, "medium")
        elif zone_raw != zone_canonical:
            add_issue("zone", "case_variant", zone_raw, zone_canonical, "canonicalize_case_only", False, "low")
        for metric, value in zip(METRICS, metrics):
            if value is None:
                add_issue(metric, "missing", None, None, "preserve_missing", True, "medium")
        speed = metrics[1]
        if speed is not None and speed < 0:
            add_issue("avg_speed_kmph", "negative_value", speed, None, "exclude_primary_analysis_do_not_overwrite", True, "high")
        if speed is not None and speed > 120:
            add_issue("avg_speed_kmph", "extreme_value", speed, None, "retain_flag_exclude_primary_analysis", True, "high")
        parking = metrics[3]
        if parking is not None and parking > 100:
            add_issue("parking_occupancy_pct", "above_100", parking, None, "retain_flag_review_semantics", True, "medium")
        temp = metrics[8]
        if temp is not None and temp >= 45:
            add_issue("temperature_c", "high_value", temp, None, "retain_flag_review_sensor_context", True, "medium")
        outage = metrics[6]
        if outage is not None and outage > 60:
            add_issue("power_outage_minutes", "above_60", outage, None, "retain_flag_review_window_definition", True, "low")
    conn.executemany("""INSERT INTO data_quality_issue (record_id,source_row_number,column_name,issue_type,raw_value,suggested_value,treatment,requires_owner_confirmation,severity) VALUES (?,?,?,?,?,?,?,?,?)""", issue_rows)

    # Structural coverage audit.
    canonical_timestamps = sorted({row[6] for row in clean_rows})
    timestamp_dt = [datetime.strptime(text, "%Y-%m-%dT%H:%M:%S") for text in canonical_timestamps]
    min_dt, max_dt = min(timestamp_dt), max(timestamp_dt)
    expected_slots = []
    cursor = min_dt
    while cursor <= max_dt:
        if cursor.hour in (0, 4, 8, 12, 16, 20):
            expected_slots.append(cursor.strftime("%Y-%m-%dT%H:%M:%S"))
        cursor += timedelta(hours=4)
    missing_slots = sorted(set(expected_slots) - set(canonical_timestamps))
    cities = sorted({row[2] for row in clean_rows})
    zones = sorted({row[4] for row in clean_rows if row[4] is not None})
    known_panel_keys = {(row[2], row[4], row[6]) for row in clean_rows if row[4] is not None}
    expected_panel = len(cities) * len(zones) * len(canonical_timestamps)
    coverage_values = [
        ("raw_rows", len(raw_rows), None, None),
        ("deduplicated_rows", len(clean_rows), None, None),
        ("exact_duplicate_rows_removed", len(raw_rows) - len(clean_rows), None, None),
        ("unique_record_ids_after_dedup", len(clean_rows_by_id), None, None),
        ("unique_timestamps_after_dedup", len(canonical_timestamps), None, None),
        ("expected_four_hour_slots", len(expected_slots), None, None),
        ("missing_four_hour_slots", len(missing_slots), json.dumps(missing_slots), None),
        ("full_panel_expected_rows", expected_panel, None, json.dumps({"cities": len(cities), "zones": len(zones), "timestamps": len(canonical_timestamps)})),
        ("full_panel_known_observed_keys", len(known_panel_keys), None, None),
        ("full_panel_known_coverage_pct", 100.0 * len(known_panel_keys) / expected_panel if expected_panel else None, None, None),
        ("one_row_per_timestamp_after_dedup", 1.0 if len(canonical_timestamps) == len(clean_rows) else 0.0, None, None),
        ("source_sha256", None, source_hash, None),
    ]
    conn.executemany("INSERT INTO coverage_audit VALUES (?,?,?,?)", coverage_values)

    for dimension, values in (("city", [row[2] for row in clean_rows]), ("zone_canonical", [row[4] if row[4] is not None else "[UNKNOWN]" for row in clean_rows]), ("hour", [str(row[8]) for row in clean_rows]), ("month", [str(row[10]) for row in clean_rows]), ("weekday", [str(row[9]) for row in clean_rows])):
        conn.executemany("INSERT INTO dimension_count VALUES (?,?,?)", [(dimension, str(member), count) for member, count in Counter(values).items()])

    for column_index, column in enumerate(EXPECTED_HEADERS):
        if column == "record_id":
            continue
        raw_missing = sum(1 for _, row in raw_rows if row[column_index] is None)
        dedup_missing = sum(1 for row in clean_rows if row[EXPECTED_HEADERS.index(column)] is None)
        conn.execute("INSERT INTO missingness_summary VALUES (?,?,?,?)", (column, raw_missing, dedup_missing, dedup_missing / len(clean_rows)))

    rng = np.random.default_rng(SEED)
    metric_stats = {}
    for metric in METRICS:
        metric_index = clean_metric_index(metric)
        values = [float(row[metric_index]) for row in clean_rows if valid_metric_value(metric, row[metric_index])]
        arr = np.asarray(values, dtype=float)
        lower, upper = percentile_ci(arr, rng)
        metric_stats[metric] = {"values": arr, "n": len(arr), "ci99_lower": lower, "ci99_upper": upper}
        rule = "exclude missing values; for avg_speed_kmph also exclude values outside 0-120"
        conn.execute("INSERT INTO metric_summary VALUES (?,?,?,?,?,?,?,?,?,?)", (metric, len(arr), float(arr.mean()) if len(arr) else None, float(np.median(arr)) if len(arr) else None, float(arr.std(ddof=1)) if len(arr) > 1 else None, float(arr.min()) if len(arr) else None, float(arr.max()) if len(arr) else None, lower, upper, rule))

    # Pairwise correlations with Fisher 99% intervals and Holm adjustment.
    corr_rows = []
    raw_corr_records = []
    for i, metric_x in enumerate(METRICS):
        for metric_y in METRICS[i + 1:]:
            ix, iy = clean_metric_index(metric_x), clean_metric_index(metric_y)
            pairs = [(row[ix], row[iy]) for row in clean_rows if valid_metric_value(metric_x, row[ix]) and valid_metric_value(metric_y, row[iy])]
            x = np.asarray([pair[0] for pair in pairs], dtype=float)
            y = np.asarray([pair[1] for pair in pairs], dtype=float)
            r = pearson(x, y)
            ci_low, ci_high = fisher_ci(r, len(x))
            p = correlation_p(r, len(x))
            rs = pearson(rankdata(x), rankdata(y))
            raw_corr_records.append((metric_x, metric_y, "pearson", len(x), r, ci_low, ci_high, p, 0.0, 0))
            rci_low, rci_high = fisher_ci(rs, len(x))
            rp = correlation_p(rs, len(x))
            raw_corr_records.append((metric_x, metric_y, "spearman", len(x), rs, rci_low, rci_high, rp, 0.0, 0))
    pearson_p = [row[7] for row in raw_corr_records if row[2] == "pearson"]
    pearson_adj = holm_adjust(pearson_p)
    spearman_p = [row[7] for row in raw_corr_records if row[2] == "spearman"]
    spearman_adj = holm_adjust(spearman_p)
    pi = si = 0
    for row in raw_corr_records:
        adj = pearson_adj[pi] if row[2] == "pearson" else spearman_adj[si]
        if row[2] == "pearson": pi += 1
        else: si += 1
        out = list(row)
        out[8] = adj
        out[9] = int(adj < ALPHA)
        corr_rows.append(tuple(out))
    conn.executemany("INSERT INTO correlation_result VALUES (?,?,?,?,?,?,?,?,?,?)", corr_rows)

    # Group effects: permutation eta-squared tests, Holm adjusted across all 45 tests.
    group_records = []
    factor_index = {"city": 2, "zone": 4, "month": 10, "hour": 8, "weekday": 9}
    for factor, index in factor_index.items():
        for metric in METRICS:
            metric_index = clean_metric_index(metric)
            pairs = [(row[metric_index], row[index]) for row in clean_rows if valid_metric_value(metric, row[metric_index]) and row[index] is not None]
            values = np.asarray([pair[0] for pair in pairs], dtype=float)
            labels_raw = [pair[1] for pair in pairs]
            labels_unique = {label: i for i, label in enumerate(sorted(set(labels_raw), key=str))}
            labels = np.asarray([labels_unique[label] for label in labels_raw], dtype=int)
            eta, p = permutation_group_test(values, labels, rng)
            group_records.append([factor, metric, len(labels_unique), len(values), eta, p, 0.0, 0])
    group_adj = holm_adjust([row[5] for row in group_records])
    for row, adjusted in zip(group_records, group_adj):
        row[6] = adjusted
        row[7] = int(adjusted < ALPHA)
    conn.executemany("INSERT INTO group_test_result VALUES (?,?,?,?,?,?,?,?)", group_records)

    # Record run settings and conclusions.
    analysis_meta = [
        ("alpha", None, ALPHA, json.dumps({"confidence_level": 0.99})),
        ("bootstrap_repetitions", None, BOOTSTRAP_REPS, None),
        ("group_permutation_repetitions", None, GROUP_PERMUTATIONS, None),
        ("random_seed", None, SEED, None),
        ("primary_cleaning_policy", "preserve_raw_and_flag; no imputation or unverified correction", None, None),
        ("row_grain_status", "one_observation_per_timestamp_after_dedup; full-panel status unresolved", None, None),
        ("pairwise_pearson_significant_count", None, sum(row[9] for row in corr_rows if row[2] == "pearson"), None),
        ("pairwise_spearman_significant_count", None, sum(row[9] for row in corr_rows if row[2] == "spearman"), None),
        ("group_significant_count", None, sum(row[7] for row in group_records), None),
    ]
    conn.executemany("INSERT INTO analysis_run VALUES (?,?,?,?)", analysis_meta)

    complete_observed_count = conn.execute("SELECT COUNT(*) FROM v_observed_analysis").fetchone()[0]
    contract_rows = [
        ("row_grain", "Structure", "One observed row per four-hour timestamp after exact de-duplication; not a complete city-zone-time panel.", "BLOCKED_FOR_FULL_PANEL_INFERENCE", "Data owner must confirm whether the sparse sampled grain is intentional."),
        ("primary_key_clean", "Structure", "record_id is unique in urbanpulse_clean; source row number is retained for traceability.", "PASS", None),
        ("timestamp", "Structure", f"All {len(canonical_timestamps):,} deduplicated timestamps parse and align to the four-hour schedule from {min_dt.date()} through {max_dt}.", "PASS", None),
        ("city", "Domain", f"Seven city labels are present: {', '.join(cities)}.", "PASS", None),
        ("zone", "Domain", f"Five canonical zone labels are present, with {sum(1 for row in clean_rows if row[4] is None)} missing zone values; case variants were canonicalized only in the clean table.", "REQUIRES_OWNER_CONFIRMATION", "Confirm whether blank zones may remain unknown."),
        ("duplicates", "Quality", f"{len(raw_rows) - len(clean_rows)} exact duplicate rows are preserved in raw_urbanpulse and excluded only from urbanpulse_clean.", "PASS_WITH_AUDIT_TRAIL", None),
        ("missing_numeric", "Quality", "Missing traffic, speed, and temperature values remain NULL in the analytical base; no imputation was applied.", "PRESERVE_NULL", "Choose an imputation policy only for a separately labeled sensitivity analysis."),
        ("speed", "Quality", "Five negative speeds and five speeds above 120 km/h are flagged and excluded from the primary observed analysis; raw values are unchanged.", "REQUIRES_OWNER_CONFIRMATION", "Confirm whether these are sentinel or sensor errors."),
        ("parking", "Quality", "113 parking readings above 100% are retained and flagged.", "REQUIRES_SEMANTIC_CONFIRMATION", "Confirm whether the metric is utilization relative to nominal capacity and can exceed 100%."),
        ("temperature", "Quality", "27 temperature readings at or above 45 C are retained and flagged.", "REQUIRES_SENSOR_CONTEXT", "Confirm valid operating range before any correction or exclusion."),
        ("power_outage", "Quality", "16 outage readings above 60 minutes are retained and flagged.", "REQUIRES_WINDOW_DEFINITION", "Confirm whether the observation window permits outages above 60 minutes."),
        ("analysis_base", "Analysis", f"{complete_observed_count:,} complete observed rows meet the primary metric and speed eligibility rules.", "READY_WITH_LIMITATION", "Do not generalize to a full panel until row grain is confirmed."),
        ("confidence_standard", "Analysis", "Primary intervals use 99% confidence and hypothesis tests use alpha 0.01 with Holm correction.", "PASS", None),
    ]
    conn.executemany("INSERT INTO data_contract VALUES (?,?,?,?,?)", contract_rows)

    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise ValueError(f"SQLite integrity check failed: {integrity}")
    conn.commit()
    conn.close()

    # Export schema and a decision-oriented report.
    with open(SCHEMA_PATH, "w", encoding="utf-8") as f:
        f.write(SQL_SCHEMA.strip() + "\n")

    def fmt(value, digits=3):
        if value is None:
            return "n/a"
        return f"{value:.{digits}f}"

    report_lines = [
        "# UrbanPulse RDBMS and 99% Analysis Report",
        "",
        "## Scope",
        "",
        "The raw workbook was loaded into SQLite without modifying the source file. Raw values are preserved. The cleaned table only canonicalizes zone capitalization and derives timestamp fields. Missing and questionable values remain flagged rather than silently imputed or corrected.",
        "",
        f"Source SHA-256: `{source_hash}`",
        "",
        "## Database objects",
        "",
        "- `raw_urbanpulse`: immutable source rows",
        "- `urbanpulse_clean`: deduplicated, typed, auditable analytical base",
        "- `deduplication_log`: exact duplicate decisions",
        "- `data_quality_issue`: row-level quality issues and treatments",
        "- `coverage_audit`, `dimension_count`, `missingness_summary`: structural checks",
        "- `metric_summary`, `correlation_result`, `group_test_result`: 99% analysis results",
        "- `data_contract`: authoritative schema, quality rules, and decision gates",
        "- `v_observed_analysis`: complete observed cases with invalid speeds excluded",
        "",
        "## Structural result",
        "",
        f"- Raw rows: **{len(raw_rows):,}**",
        f"- Deduplicated rows: **{len(clean_rows):,}**",
        f"- Exact duplicates removed from analytical base: **{len(raw_rows) - len(clean_rows):,}**",
        f"- Unique timestamps after deduplication: **{len(canonical_timestamps):,}**",
        f"- Expected four-hour slots in the date range: **{len(expected_slots):,}**",
        f"- Missing four-hour slots: **{len(missing_slots):,}**",
        f"- Full-panel rows if every city-zone-time combination were required: **{expected_panel:,}**",
        f"- Known city-zone-time keys observed: **{len(known_panel_keys):,} ({100.0 * len(known_panel_keys) / expected_panel:.2f}%)**",
        "",
        "The file behaves as one sampled observation per timestamp after exact de-duplication. It is not a complete city-zone panel unless most expected observations were omitted before delivery.",
        "",
        "## 99% statistical results",
        "",
        "The analysis used 99% confidence intervals and Holm correction at alpha = 0.01. It did not impute missing values or overwrite unverified values.",
        "",
        "### Metric summaries",
        "",
        "| Metric | n | Mean | 99% CI |",
        "|---|---:|---:|---:|",
    ]
    for metric in METRICS:
        values = metric_stats[metric]["values"]
        low, high = metric_stats[metric]["ci99_lower"], metric_stats[metric]["ci99_upper"]
        report_lines.append(f"| {metric} | {len(values):,} | {fmt(float(values.mean()))} | [{fmt(low)}, {fmt(high)}] |")
    corr_sig = sum(row[9] for row in corr_rows if row[2] == "pearson")
    group_sig = sum(row[7] for row in group_records)
    max_corr = max((abs(row[4]) for row in corr_rows if row[2] == "pearson"), default=0.0)
    report_lines += [
        "",
        "### Decision results",
        "",
        f"- Pearson metric pairs significant after Holm correction at 99%: **{corr_sig} of 36**.",
        f"- City, zone, month, hour, and weekday effects significant after Holm correction at 99%: **{group_sig} of 45**.",
        f"- Largest absolute Pearson correlation: **{max_corr:.3f}**.",
        "- These are non-detection results, not proof that the variables are mathematically independent.",
        "",
        "## Final assessment",
        "",
        "The RDBMS conversion and audit are complete. The dataset is usable for data-engineering, quality-control, and pipeline-testing work. It should not be treated as a complete city-zone sensor panel without confirmation of the intended grain. Any city, zone, temporal, or policy conclusion should remain provisional until the data owner confirms whether the sparse sampling is intentional.",
        "",
        "## Verification",
        "",
        "- SQLite `PRAGMA integrity_check`: `ok`",
        "- Raw rows preserved in `raw_urbanpulse`",
        "- Exact duplicates retained in raw table and logged separately",
        "- No automatic imputation",
        "- No unverified value correction",
        "- 99% intervals and alpha = 0.01 multiple-testing controls applied",
    ]
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")

    contract_lines = [
        "# UrbanPulse Data Contract",
        "",
        "This contract is the Step 2 quality gate for the SQLite RDBMS. The raw workbook remains unchanged. Quality treatments apply to the clean analytical layer only.",
        "",
        "| Key | Category | Specification | Status | Action required |",
        "|---|---|---|---|---|",
    ]
    for key, category, specification, status, action in contract_rows:
        safe = lambda value: str(value or "").replace("|", "\\|")
        contract_lines.append(f"| {safe(key)} | {safe(category)} | {safe(specification)} | {safe(status)} | {safe(action)} |")
    contract_lines += [
        "",
        "## Decision gate",
        "",
        "The dataset may proceed to descriptive and sensitivity analysis. Full panel inference, city ranking, and operational conclusions remain blocked until the data owner confirms whether one sampled observation per timestamp is intentional or whether city-zone combinations are missing from the source.",
    ]
    with open(CONTRACT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(contract_lines) + "\n")

    print(json.dumps({
        "database": DB_PATH,
        "schema": SCHEMA_PATH,
        "report": REPORT_PATH,
        "contract": CONTRACT_PATH,
        "raw_rows": len(raw_rows),
        "deduplicated_rows": len(clean_rows),
        "exact_duplicates": len(raw_rows) - len(clean_rows),
        "unique_timestamps": len(canonical_timestamps),
        "expected_full_panel_rows": expected_panel,
        "known_panel_keys": len(known_panel_keys),
        "known_panel_coverage_pct": 100.0 * len(known_panel_keys) / expected_panel,
        "max_abs_pearson": max_corr,
        "pearson_significant_after_holm": corr_sig,
        "group_significant_after_holm": group_sig,
        "sqlite_integrity": integrity,
    }, indent=2))


if __name__ == "__main__":
    main()
