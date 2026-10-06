import json
import sqlite3

from project_config import DB_PATH, OUTPUT_DIR

REPORT_PATH = OUTPUT_DIR / "urbanpulse_stage4_quality_decisions.md"

IMD_CLIMATE_URL = "https://mausam.imd.gov.in/responsive/climate_services.php"
IMD_CURRENT_URL = "https://mausam.imd.gov.in/imd_latest/contents/current_weather.php"


def main():
    con = sqlite3.connect(DB_PATH)
    con.executescript("""
    CREATE TABLE IF NOT EXISTS quality_decision (
        decision_key TEXT PRIMARY KEY,
        issue_type TEXT NOT NULL,
        field_name TEXT NOT NULL,
        observed_count INTEGER NOT NULL,
        decision_class TEXT NOT NULL CHECK (decision_class IN ('confirmed_error','valid_extreme','unknown')),
        disposition TEXT NOT NULL,
        primary_analysis_treatment TEXT NOT NULL,
        source_confirmation_status TEXT NOT NULL,
        rationale TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS source_confirmation (
        decision_key TEXT NOT NULL,
        source_name TEXT NOT NULL,
        source_url TEXT NOT NULL,
        source_role TEXT NOT NULL,
        evidence_summary TEXT NOT NULL,
        confirmation_status TEXT NOT NULL,
        PRIMARY KEY (decision_key, source_url)
    );
    """)
    con.execute("DELETE FROM quality_decision")
    con.execute("DELETE FROM source_confirmation")

    counts = {
        "exact_duplicate_rows": con.execute("SELECT COUNT(*) FROM deduplication_log WHERE action='removed_exact_duplicate'").fetchone()[0],
        "zone_case_variant": con.execute("SELECT COUNT(*) FROM data_quality_issue WHERE issue_type='case_variant' AND column_name='zone'").fetchone()[0],
        "zone_missing": con.execute("SELECT COUNT(*) FROM data_quality_issue WHERE issue_type='missing' AND column_name='zone'").fetchone()[0],
        "traffic_missing": con.execute("SELECT COUNT(*) FROM data_quality_issue WHERE issue_type='missing' AND column_name='traffic_volume'").fetchone()[0],
        "speed_missing": con.execute("SELECT COUNT(*) FROM data_quality_issue WHERE issue_type='missing' AND column_name='avg_speed_kmph'").fetchone()[0],
        "temperature_missing": con.execute("SELECT COUNT(*) FROM data_quality_issue WHERE issue_type='missing' AND column_name='temperature_c'").fetchone()[0],
        "speed_negative": con.execute("SELECT COUNT(*) FROM data_quality_issue WHERE issue_type='negative_value' AND column_name='avg_speed_kmph'").fetchone()[0],
        "speed_extreme": con.execute("SELECT COUNT(*) FROM data_quality_issue WHERE issue_type='extreme_value' AND column_name='avg_speed_kmph'").fetchone()[0],
        "parking_over_100": con.execute("SELECT COUNT(*) FROM data_quality_issue WHERE issue_type='above_100' AND column_name='parking_occupancy_pct'").fetchone()[0],
        "temperature_high": con.execute("SELECT COUNT(*) FROM data_quality_issue WHERE issue_type='high_value' AND column_name='temperature_c'").fetchone()[0],
        "outage_over_60": con.execute("SELECT COUNT(*) FROM data_quality_issue WHERE issue_type='above_60' AND column_name='power_outage_minutes'").fetchone()[0],
    }

    decisions = [
        ("duplicates", "exact_duplicate", "__row__", counts["exact_duplicate_rows"], "confirmed_error", "Exclude exact duplicate rows from canonical_cleaned; preserve all raw rows and log the removal.", "Excluded from canonical primary layer.", "confirmed_by_internal_key_check", "Exact row duplicates are objectively confirmed within the source workbook."),
        ("zone_case", "case_variant", "zone", counts["zone_case_variant"], "confirmed_error", "Canonicalize case only in canonical_cleaned; preserve raw zone text.", "Included after vocabulary normalization.", "confirmed_by_controlled_vocabulary", "Central/central and North/NORTH are the same semantic labels under the declared five-zone vocabulary."),
        ("zone_missing", "missing", "zone", counts["zone_missing"], "unknown", "Preserve NULL and flag unknown; do not infer a zone.", "Excluded from zone-specific analysis.", "not_confirmed", "The source contains no evidence to recover the missing zone."),
        ("traffic_missing", "missing", "traffic_volume", counts["traffic_missing"], "unknown", "Preserve NULL; do not impute in the primary layer.", "Excluded for traffic analysis.", "not_confirmed", "Missingness cannot be repaired from the source row alone."),
        ("speed_missing", "missing", "avg_speed_kmph", counts["speed_missing"], "unknown", "Preserve NULL; do not impute in the primary layer.", "Excluded for speed analysis.", "not_confirmed", "Missingness cannot be repaired from the source row alone."),
        ("temperature_missing", "missing", "temperature_c", counts["temperature_missing"], "unknown", "Preserve NULL; do not impute in the primary layer.", "Excluded for temperature analysis.", "not_confirmed", "Missingness cannot be repaired from the source row alone."),
        ("speed_negative", "negative_value", "avg_speed_kmph", counts["speed_negative"], "unknown", "Retain raw -10 values, flag, and do not replace them with +10.", "Excluded from primary speed analysis.", "not_confirmed", "The source does not establish that -10 is a sign error or a sentinel code."),
        ("speed_extreme", "extreme_value", "avg_speed_kmph", counts["speed_extreme"], "unknown", "Retain 150/200 values and flag them.", "Excluded from primary speed analysis pending source confirmation.", "not_confirmed", "These values are outside the conservative speed domain but could reflect a unit or source error."),
        ("parking_over_100", "above_100", "parking_occupancy_pct", counts["parking_over_100"], "unknown", "Retain and flag; do not cap at 100.", "Retained in primary metrics but excluded from semantic interpretation until capacity is confirmed.", "owner_confirmation_required", "Occupancy can exceed nominal capacity, but the denominator is undocumented."),
        ("temperature_high", "high_value", "temperature_c", counts["temperature_high"], "unknown", "Preserve the recorded temperature and flag it. Do not replace it without an exact city-date station source match.", "Excluded only where the primary analysis rule already excludes missing values; otherwise retained as flagged observed data.", "historical_source_match_pending", "IMD provides authoritative temperature products and historical-data request routes, but the public pages do not directly confirm each flagged 2026 row."),
        ("outage_over_60", "above_60", "power_outage_minutes", counts["outage_over_60"], "valid_extreme", "Retain and flag.", "Retained in primary analysis with an explicit quality flag.", "window_assumption_pending", "A value above 60 minutes can occur within a four-hour observation window; the source window definition should still be confirmed."),
    ]
    con.executemany("INSERT INTO quality_decision VALUES (?,?,?,?,?,?,?,?,?)", decisions)
    con.executemany("INSERT INTO source_confirmation VALUES (?,?,?,?,?,?)", [
        ("temperature_high", "India Meteorological Department Climate Services", IMD_CLIMATE_URL, "authoritative temperature products and historical-data route", "The page lists daily temperature maps and directs historical-data queries to IMD contacts; it does not expose a row-level match for these 27 records.", "not_confirmed"),
        ("temperature_high", "India Meteorological Department City Weather Reports", IMD_CURRENT_URL, "station-level recorded temperature and departure fields", "The city-report service exposes recorded minimum/maximum temperatures and departures from normal for named stations; it does not provide the exact historical source row for each flagged record through the public page.", "not_confirmed"),
    ])
    con.execute("INSERT OR REPLACE INTO data_contract VALUES (?,?,?,?,?)", (
        "stage4_quality_decisions",
        "Quality",
        "Each issue is classified as confirmed_error, valid_extreme, or unknown. Raw values are never overwritten by this stage.",
        "COMPLETED_STAGE_4_WITH_TEMPERATURE_SOURCE_PENDING",
        "Obtain exact city-date-station historical records before replacing any high-temperature value.",
    ))
    con.execute("INSERT OR REPLACE INTO analysis_run VALUES (?,?,?,?)", (
        "stage4_quality_decisions",
        "Stage 4 completed: quality issues classified without overwriting raw values; temperature source confirmation remains pending.",
        None,
        json.dumps({"stage": 4, "temperature_replacements": 0, "negative_speed_replacements": 0, "external_source_confirmation": "pending"}),
    ))
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.commit()
    decision_rows = con.execute("SELECT decision_key,decision_class,observed_count,source_confirmation_status,disposition FROM quality_decision ORDER BY decision_key").fetchall()
    con.close()

    lines = [
        "# UrbanPulse Stage 4: Data-Quality Decisions",
        "",
        "Stage 4 classifies issues as confirmed errors, valid extremes, or unknowns. It does not overwrite the immutable raw layer.",
        "",
        "## Decisions",
        "",
        "| Issue | Class | Count | Source status | Treatment |",
        "|---|---|---:|---|---|",
    ]
    for key, decision_class, count, source_status, disposition in decision_rows:
        lines.append(f"| {key} | {decision_class} | {count:,} | {source_status} | {disposition} |")
    lines += [
        "",
        "## Explicit non-corrections",
        "",
        "- The five `-10` speed values were not changed to `+10`.",
        "- No high-temperature value was replaced.",
        "- No primary-layer imputation was performed.",
        "- Numeric values remain available in raw and canonical side-by-side columns.",
        "",
        "## Temperature source confirmation",
        "",
        f"IMD Climate Services: {IMD_CLIMATE_URL}",
        f"IMD City Weather Reports: {IMD_CURRENT_URL}",
        "",
        "These official services establish the appropriate source family, but the public pages do not provide an exact historical city-date-station match for the 27 flagged records. Therefore the temperatures remain unknown and unchanged. A correction would require the matching historical station record and a logged source reference for each affected row.",
        "",
        f"SQLite integrity check: `{integrity}`.",
    ]
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps({"report": REPORT_PATH, "decisions": len(decisions), "temperature_replacements": 0, "integrity": integrity}, indent=2))


if __name__ == "__main__":
    main()
