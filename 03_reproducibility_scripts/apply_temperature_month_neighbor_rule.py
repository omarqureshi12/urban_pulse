import csv
import json
import sqlite3
import subprocess
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from project_config import DB_PATH, OUTPUT_DIR

REPORT_PATH = OUTPUT_DIR / "urbanpulse_temperature_month_neighbor_validation.md"
CSV_PATH = OUTPUT_DIR / "urbanpulse_temperature_month_neighbor_validation.csv"
START_DATE = "20160101"
END_DATE = "20261001"
START_ISO = "2016-01-01"
END_ISO = "2026-10-01"
NEIGHBOR_TOLERANCE_C = 10.0
NASA_POWER_DOC_URL = "https://power.larc.nasa.gov/docs/services/api/temporal/daily/"

CITY_COORDS = {
    "Bengaluru": (12.9716, 77.5946),
    "Bhopal": (23.2599, 77.4126),
    "Delhi": (28.6139, 77.2090),
    "Indore": (22.7196, 75.8577),
    "Jaipur": (26.9124, 75.7873),
    "Nagpur": (21.1458, 79.0882),
    "Pune": (18.5204, 73.8567),
}


def fetch_monthly_envelopes(city, latitude, longitude):
    params = urllib.parse.urlencode(
        {
            "parameters": "T2M_MAX,T2M_MIN",
            "community": "AG",
            "longitude": longitude,
            "latitude": latitude,
            "start": START_DATE,
            "end": END_DATE,
            "format": "JSON",
            "time-standard": "LST",
        }
    )
    url = "https://power.larc.nasa.gov/api/temporal/daily/point?" + params
    payload = subprocess.check_output(
        ["curl", "-L", "--fail", "--silent", "--show-error", url],
        text=True,
    )
    data = json.loads(payload)["properties"]["parameter"]
    envelopes = {month: {"low": 999.0, "high": -999.0} for month in range(1, 13)}
    for date, raw_value in data["T2M_MIN"].items():
        value = float(raw_value)
        if value > -900:
            envelopes[int(date[4:6])]["low"] = min(envelopes[int(date[4:6])]["low"], value)
    for date, raw_value in data["T2M_MAX"].items():
        value = float(raw_value)
        if value > -900:
            envelopes[int(date[4:6])]["high"] = max(envelopes[int(date[4:6])]["high"], value)
    return url, envelopes


def main():
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    monthly_rows = []
    monthly_lookup = {}
    for city, (latitude, longitude) in CITY_COORDS.items():
        source_url, envelopes = fetch_monthly_envelopes(city, latitude, longitude)
        monthly_lookup[city] = envelopes
        for month, bounds in envelopes.items():
            monthly_rows.append((city, month, bounds["low"], bounds["high"], source_url, retrieved_at))

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS temperature_month_benchmark (
            city TEXT NOT NULL,
            month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
            benchmark_low_c REAL NOT NULL,
            benchmark_high_c REAL NOT NULL,
            source_name TEXT NOT NULL,
            source_url TEXT NOT NULL,
            retrieved_at_utc TEXT NOT NULL,
            PRIMARY KEY (city, month)
        );

        CREATE TABLE IF NOT EXISTS temperature_neighbor_validation (
            record_id TEXT PRIMARY KEY,
            source_row_number INTEGER NOT NULL,
            city TEXT,
            observation_date TEXT,
            observation_timestamp TEXT,
            temperature_c REAL,
            month INTEGER,
            month_benchmark_low_c REAL,
            month_benchmark_high_c REAL,
            month_plausibility TEXT NOT NULL CHECK (month_plausibility IN ('plausible','implausible','unknown')),
            previous_record_id TEXT,
            previous_timestamp TEXT,
            previous_temperature_c REAL,
            next_record_id TEXT,
            next_timestamp TEXT,
            next_temperature_c REAL,
            neighbor_status TEXT NOT NULL CHECK (neighbor_status IN ('consistent','inconsistent','insufficient','unknown')),
            final_decision TEXT NOT NULL CHECK (final_decision IN ('retain_unchanged','flag_for_review','probable_error','not_assessed')),
            rule_text TEXT NOT NULL,
            source_url TEXT,
            evaluated_at_utc TEXT NOT NULL
        );
        """
    )
    con.execute("DELETE FROM temperature_month_benchmark")
    con.execute("DELETE FROM temperature_neighbor_validation")
    con.executemany(
        """
        INSERT INTO temperature_month_benchmark
        (city, month, benchmark_low_c, benchmark_high_c, source_name, source_url, retrieved_at_utc)
        VALUES (?,?,?,?,?,?,?)
        """,
        [(city, month, bounds["low"], bounds["high"], "NASA POWER Daily API", monthly_rows[(list(CITY_COORDS).index(city) * 12) + month - 1][4], retrieved_at) for city, month, bounds in [(c, m, {"low": lo, "high": hi}) for c, m, lo, hi, _, _ in monthly_rows]],
    )

    records = con.execute(
        """
        SELECT record_id, source_row_number, cleaned_city AS city, observation_date,
               cleaned_timestamp_iso AS observation_timestamp, cleaned_temperature_c AS temperature_c
        FROM canonical_cleaned
        ORDER BY cleaned_city, cleaned_timestamp_iso
        """
    ).fetchall()
    by_city = {}
    for row in records:
        if row["temperature_c"] is not None:
            by_city.setdefault(row["city"], []).append(row)

    def nearest_neighbors(city, record_id):
        city_rows = by_city.get(city, [])
        index = next((i for i, item in enumerate(city_rows) if item["record_id"] == record_id), None)
        if index is None:
            return None, None
        previous = city_rows[index - 1] if index > 0 else None
        following = city_rows[index + 1] if index + 1 < len(city_rows) else None
        return previous, following

    validation_rows = []
    for row in records:
        city = row["city"]
        temperature = row["temperature_c"]
        previous, following = nearest_neighbors(city, row["record_id"])
        if temperature is None:
            month = int(row["observation_date"][5:7]) if row["observation_date"] else None
            bounds = monthly_lookup.get(city, {}).get(month) if month else None
            month_status = "unknown"
            neighbor_status = "unknown"
            final_decision = "not_assessed"
            low = high = source_url = None
        elif city not in monthly_lookup:
            month = int(row["observation_date"][5:7])
            bounds = None
            month_status = "unknown"
            neighbor_status = "unknown"
            final_decision = "not_assessed"
            low = high = source_url = None
        else:
            month = int(row["observation_date"][5:7])
            bounds = monthly_lookup[city][month]
            low, high = bounds["low"], bounds["high"]
            source_url = next(x[4] for x in monthly_rows if x[0] == city and x[1] == month)
            month_status = "plausible" if low <= temperature <= high else "implausible"
            if previous is None or following is None:
                neighbor_status = "insufficient"
            else:
                values = [previous["temperature_c"], following["temperature_c"], temperature]
                neighbor_status = "consistent" if max(values) - min(values) <= NEIGHBOR_TOLERANCE_C else "inconsistent"
            if month_status == "plausible" and neighbor_status == "consistent":
                final_decision = "retain_unchanged"
            elif month_status == "plausible" and neighbor_status == "inconsistent":
                final_decision = "flag_for_review"
            elif month_status == "implausible" and neighbor_status == "inconsistent":
                final_decision = "probable_error"
            else:
                final_decision = "not_assessed"
        validation_rows.append(
            (
                row["record_id"], row["source_row_number"], city, row["observation_date"], row["observation_timestamp"], temperature, month,
                low, high, month_status,
                previous["record_id"] if previous else None, previous["observation_timestamp"] if previous else None, previous["temperature_c"] if previous else None,
                following["record_id"] if following else None, following["observation_timestamp"] if following else None, following["temperature_c"] if following else None,
                neighbor_status, final_decision,
                "Month plausibility plus nearest same-city preceding/following temperature; neighboring spread threshold = 10 C.", source_url, retrieved_at,
            )
        )
    con.executemany(
        """
        INSERT INTO temperature_neighbor_validation VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        validation_rows,
    )

    # Add a separate quality flag for values classified as probable errors. Values are never changed.
    con.execute(
        """
        INSERT INTO quality_flag (record_id, source_row_number, field_name, flag_type, raw_value, cleaned_value, reason, primary_analysis_effect)
        SELECT v.record_id, v.source_row_number, 'temperature_c', 'outlier', CAST(v.temperature_c AS TEXT), CAST(v.temperature_c AS TEXT),
               'Temperature is implausible for its city-month and inconsistent with neighboring same-city observations.',
               'Preserved unchanged; exclude from primary temperature interpretation pending review.'
        FROM temperature_neighbor_validation v
        WHERE v.final_decision='probable_error'
          AND NOT EXISTS (
            SELECT 1 FROM quality_flag q WHERE q.record_id=v.record_id AND q.field_name='temperature_c'
              AND q.reason='Temperature is implausible for its city-month and inconsistent with neighboring same-city observations.'
          )
        """
    )
    con.execute("DELETE FROM quality_flag_summary")
    con.execute("INSERT INTO quality_flag_summary SELECT flag_type, field_name, COUNT(*) FROM quality_flag GROUP BY flag_type, field_name")
    con.execute(
        "INSERT OR REPLACE INTO data_contract VALUES (?,?,?,?,?)",
        (
            "temperature_month_neighbor_rule",
            "Quality",
            "Month plausible + neighboring same-city temperatures consistent = retain. Month plausible + neighbors inconsistent = review. Month implausible + neighbors inconsistent = probable error.",
            "COMPLETED_STAGE_4_MONTH_NEIGHBOR_VALIDATION",
            "No values are overwritten. Probable errors remain in raw/canonical layers and must be separately confirmed before any correction.",
        ),
    )
    decision_counts = dict(con.execute("SELECT final_decision, COUNT(*) FROM temperature_neighbor_validation GROUP BY final_decision").fetchall())
    month_counts = dict(con.execute("SELECT month_plausibility, COUNT(*) FROM temperature_neighbor_validation GROUP BY month_plausibility").fetchall())
    neighbor_counts = dict(con.execute("SELECT neighbor_status, COUNT(*) FROM temperature_neighbor_validation GROUP BY neighbor_status").fetchall())
    probable_city_counts = dict(con.execute("SELECT city, COUNT(*) FROM temperature_neighbor_validation WHERE final_decision='probable_error' GROUP BY city ORDER BY city").fetchall())
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.execute(
        "INSERT OR REPLACE INTO analysis_run VALUES (?,?,?,?)",
        (
            "temperature_month_neighbor_rule",
            "Temperature validation applied using city-month plausibility and neighboring same-city consistency; no values overwritten.",
            None,
            json.dumps({"month_period_start": START_ISO, "month_period_end": END_ISO, "neighbor_tolerance_c": NEIGHBOR_TOLERANCE_C, "decision_counts": decision_counts, "probable_error_city_counts": probable_city_counts}),
        ),
    )
    con.commit()
    con.close()

    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["record_id", "source_row_number", "city", "observation_date", "temperature_c", "month_benchmark_low_c", "month_benchmark_high_c", "month_plausibility", "previous_temperature_c", "next_temperature_c", "neighbor_status", "final_decision"])
        for row in validation_rows:
            writer.writerow([row[0], row[1], row[2], row[3], row[5], row[7], row[8], row[9], row[12], row[15], row[16], row[17]])

    lines = [
        "# UrbanPulse Temperature Month-and-Neighbor Validation",
        "",
        "## Rule applied",
        "",
        "- Month plausible and neighboring temperatures of the same city are consistent: retain unchanged.",
        "- Month plausible but neighboring temperatures are inconsistent: flag for review.",
        "- Month implausible and neighboring temperatures are inconsistent: classify as probable error, preserve the raw value, and do not correct automatically.",
        "",
        f"Month plausibility uses the historical NASA POWER daily envelope for the same city and calendar month over {START_ISO} through {END_ISO}.",
        f"Neighbor consistency uses the nearest preceding and following non-missing observation for the same city. The maximum spread among the target and both neighbors must be no more than {NEIGHBOR_TOLERANCE_C:.0f} °C.",
        "",
        "## Results",
        "",
        "| Final decision | Rows |",
        "|---|---:|",
    ]
    for key in ("retain_unchanged", "flag_for_review", "probable_error", "not_assessed"):
        lines.append(f"| {key} | {decision_counts.get(key, 0):,} |")
    lines += [
        "",
        "Month plausibility: " + ", ".join(f"{k} {v:,}" for k, v in sorted(month_counts.items())) + ".",
        "Neighbor status: " + ", ".join(f"{k} {v:,}" for k, v in sorted(neighbor_counts.items())) + ".",
        "Probable-error counts by city: " + (", ".join(f"{city} {count}" for city, count in probable_city_counts.items()) if probable_city_counts else "none") + ".",
        "",
        "## Data-preservation statement",
        "",
        "No raw or canonical temperature was overwritten. Probable errors are classifications only. Any future correction must be supported by a separate source confirmation and a separate change-log entry.",
        "",
        f"NASA POWER Daily API: {NASA_POWER_DOC_URL}",
        f"SQLite integrity check: `{integrity}`.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(REPORT_PATH), "csv": str(CSV_PATH), "decision_counts": decision_counts, "probable_city_counts": probable_city_counts, "integrity": integrity, "replacements": 0}, indent=2))


if __name__ == "__main__":
    main()
