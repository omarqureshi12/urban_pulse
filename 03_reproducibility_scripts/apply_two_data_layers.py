import json
import os
import sqlite3

from project_config import DB_PATH, OUTPUT_DIR

SCHEMA_PATH = OUTPUT_DIR / "urbanpulse_schema.sql"
CONTRACT_PATH = OUTPUT_DIR / "urbanpulse_data_contract.md"
REPORT_PATH = OUTPUT_DIR / "urbanpulse_data_layers.md"
MIGRATION_PATH = OUTPUT_DIR / "urbanpulse_data_layers_migration.sql"

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


def q(value):
    return "NULL" if value is None else "'" + str(value).replace("'", "''") + "'"


def main():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript("""
    CREATE TABLE IF NOT EXISTS canonical_cleaned (
        record_id TEXT PRIMARY KEY,
        source_row_number INTEGER NOT NULL,
        raw_city TEXT,
        cleaned_city TEXT,
        raw_zone TEXT,
        cleaned_zone TEXT,
        raw_timestamp TEXT,
        cleaned_timestamp_iso TEXT,
        observation_date TEXT,
        hour INTEGER,
        weekday INTEGER,
        month INTEGER,
        raw_traffic_volume INTEGER,
        cleaned_traffic_volume INTEGER,
        raw_avg_speed_kmph REAL,
        cleaned_avg_speed_kmph REAL,
        raw_public_transport_usage INTEGER,
        cleaned_public_transport_usage INTEGER,
        raw_parking_occupancy_pct REAL,
        cleaned_parking_occupancy_pct REAL,
        raw_road_incidents INTEGER,
        cleaned_road_incidents INTEGER,
        raw_waterlogging_reports INTEGER,
        cleaned_waterlogging_reports INTEGER,
        raw_power_outage_minutes REAL,
        cleaned_power_outage_minutes REAL,
        raw_citizen_complaints INTEGER,
        cleaned_citizen_complaints INTEGER,
        raw_temperature_c REAL,
        cleaned_temperature_c REAL,
        row_quality_status TEXT NOT NULL,
        primary_analysis_eligible INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS quality_flag (
        flag_id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_id TEXT NOT NULL,
        source_row_number INTEGER NOT NULL,
        field_name TEXT NOT NULL,
        flag_type TEXT NOT NULL CHECK (flag_type IN ('missing','imputed','corrected','outlier','unknown')),
        raw_value TEXT,
        cleaned_value TEXT,
        reason TEXT NOT NULL,
        primary_analysis_effect TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS change_log (
        change_id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_id TEXT,
        source_row_number INTEGER NOT NULL,
        field_name TEXT NOT NULL,
        raw_value TEXT,
        cleaned_value TEXT,
        change_type TEXT NOT NULL,
        method TEXT NOT NULL,
        primary_analysis_effect TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS quality_flag_summary (
        flag_type TEXT NOT NULL,
        field_name TEXT NOT NULL,
        flag_count INTEGER NOT NULL,
        PRIMARY KEY (flag_type, field_name)
    );

    CREATE VIEW IF NOT EXISTS v_primary_observed AS
    SELECT * FROM canonical_cleaned WHERE primary_analysis_eligible=1;

    CREATE VIEW IF NOT EXISTS v_primary_zone_complete AS
    SELECT * FROM v_primary_observed WHERE cleaned_zone IS NOT NULL;
    """)
    con.execute("DELETE FROM canonical_cleaned")
    con.execute("DELETE FROM quality_flag")
    con.execute("DELETE FROM change_log")
    con.execute("DELETE FROM quality_flag_summary")

    rows = con.execute("""
        SELECT record_id,source_row_number,city,zone_raw,zone_canonical,timestamp_text,timestamp_iso,observation_date,hour,weekday,month,
               traffic_volume,avg_speed_kmph,public_transport_usage,parking_occupancy_pct,road_incidents,waterlogging_reports,
               power_outage_minutes,citizen_complaints,temperature_c,quality_status
        FROM urbanpulse_clean ORDER BY source_row_number
    """).fetchall()
    clean_insert = []
    flag_insert = []
    change_insert = []
    for row in rows:
        (record_id, source_row, city, zone_raw, zone_clean, ts_raw, ts_iso, obs_date, hour, weekday, month,
         traffic, speed, transit, parking, incidents, waterlogging, outage, complaints, temperature, prior_status) = row
        values = {
            "traffic_volume": traffic,
            "avg_speed_kmph": speed,
            "public_transport_usage": transit,
            "parking_occupancy_pct": parking,
            "road_incidents": incidents,
            "waterlogging_reports": waterlogging,
            "power_outage_minutes": outage,
            "citizen_complaints": complaints,
            "temperature_c": temperature,
        }
        flags = []
        if zone_raw in (None, ""):
            flags += [("zone", "missing", zone_raw, zone_clean, "Zone is blank in the source.", "Retained as NULL in primary analysis."),
                      ("zone", "unknown", zone_raw, zone_clean, "Zone cannot be inferred from the source.", "Retained as NULL in primary analysis.")]
        elif zone_raw != zone_clean:
            flags.append(("zone", "corrected", zone_raw, zone_clean, "Case normalized to the controlled vocabulary.", "Normalization only; retained in primary analysis."))
            change_insert.append((record_id, source_row, "zone", zone_raw, zone_clean, "canonicalized", "casefold then controlled-vocabulary capitalization", "included after normalization"))
        for metric, value in values.items():
            if value is None:
                flags.append((metric, "missing", value, value, "Source value is blank.", "Excluded for that metric; no imputation in primary analysis."))
        if speed is not None and speed < 0:
            flags.append(("avg_speed_kmph", "outlier", speed, speed, "Negative speed is outside the operational domain.", "Excluded from primary speed analysis."))
        if speed is not None and speed > 120:
            flags.append(("avg_speed_kmph", "outlier", speed, speed, "Speed exceeds the conservative domain threshold.", "Excluded from primary speed analysis."))
        if parking is not None and parking > 100:
            flags.append(("parking_occupancy_pct", "outlier", parking, parking, "Parking exceeds nominal 100% occupancy.", "Retained and flagged; semantics require confirmation."))
        if temperature is not None and temperature >= 45:
            flags.append(("temperature_c", "outlier", temperature, temperature, "Temperature is at or above 45 C.", "Retained and flagged; sensor context required."))
        if outage is not None and outage > 60:
            flags.append(("power_outage_minutes", "outlier", outage, outage, "Outage exceeds 60 minutes.", "Retained and flagged; window definition required."))
        for field, flag_type, raw_value, clean_value, reason, effect in flags:
            flag_insert.append((record_id, source_row, field, flag_type, None if raw_value is None else str(raw_value), None if clean_value is None else str(clean_value), reason, effect))
        primary_eligible = int(all(values[m] is not None for m in METRICS) and speed is not None and 0 <= speed <= 120)
        row_status = "flagged" if flags else "observed"
        if primary_eligible and not flags:
            row_status = "observed"
        clean_insert.append((
            record_id, source_row, city, city, zone_raw, zone_clean, ts_raw, ts_iso, obs_date, hour, weekday, month,
            traffic, traffic, speed, speed, transit, transit, parking, parking, incidents, incidents, waterlogging, waterlogging,
            outage, outage, complaints, complaints, temperature, temperature, row_status, primary_eligible
        ))

    # Exact duplicate rows are represented in the separate change log, not in the canonical layer.
    duplicate_rows = con.execute("""
        SELECT d.source_row_number,d.record_id,d.kept_source_row_number
        FROM deduplication_log d WHERE d.action='removed_exact_duplicate'
    """).fetchall()
    for source_row, record_id, kept_row in duplicate_rows:
        change_insert.append((record_id, source_row, "__row__", record_id, None, "deduplicated", "exact row match; retained first source occurrence", "row excluded from canonical primary layer"))

    con.executemany("INSERT INTO canonical_cleaned VALUES (" + ",".join(["?"] * 32) + ")", clean_insert)
    con.executemany("""INSERT INTO quality_flag (record_id,source_row_number,field_name,flag_type,raw_value,cleaned_value,reason,primary_analysis_effect) VALUES (?,?,?,?,?,?,?,?)""", flag_insert)
    con.executemany("""INSERT INTO change_log (record_id,source_row_number,field_name,raw_value,cleaned_value,change_type,method,primary_analysis_effect) VALUES (?,?,?,?,?,?,?,?)""", change_insert)
    con.execute("""
        INSERT INTO quality_flag_summary
        SELECT flag_type,field_name,COUNT(*) FROM quality_flag GROUP BY flag_type,field_name
    """)
    con.execute("INSERT OR REPLACE INTO data_contract VALUES (?,?,?,?,?)", (
        "data_layers",
        "Architecture",
        "raw_urbanpulse is immutable; canonical_cleaned stores raw and cleaned values side by side; quality_flag and change_log provide normalized audit trails.",
        "COMPLETED_STEP_2",
        "Use v_primary_observed for primary statistics; use sensitivity tables for imputation scenarios only.",
    ))
    con.execute("INSERT OR REPLACE INTO data_contract VALUES (?,?,?,?,?)", (
        "imputation_policy",
        "Analysis",
        "No imputed values are present in canonical_cleaned or v_primary_observed. Imputation exists only in the sensitivity analysis scenarios.",
        "PRIMARY_OBSERVED_ONLY",
        "Do not promote sensitivity imputations into the primary analysis layer.",
    ))
    con.execute("INSERT OR REPLACE INTO analysis_run VALUES (?,?,?,?)", (
        "step2_data_layers",
        "Two-layer raw/canonical RDBMS design applied with normalized flags and separate change log.",
        None,
        '{"primary_imputation":false,"sensitivity_imputation":true,"quality_flag_types":["missing","imputed","corrected","outlier","unknown"]}',
    ))
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.commit()

    counts = {
        "raw_rows": con.execute("SELECT COUNT(*) FROM raw_urbanpulse").fetchone()[0],
        "canonical_rows": con.execute("SELECT COUNT(*) FROM canonical_cleaned").fetchone()[0],
        "primary_observed_rows": con.execute("SELECT COUNT(*) FROM v_primary_observed").fetchone()[0],
        "change_log_rows": con.execute("SELECT COUNT(*) FROM change_log").fetchone()[0],
        "quality_flag_rows": con.execute("SELECT COUNT(*) FROM quality_flag").fetchone()[0],
        "imputed_flags": con.execute("SELECT COUNT(*) FROM quality_flag WHERE flag_type='imputed'").fetchone()[0],
        "corrected_flags": con.execute("SELECT COUNT(*) FROM quality_flag WHERE flag_type='corrected'").fetchone()[0],
        "integrity": integrity,
    }
    flag_counts = con.execute("SELECT flag_type,field_name,flag_count FROM quality_flag_summary ORDER BY flag_type,field_name").fetchall()
    con.close()

    migration_sql = """-- UrbanPulse two-layer data model migration\n-- Apply after urbanpulse_schema.sql.\n\nCREATE TABLE IF NOT EXISTS canonical_cleaned (\n    record_id TEXT PRIMARY KEY, source_row_number INTEGER NOT NULL,\n    raw_city TEXT, cleaned_city TEXT, raw_zone TEXT, cleaned_zone TEXT,\n    raw_timestamp TEXT, cleaned_timestamp_iso TEXT, observation_date TEXT, hour INTEGER, weekday INTEGER, month INTEGER,\n    raw_traffic_volume INTEGER, cleaned_traffic_volume INTEGER, raw_avg_speed_kmph REAL, cleaned_avg_speed_kmph REAL,\n    raw_public_transport_usage INTEGER, cleaned_public_transport_usage INTEGER, raw_parking_occupancy_pct REAL, cleaned_parking_occupancy_pct REAL,\n    raw_road_incidents INTEGER, cleaned_road_incidents INTEGER, raw_waterlogging_reports INTEGER, cleaned_waterlogging_reports INTEGER,\n    raw_power_outage_minutes REAL, cleaned_power_outage_minutes REAL, raw_citizen_complaints INTEGER, cleaned_citizen_complaints INTEGER,\n    raw_temperature_c REAL, cleaned_temperature_c REAL, row_quality_status TEXT NOT NULL, primary_analysis_eligible INTEGER NOT NULL\n);\n\nCREATE TABLE IF NOT EXISTS quality_flag (\n    flag_id INTEGER PRIMARY KEY AUTOINCREMENT, record_id TEXT NOT NULL, source_row_number INTEGER NOT NULL, field_name TEXT NOT NULL,\n    flag_type TEXT NOT NULL CHECK (flag_type IN ('missing','imputed','corrected','outlier','unknown')),\n    raw_value TEXT, cleaned_value TEXT, reason TEXT NOT NULL, primary_analysis_effect TEXT NOT NULL\n);\n\nCREATE TABLE IF NOT EXISTS change_log (\n    change_id INTEGER PRIMARY KEY AUTOINCREMENT, record_id TEXT, source_row_number INTEGER NOT NULL, field_name TEXT NOT NULL,\n    raw_value TEXT, cleaned_value TEXT, change_type TEXT NOT NULL, method TEXT NOT NULL, primary_analysis_effect TEXT NOT NULL\n);\n\nCREATE TABLE IF NOT EXISTS quality_flag_summary (\n    flag_type TEXT NOT NULL, field_name TEXT NOT NULL, flag_count INTEGER NOT NULL, PRIMARY KEY (flag_type, field_name)\n);\n\nCREATE VIEW IF NOT EXISTS v_primary_observed AS SELECT * FROM canonical_cleaned WHERE primary_analysis_eligible=1;\n"""
    migration_sql += "\nCREATE VIEW IF NOT EXISTS v_primary_zone_complete AS SELECT * FROM v_primary_observed WHERE cleaned_zone IS NOT NULL;\n"
    with open(MIGRATION_PATH, "w", encoding="utf-8") as f:
        f.write(migration_sql)
    with open(SCHEMA_PATH, "a", encoding="utf-8") as f:
        f.write("\n\n" + migration_sql)

    text = open(CONTRACT_PATH, encoding="utf-8").read()
    section = """
## Two-layer data model

- `raw_urbanpulse` is immutable and preserves the workbook values.
- `canonical_cleaned` stores raw and cleaned values side by side.
- `quality_flag` stores normalized `missing`, `imputed`, `corrected`, `outlier`, and `unknown` flags.
- `change_log` records actual canonicalization and de-duplication actions.
- `v_primary_observed` is observed-only and contains no imputed values.
- `v_primary_zone_complete` is the observed-only subset for primary analyses requiring a known zone.
- Imputation is confined to the Stage 3 sensitivity tables.
"""
    if "## Two-layer data model" not in text:
        text += section
    with open(CONTRACT_PATH, "w", encoding="utf-8") as f:
        f.write(text)

    report_lines = [
        "# UrbanPulse Two-Layer Data Model",
        "",
        "Step 2 now uses an auditable two-layer RDBMS design. The raw source is immutable. The canonical layer keeps raw and cleaned values side by side. Primary analysis uses observed values only.",
        "",
        "## Layer status",
        "",
        f"- Raw rows: **{counts['raw_rows']:,}**",
        f"- Canonical cleaned rows: **{counts['canonical_rows']:,}**",
        f"- Primary observed rows: **{counts['primary_observed_rows']:,}**",
        f"- Change-log entries: **{counts['change_log_rows']:,}**",
        f"- Quality-flag entries: **{counts['quality_flag_rows']:,}**",
        f"- Imputed primary values: **{counts['imputed_flags']:,}**",
        f"- Corrected/normalized flags: **{counts['corrected_flags']:,}**",
        f"- SQLite integrity: **{counts['integrity']}**",
        "",
        "## Quality flags",
        "",
        "| Flag type | Field | Count |",
        "|---|---|---:|",
    ]
    report_lines.extend(f"| {flag_type} | {field} | {count:,} |" for flag_type, field, count in flag_counts)
    report_lines += [
        "",
        "## Primary analysis rule",
        "",
        "`v_primary_observed` excludes missing metric values and invalid speeds and contains no imputed values. Use `v_primary_zone_complete` for primary analyses requiring a known zone. Imputation is permitted only in the sensitivity tables and cannot be promoted into the primary analytical layer without a separate decision.",
        "",
        "## RDBMS objects",
        "",
        "- `raw_urbanpulse`",
        "- `canonical_cleaned`",
        "- `quality_flag`",
        "- `change_log`",
        "- `quality_flag_summary`",
        "- `v_primary_observed`",
        "- `v_primary_zone_complete`",
    ]
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")
    print(json.dumps({"report": str(REPORT_PATH), "migration": str(MIGRATION_PATH), **counts}, indent=2))


if __name__ == "__main__":
    main()
