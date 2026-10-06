import json
import sqlite3

from project_config import DB_PATH


VIEW_SQL = """
CREATE VIEW IF NOT EXISTS v_primary_zone_complete AS
SELECT *
FROM v_primary_observed
WHERE cleaned_zone IS NOT NULL
"""


def main():
    con = sqlite3.connect(DB_PATH)
    con.executescript(VIEW_SQL)
    primary_rows = con.execute("SELECT COUNT(*) FROM v_primary_observed").fetchone()[0]
    zone_complete_rows = con.execute("SELECT COUNT(*) FROM v_primary_zone_complete").fetchone()[0]
    unknown_zone_rows = con.execute("SELECT COUNT(*) FROM v_primary_observed WHERE cleaned_zone IS NULL").fetchone()[0]
    con.execute(
        "UPDATE data_contract SET current_status=?, action_required=? WHERE contract_key='data_layers'",
        (
            "COMPLETED_STEP_3_ZONE_COMPLETE_PRIMARY_POLICY",
            "Use v_primary_zone_complete for all primary analyses requiring zone; retain v_primary_observed for analyses that do not require zone.",
        ),
    )
    con.execute(
        "INSERT OR REPLACE INTO analysis_run VALUES (?,?,?,?)",
        (
            "stage3_zone_complete_primary",
            "Zone-complete primary view created without deleting raw or canonical records.",
            float(zone_complete_rows),
            json.dumps({
                "primary_observed_rows": primary_rows,
                "zone_complete_primary_rows": zone_complete_rows,
                "unknown_zone_rows_excluded_from_zone_analyses": unknown_zone_rows,
                "imputation_used": False,
            }),
        ),
    )
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.commit()
    con.close()
    print(json.dumps({
        "view": "v_primary_zone_complete",
        "primary_observed_rows": primary_rows,
        "zone_complete_primary_rows": zone_complete_rows,
        "unknown_zone_rows_excluded_from_zone_analyses": unknown_zone_rows,
        "integrity": integrity,
    }, indent=2))


if __name__ == "__main__":
    main()
