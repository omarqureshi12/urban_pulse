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

CREATE VIEW IF NOT EXISTS v_primary_zone_complete AS
SELECT * FROM v_primary_observed WHERE cleaned_zone IS NOT NULL;
