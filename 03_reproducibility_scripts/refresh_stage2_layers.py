"""Refresh the UrbanPulse raw and canonical data layers from a workbook.

This script is intentionally limited to Stage 2. It does not perform imputation,
re-run inferential models, or overwrite the immutable source workbook. Point it at
a disposable database copy before refreshing a finalized analysis database.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from openpyxl import load_workbook


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
HEADERS = ["record_id", "city", "zone", "timestamp", *METRICS]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_timestamp(value) -> datetime:
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unparseable timestamp: {value!r}")


def canonical_zone(value):
    if value is None or str(value).strip() == "":
        return None
    return str(value).strip().casefold().capitalize()


def valid_metric(metric: str, value) -> bool:
    if value is None:
        return False
    if metric == "avg_speed_kmph":
        return 0 <= float(value) <= 120
    return True


def load_raw(input_path: Path):
    workbook = load_workbook(input_path, read_only=True, data_only=True)
    worksheet = workbook[workbook.sheetnames[0]]
    header_row = next(worksheet.iter_rows(min_row=1, max_row=1, values_only=True))
    headers = list(header_row)
    if headers != HEADERS:
        raise ValueError(f"Unexpected headers: {headers!r}")
    rows = []
    for source_row_number, values in enumerate(worksheet.iter_rows(min_row=2, values_only=True), start=2):
        if all(value is None for value in values):
            continue
        if len(values) < len(HEADERS):
            values = tuple(values) + (None,) * (len(HEADERS) - len(values))
        if len(values) > len(HEADERS):
            raise ValueError(f"Unexpected column count at source row {source_row_number}")
        rows.append((source_row_number, list(values)))
    workbook.close()
    return rows


def prepare_rows(raw_rows):
    duplicate_groups = defaultdict(list)
    for source_row_number, values in raw_rows:
        duplicate_groups[tuple(values)].append(source_row_number)

    kept_rows = []
    duplicate_log = []
    for source_row_number, values in raw_rows:
        group = duplicate_groups[tuple(values)]
        kept_source_row = group[0]
        if source_row_number == kept_source_row:
            kept_rows.append((source_row_number, values))
        if len(group) > 1:
            duplicate_log.append(
                (
                    source_row_number,
                    values[0],
                    len(group),
                    kept_source_row,
                    "kept" if source_row_number == kept_source_row else "removed_exact_duplicate",
                )
            )

    prepared = []
    for source_row_number, values in kept_rows:
        record_id, city, zone, timestamp, *metrics = values
        parsed = parse_timestamp(timestamp)
        zone_clean = canonical_zone(zone)
        prepared.append(
            {
                "record_id": record_id,
                "source_row_number": source_row_number,
                "city": city,
                "zone_raw": zone,
                "zone_clean": zone_clean,
                "timestamp_raw": str(timestamp),
                "timestamp_iso": parsed.strftime("%Y-%m-%dT%H:%M:%S"),
                "observation_date": parsed.strftime("%Y-%m-%d"),
                "hour": parsed.hour,
                "weekday": parsed.weekday(),
                "month": parsed.month,
                "metrics": dict(zip(METRICS, metrics)),
            }
        )

    record_ids = [row["record_id"] for row in prepared]
    if len(record_ids) != len(set(record_ids)):
        raise ValueError("Non-exact duplicate record IDs remain after exact-row de-duplication")
    return prepared, duplicate_log


def ensure_schema(con: sqlite3.Connection):
    con.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS raw_urbanpulse (
            source_row_number INTEGER PRIMARY KEY, record_id TEXT, city TEXT, zone TEXT,
            timestamp_text TEXT, traffic_volume INTEGER, avg_speed_kmph REAL,
            public_transport_usage INTEGER, parking_occupancy_pct REAL, road_incidents INTEGER,
            waterlogging_reports INTEGER, power_outage_minutes REAL, citizen_complaints INTEGER,
            temperature_c REAL
        );
        CREATE TABLE IF NOT EXISTS urbanpulse_clean (
            record_id TEXT PRIMARY KEY, source_row_number INTEGER NOT NULL, city TEXT NOT NULL,
            zone_raw TEXT, zone_canonical TEXT, timestamp_text TEXT NOT NULL, timestamp_iso TEXT NOT NULL,
            observation_date TEXT NOT NULL, hour INTEGER NOT NULL, weekday INTEGER NOT NULL, month INTEGER NOT NULL,
            traffic_volume INTEGER, avg_speed_kmph REAL, public_transport_usage INTEGER,
            parking_occupancy_pct REAL, road_incidents INTEGER, waterlogging_reports INTEGER,
            power_outage_minutes REAL, citizen_complaints INTEGER, temperature_c REAL,
            issue_count INTEGER NOT NULL, quality_status TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS deduplication_log (
            source_row_number INTEGER PRIMARY KEY, record_id TEXT NOT NULL,
            duplicate_group_size INTEGER NOT NULL, kept_source_row_number INTEGER NOT NULL, action TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS data_quality_issue (
            issue_id INTEGER PRIMARY KEY AUTOINCREMENT, record_id TEXT, source_row_number INTEGER,
            column_name TEXT NOT NULL, issue_type TEXT NOT NULL, raw_value TEXT, suggested_value TEXT,
            treatment TEXT NOT NULL, requires_owner_confirmation INTEGER NOT NULL, severity TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS canonical_cleaned (
            record_id TEXT PRIMARY KEY, source_row_number INTEGER NOT NULL,
            raw_city TEXT, cleaned_city TEXT, raw_zone TEXT, cleaned_zone TEXT,
            raw_timestamp TEXT, cleaned_timestamp_iso TEXT, observation_date TEXT, hour INTEGER,
            weekday INTEGER, month INTEGER,
            raw_traffic_volume INTEGER, cleaned_traffic_volume INTEGER,
            raw_avg_speed_kmph REAL, cleaned_avg_speed_kmph REAL,
            raw_public_transport_usage INTEGER, cleaned_public_transport_usage INTEGER,
            raw_parking_occupancy_pct REAL, cleaned_parking_occupancy_pct REAL,
            raw_road_incidents INTEGER, cleaned_road_incidents INTEGER,
            raw_waterlogging_reports INTEGER, cleaned_waterlogging_reports INTEGER,
            raw_power_outage_minutes REAL, cleaned_power_outage_minutes REAL,
            raw_citizen_complaints INTEGER, cleaned_citizen_complaints INTEGER,
            raw_temperature_c REAL, cleaned_temperature_c REAL,
            row_quality_status TEXT NOT NULL, primary_analysis_eligible INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS quality_flag (
            flag_id INTEGER PRIMARY KEY AUTOINCREMENT, record_id TEXT NOT NULL,
            source_row_number INTEGER NOT NULL, field_name TEXT NOT NULL,
            flag_type TEXT NOT NULL CHECK (flag_type IN ('missing','imputed','corrected','outlier','unknown')),
            raw_value TEXT, cleaned_value TEXT, reason TEXT NOT NULL, primary_analysis_effect TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS change_log (
            change_id INTEGER PRIMARY KEY AUTOINCREMENT, record_id TEXT, source_row_number INTEGER NOT NULL,
            field_name TEXT NOT NULL, raw_value TEXT, cleaned_value TEXT,
            change_type TEXT NOT NULL, method TEXT NOT NULL, primary_analysis_effect TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS quality_flag_summary (
            flag_type TEXT NOT NULL, field_name TEXT NOT NULL, flag_count INTEGER NOT NULL,
            PRIMARY KEY (flag_type, field_name)
        );
        CREATE TABLE IF NOT EXISTS coverage_audit (
            audit_key TEXT PRIMARY KEY, value_num REAL, value_text TEXT, details_json TEXT
        );
        CREATE TABLE IF NOT EXISTS dimension_count (
            dimension TEXT NOT NULL, member TEXT NOT NULL, row_count INTEGER NOT NULL,
            PRIMARY KEY (dimension, member)
        );
        CREATE TABLE IF NOT EXISTS missingness_summary (
            column_name TEXT PRIMARY KEY, raw_missing_count INTEGER NOT NULL,
            dedup_missing_count INTEGER NOT NULL, dedup_missing_rate REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS data_contract (
            contract_key TEXT PRIMARY KEY, category TEXT NOT NULL, specification TEXT NOT NULL,
            current_status TEXT NOT NULL, action_required TEXT
        );
        CREATE TABLE IF NOT EXISTS analysis_run (
            run_key TEXT PRIMARY KEY, value_text TEXT, value_num REAL, details_json TEXT
        );
        CREATE VIEW IF NOT EXISTS v_primary_observed AS
        SELECT * FROM canonical_cleaned WHERE primary_analysis_eligible = 1;

        CREATE VIEW IF NOT EXISTS v_primary_zone_complete AS
        SELECT * FROM v_primary_observed WHERE cleaned_zone IS NOT NULL;
        """
    )


def refresh_layers(con: sqlite3.Connection, input_path: Path):
    raw_rows = load_raw(input_path)
    prepared, duplicate_log = prepare_rows(raw_rows)
    con.execute("BEGIN")
    try:
        for table in (
            "raw_urbanpulse",
            "urbanpulse_clean",
            "deduplication_log",
            "data_quality_issue",
            "canonical_cleaned",
            "quality_flag",
            "change_log",
            "quality_flag_summary",
            "coverage_audit",
            "dimension_count",
            "missingness_summary",
        ):
            con.execute(f"DELETE FROM {table}")

        con.executemany(
            "INSERT INTO raw_urbanpulse VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(source_row, *values) for source_row, values in raw_rows],
        )
        con.executemany("INSERT INTO deduplication_log VALUES (?,?,?,?,?)", duplicate_log)

        clean_rows = []
        canonical_rows = []
        flags = []
        changes = []
        quality_issues = []

        def text_or_none(value):
            return None if value is None else str(value)

        for row in prepared:
            metrics = row["metrics"]
            row_flags = []
            if row["zone_raw"] in (None, ""):
                row_flags.extend([
                    ("zone", "missing", None, None, "Zone is blank in the source.", "Retained as NULL in primary analysis."),
                    ("zone", "unknown", None, None, "Zone cannot be inferred from the source.", "Retained as NULL in primary analysis."),
                ])
                quality_issues.append((row["record_id"], row["source_row_number"], "zone", "missing", None, None, "preserve_missing", 1, "medium"))
            elif row["zone_raw"] != row["zone_clean"]:
                row_flags.append(("zone", "corrected", row["zone_raw"], row["zone_clean"], "Case normalized to the controlled vocabulary.", "Normalization only; retained in primary analysis."))
                changes.append((row["record_id"], row["source_row_number"], "zone", text_or_none(row["zone_raw"]), text_or_none(row["zone_clean"]), "canonicalized", "casefold then controlled-vocabulary capitalization", "included after normalization"))
                quality_issues.append((row["record_id"], row["source_row_number"], "zone", "case_variant", text_or_none(row["zone_raw"]), text_or_none(row["zone_clean"]), "canonicalize_case_only", 0, "low"))

            for metric, value in metrics.items():
                if value is None:
                    row_flags.append((metric, "missing", None, None, "Source value is blank.", "Excluded for that metric; no imputation in primary analysis."))
                    quality_issues.append((row["record_id"], row["source_row_number"], metric, "missing", None, None, "preserve_missing", 1, "medium"))

            speed = metrics["avg_speed_kmph"]
            if speed is not None and (speed < 0 or speed > 120):
                row_flags.append(("avg_speed_kmph", "outlier", speed, speed, "Speed is outside the conservative 0-120 km/h domain.", "Excluded from primary speed analysis."))
                quality_issues.append((row["record_id"], row["source_row_number"], "avg_speed_kmph", "out_of_domain", text_or_none(speed), None, "exclude_primary_analysis_do_not_overwrite", 1, "high"))
            parking = metrics["parking_occupancy_pct"]
            if parking is not None and parking > 100:
                row_flags.append(("parking_occupancy_pct", "outlier", parking, parking, "Parking exceeds nominal 100% occupancy.", "Retained and flagged; semantics require confirmation."))
                quality_issues.append((row["record_id"], row["source_row_number"], "parking_occupancy_pct", "above_100", text_or_none(parking), None, "retain_flag_review_semantics", 1, "medium"))
            temperature = metrics["temperature_c"]
            if temperature is not None and temperature >= 45:
                row_flags.append(("temperature_c", "outlier", temperature, temperature, "Temperature is at or above 45 C.", "Retained and flagged; sensor context required."))
                quality_issues.append((row["record_id"], row["source_row_number"], "temperature_c", "high_value", text_or_none(temperature), None, "retain_flag_review_sensor_context", 1, "medium"))
            outage = metrics["power_outage_minutes"]
            if outage is not None and outage > 60:
                row_flags.append(("power_outage_minutes", "outlier", outage, outage, "Outage exceeds 60 minutes.", "Retained and flagged; window definition required."))
                quality_issues.append((row["record_id"], row["source_row_number"], "power_outage_minutes", "above_60", text_or_none(outage), None, "retain_flag_review_window_definition", 1, "low"))

            for field, flag_type, raw_value, cleaned_value, reason, effect in row_flags:
                flags.append((row["record_id"], row["source_row_number"], field, flag_type, text_or_none(raw_value), text_or_none(cleaned_value), reason, effect))

            clean_values = [metrics[metric] for metric in METRICS]
            clean_rows.append((
                row["record_id"], row["source_row_number"], row["city"], row["zone_raw"], row["zone_clean"],
                row["timestamp_raw"], row["timestamp_iso"], row["observation_date"], row["hour"], row["weekday"], row["month"],
                *clean_values, len(row_flags), "flagged" if row_flags else "observed",
            ))
            eligible = int(all(valid_metric(metric, metrics[metric]) for metric in METRICS))
            canonical_rows.append((
                row["record_id"], row["source_row_number"], row["city"], row["city"], row["zone_raw"], row["zone_clean"],
                row["timestamp_raw"], row["timestamp_iso"], row["observation_date"], row["hour"], row["weekday"], row["month"],
                *sum(([metrics[metric], metrics[metric]] for metric in METRICS), []),
                "flagged" if row_flags else "observed", eligible,
            ))

        con.executemany("INSERT INTO urbanpulse_clean VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", clean_rows)
        con.executemany("INSERT INTO canonical_cleaned VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", canonical_rows)
        con.executemany("""
            INSERT INTO quality_flag (record_id,source_row_number,field_name,flag_type,raw_value,cleaned_value,reason,primary_analysis_effect)
            VALUES (?,?,?,?,?,?,?,?)
        """, flags)
        con.executemany("""
            INSERT INTO change_log (record_id,source_row_number,field_name,raw_value,cleaned_value,change_type,method,primary_analysis_effect)
            VALUES (?,?,?,?,?,?,?,?)
        """, changes)
        for source_row, record_id, group_size, kept_source_row, action in duplicate_log:
            if action == "removed_exact_duplicate":
                changes.append((record_id, source_row, "__row__", record_id, None, "deduplicated", "exact row match; retained first source occurrence", "row excluded from canonical primary layer"))
        if duplicate_log:
            con.executemany("""
                INSERT INTO change_log (record_id,source_row_number,field_name,raw_value,cleaned_value,change_type,method,primary_analysis_effect)
                VALUES (?,?,?,?,?,?,?,?)
            """, [row for row in changes if row[2] == "__row__"])
        con.executemany("""
            INSERT INTO data_quality_issue (record_id,source_row_number,column_name,issue_type,raw_value,suggested_value,treatment,requires_owner_confirmation,severity)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, quality_issues)
        con.execute("INSERT INTO quality_flag_summary SELECT flag_type,field_name,COUNT(*) FROM quality_flag GROUP BY flag_type,field_name")

        raw_missing = {header: sum(1 for _, values in raw_rows if values[index] is None) for index, header in enumerate(HEADERS)}
        dedup_missing = {header: sum(1 for row in prepared if (row["metrics"].get(header) if header in METRICS else row.get({"record_id": "record_id", "city": "city", "zone": "zone_raw", "timestamp": "timestamp_raw"}[header])) is None) for header in HEADERS}
        for header in HEADERS:
            if header == "record_id":
                continue
            con.execute("INSERT INTO missingness_summary VALUES (?,?,?,?)", (header, raw_missing[header], dedup_missing[header], dedup_missing[header] / len(prepared)))

        timestamps = sorted(row["timestamp_iso"] for row in prepared)
        timestamp_set = set(timestamps)
        start = datetime.strptime(timestamps[0], "%Y-%m-%dT%H:%M:%S")
        end = datetime.strptime(timestamps[-1], "%Y-%m-%dT%H:%M:%S")
        expected = []
        cursor = start
        while cursor <= end:
            if cursor.hour in (0, 4, 8, 12, 16, 20):
                expected.append(cursor.strftime("%Y-%m-%dT%H:%M:%S"))
            cursor += timedelta(hours=4)
        cities = sorted({row["city"] for row in prepared})
        zones = sorted({row["zone_clean"] for row in prepared if row["zone_clean"] is not None})
        known_keys = {(row["city"], row["zone_clean"], row["timestamp_iso"]) for row in prepared if row["zone_clean"] is not None}
        expected_panel = len(cities) * len(zones) * len(timestamps)
        coverage = [
            ("raw_rows", len(raw_rows), None, None),
            ("deduplicated_rows", len(prepared), None, None),
            ("exact_duplicate_rows_removed", len(raw_rows) - len(prepared), None, None),
            ("unique_timestamps_after_dedup", len(timestamps), None, None),
            ("expected_four_hour_slots", len(expected), None, None),
            ("missing_four_hour_slots", len(set(expected) - timestamp_set), json.dumps(sorted(set(expected) - timestamp_set)), None),
            ("full_panel_expected_rows", expected_panel, None, json.dumps({"cities": len(cities), "zones": len(zones), "timestamps": len(timestamps)})),
            ("full_panel_known_observed_keys", len(known_keys), None, None),
            ("full_panel_known_coverage_pct", 100 * len(known_keys) / expected_panel if expected_panel else None, None, None),
            ("one_row_per_timestamp_after_dedup", float(len(timestamps) == len(prepared)), None, None),
        ]
        con.executemany("INSERT INTO coverage_audit VALUES (?,?,?,?)", coverage)
        for dimension, values in (
            ("city", [row["city"] for row in prepared]),
            ("zone_canonical", [row["zone_clean"] or "[UNKNOWN]" for row in prepared]),
            ("hour", [str(row["hour"]) for row in prepared]),
            ("month", [str(row["month"]) for row in prepared]),
            ("weekday", [str(row["weekday"]) for row in prepared]),
        ):
            con.executemany("INSERT INTO dimension_count VALUES (?,?,?)", [(dimension, str(member), count) for member, count in Counter(values).items()])

        con.execute("INSERT OR REPLACE INTO data_contract VALUES (?,?,?,?,?)", (
            "canonical_authority", "Architecture", "canonical_cleaned is the authoritative raw/cleaned analytical layer; urbanpulse_clean is a compatibility mirror for legacy scripts.", "COMPLETED_STAGE2", "Use canonical_cleaned for new work.",
        ))
        con.execute("INSERT OR REPLACE INTO data_contract VALUES (?,?,?,?,?)", (
            "stage2_refresh_source", "Refresh", "The Stage 2 refresh reads the workbook table-shaped source and deterministically rebuilds the raw and canonical layer tables.", "COMPLETED_STAGE2", "Run Stage 3 sensitivity refresh after any new source data.",
        ))
        con.execute("INSERT OR REPLACE INTO analysis_run VALUES (?,?,?,?)", (
            "stage2_refresh_layers", "Stage 2 raw-to-canonical refresh completed without imputation.", None,
            json.dumps({"input": str(input_path), "raw_rows": len(raw_rows), "canonical_rows": len(prepared), "imputed_primary_values": 0}),
        ))
        con.commit()
    except Exception:
        con.rollback()
        raise

    return {
        "raw_rows": len(raw_rows),
        "canonical_rows": len(prepared),
        "duplicate_rows_removed": len(raw_rows) - len(prepared),
        "primary_observed_rows": con.execute("SELECT COUNT(*) FROM v_primary_observed").fetchone()[0],
        "change_log_rows": con.execute("SELECT COUNT(*) FROM change_log").fetchone()[0],
        "quality_flag_rows": con.execute("SELECT COUNT(*) FROM quality_flag").fetchone()[0],
        "imputed_flags": con.execute("SELECT COUNT(*) FROM quality_flag WHERE flag_type='imputed'").fetchone()[0],
        "integrity": con.execute("PRAGMA integrity_check").fetchone()[0],
        "quality_flag_summary": con.execute("SELECT flag_type,field_name,flag_count FROM quality_flag_summary ORDER BY flag_type,field_name").fetchall(),
    }


def write_report(output_dir: Path, input_path: Path, db_path: Path, result: dict):
    output_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# UrbanPulse Stage 2 Refreshable Data Layers",
        "",
        "This report is generated from the live Stage 2 raw-to-canonical refresh run.",
        "",
        f"- Input workbook: `{input_path}`",
        f"- Input SHA-256: `{sha256_file(input_path)}`",
        f"- Database: `{db_path}`",
        f"- Raw rows: **{result['raw_rows']:,}**",
        f"- Canonical rows: **{result['canonical_rows']:,}**",
        f"- Exact duplicate rows excluded from canonical: **{result['duplicate_rows_removed']:,}**",
        f"- Primary observed rows: **{result['primary_observed_rows']:,}**",
        f"- Change-log entries: **{result['change_log_rows']:,}**",
        f"- Stage 2 quality flags: **{result['quality_flag_rows']:,}**",
        f"- Imputed values in Stage 2 canonical layer: **{result['imputed_flags']:,}**",
        f"- SQLite integrity: **{result['integrity']}**",
        "",
        "`canonical_cleaned` is the authoritative raw/cleaned layer. `urbanpulse_clean` is retained as a compatibility mirror for legacy scripts. Imputation is not performed in Stage 2.",
        "",
        "## Quality flags",
        "",
        "| Flag type | Field | Count |",
        "|---|---|---:|",
    ]
    lines.extend(f"| {kind} | {field} | {count:,} |" for kind, field, count in result["quality_flag_summary"])
    (output_dir / "urbanpulse_data_layers.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=project_root / "02_final_outputs" / "urbanpulse_phase4_working.xlsx")
    parser.add_argument("--db", type=Path, default=project_root / "02_final_outputs" / "urbanpulse_rdbms.sqlite")
    parser.add_argument("--output-dir", type=Path, default=project_root / "02_final_outputs")
    args = parser.parse_args()
    con = sqlite3.connect(args.db)
    ensure_schema(con)
    result = refresh_layers(con, args.input)
    write_report(args.output_dir, args.input, args.db, result)
    con.close()
    print(json.dumps(result, indent=2, default=list))


if __name__ == "__main__":
    main()
