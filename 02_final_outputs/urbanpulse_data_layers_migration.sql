-- UrbanPulse two-layer data model migration
-- Apply after urbanpulse_schema.sql.

CREATE TABLE IF NOT EXISTS canonical_cleaned (
    record_id TEXT PRIMARY KEY, source_row_number INTEGER NOT NULL,
    raw_city TEXT, cleaned_city TEXT, raw_zone TEXT, cleaned_zone TEXT,
    raw_timestamp TEXT, cleaned_timestamp_iso TEXT, observation_date TEXT, hour INTEGER, weekday INTEGER, month INTEGER,
    raw_traffic_volume INTEGER, cleaned_traffic_volume INTEGER, raw_avg_speed_kmph REAL, cleaned_avg_speed_kmph REAL,
    raw_public_transport_usage INTEGER, cleaned_public_transport_usage INTEGER, raw_parking_occupancy_pct REAL, cleaned_parking_occupancy_pct REAL,
    raw_road_incidents INTEGER, cleaned_road_incidents INTEGER, raw_waterlogging_reports INTEGER, cleaned_waterlogging_reports INTEGER,
    raw_power_outage_minutes REAL, cleaned_power_outage_minutes REAL, raw_citizen_complaints INTEGER, cleaned_citizen_complaints INTEGER,
    raw_temperature_c REAL, cleaned_temperature_c REAL, row_quality_status TEXT NOT NULL, primary_analysis_eligible INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS quality_flag (
    flag_id INTEGER PRIMARY KEY AUTOINCREMENT, record_id TEXT NOT NULL, source_row_number INTEGER NOT NULL, field_name TEXT NOT NULL,
    flag_type TEXT NOT NULL CHECK (flag_type IN ('missing','imputed','corrected','outlier','unknown')),
    raw_value TEXT, cleaned_value TEXT, reason TEXT NOT NULL, primary_analysis_effect TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS change_log (
    change_id INTEGER PRIMARY KEY AUTOINCREMENT, record_id TEXT, source_row_number INTEGER NOT NULL, field_name TEXT NOT NULL,
    raw_value TEXT, cleaned_value TEXT, change_type TEXT NOT NULL, method TEXT NOT NULL, primary_analysis_effect TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quality_flag_summary (
    flag_type TEXT NOT NULL, field_name TEXT NOT NULL, flag_count INTEGER NOT NULL, PRIMARY KEY (flag_type, field_name)
);

CREATE VIEW IF NOT EXISTS v_primary_observed AS SELECT * FROM canonical_cleaned WHERE primary_analysis_eligible=1;
CREATE VIEW IF NOT EXISTS v_primary_zone_complete AS SELECT * FROM v_primary_observed WHERE cleaned_zone IS NOT NULL;
