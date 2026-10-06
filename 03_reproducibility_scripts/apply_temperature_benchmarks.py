import csv
import json
import sqlite3
import subprocess
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from project_config import DB_PATH, OUTPUT_DIR

REPORT_PATH = OUTPUT_DIR / "urbanpulse_temperature_benchmarks.md"
CSV_PATH = OUTPUT_DIR / "urbanpulse_temperature_benchmarks.csv"

START_DATE = "20160101"
END_DATE = "20261001"
START_ISO = "2016-01-01"
END_ISO = "2026-10-01"
NASA_POWER_DOC_URL = "https://power.larc.nasa.gov/docs/services/api/temporal/daily/"
NASA_POWER_PROCESSING_URL = "https://power.larc.nasa.gov/docs/methodology/data/processing/"

CITY_COORDS = {
    "Bengaluru": (12.9716, 77.5946),
    "Bhopal": (23.2599, 77.4126),
    "Delhi": (28.6139, 77.2090),
    "Indore": (22.7196, 75.8577),
    "Jaipur": (26.9124, 75.7873),
    "Nagpur": (21.1458, 79.0882),
    "Pune": (18.5204, 73.8567),
}


def fetch_power(city, latitude, longitude):
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

    def extrema(parameter, mode):
        values = [(float(value), date) for date, value in data[parameter].items() if float(value) > -900]
        return (min if mode == "min" else max)(values, key=lambda item: item[0])

    low_value, low_date = extrema("T2M_MIN", "min")
    high_value, high_date = extrema("T2M_MAX", "max")
    return {
        "city": city,
        "latitude": latitude,
        "longitude": longitude,
        "period_start": START_ISO,
        "period_end": END_ISO,
        "benchmark_low_c": low_value,
        "benchmark_low_date": f"{low_date[:4]}-{low_date[4:6]}-{low_date[6:]}",
        "benchmark_high_c": high_value,
        "benchmark_high_date": f"{high_date[:4]}-{high_date[4:6]}-{high_date[6:]}",
        "source_url": url,
        "source_observation_count": len([v for v in data["T2M_MIN"].values() if float(v) > -900]),
    }


def main():
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    benchmarks = [fetch_power(city, lat, lon) for city, (lat, lon) in CITY_COORDS.items()]

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS temperature_benchmark (
            city TEXT PRIMARY KEY,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            benchmark_low_c REAL NOT NULL,
            benchmark_low_date TEXT NOT NULL,
            benchmark_high_c REAL NOT NULL,
            benchmark_high_date TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_url TEXT NOT NULL,
            source_observation_count INTEGER NOT NULL,
            retrieved_at_utc TEXT NOT NULL,
            benchmark_definition TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS temperature_benchmark_check (
            record_id TEXT PRIMARY KEY,
            source_row_number INTEGER NOT NULL,
            city TEXT,
            observation_date TEXT,
            raw_temperature_c REAL,
            benchmark_low_c REAL,
            benchmark_high_c REAL,
            benchmark_status TEXT NOT NULL CHECK (benchmark_status IN ('within_benchmark','below_benchmark','above_benchmark','missing','unknown_city')),
            disposition TEXT NOT NULL,
            source_benchmark_city TEXT,
            source_benchmark_period_start TEXT,
            source_benchmark_period_end TEXT
        );

        CREATE VIEW IF NOT EXISTS v_temperature_benchmark_status AS
        SELECT * FROM temperature_benchmark_check;
        """
    )
    con.execute("DELETE FROM temperature_benchmark")
    con.execute("DELETE FROM temperature_benchmark_check")

    con.executemany(
        """
        INSERT INTO temperature_benchmark (
            city, latitude, longitude, period_start, period_end,
            benchmark_low_c, benchmark_low_date, benchmark_high_c, benchmark_high_date,
            source_name, source_url, source_observation_count, retrieved_at_utc, benchmark_definition
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        [
            (
                b["city"], b["latitude"], b["longitude"], b["period_start"], b["period_end"],
                b["benchmark_low_c"], b["benchmark_low_date"], b["benchmark_high_c"], b["benchmark_high_date"],
                "NASA POWER Daily API", b["source_url"], b["source_observation_count"], retrieved_at,
                "Lowest daily T2M_MIN and highest daily T2M_MAX for the city-center point over 2016-01-01 through 2026-10-01.",
            )
            for b in benchmarks
        ],
    )

    check_rows = []
    for row in con.execute(
        """
        SELECT record_id, source_row_number, cleaned_city AS city, observation_date, raw_temperature_c, cleaned_temperature_c
        FROM canonical_cleaned
        ORDER BY source_row_number
        """
    ):
        temp = row["cleaned_temperature_c"]
        b = con.execute("SELECT * FROM temperature_benchmark WHERE city=?", (row["city"],)).fetchone()
        if b is None:
            status = "unknown_city"
            disposition = "Preserve the dataset value and flag for separate review."
            low = high = benchmark_city = period_start = period_end = None
        elif temp is None:
            status = "missing"
            disposition = "Preserve missing value; no replacement in the primary layer."
            low, high = b["benchmark_low_c"], b["benchmark_high_c"]
            benchmark_city, period_start, period_end = b["city"], b["period_start"], b["period_end"]
        elif temp < b["benchmark_low_c"]:
            status = "below_benchmark"
            disposition = "Preserve the dataset value and flag as outside the external benchmark; do not overwrite."
            low, high = b["benchmark_low_c"], b["benchmark_high_c"]
            benchmark_city, period_start, period_end = b["city"], b["period_start"], b["period_end"]
        elif temp > b["benchmark_high_c"]:
            status = "above_benchmark"
            disposition = "Preserve the dataset value and flag as outside the external benchmark; do not overwrite."
            low, high = b["benchmark_low_c"], b["benchmark_high_c"]
            benchmark_city, period_start, period_end = b["city"], b["period_start"], b["period_end"]
        else:
            status = "within_benchmark"
            disposition = "Retain the dataset value unchanged."
            low, high = b["benchmark_low_c"], b["benchmark_high_c"]
            benchmark_city, period_start, period_end = b["city"], b["period_start"], b["period_end"]
        check_rows.append(
            (
                row["record_id"], row["source_row_number"], row["city"], row["observation_date"], row["raw_temperature_c"],
                low, high, status, disposition, benchmark_city, period_start, period_end,
            )
        )
    con.executemany(
        "INSERT INTO temperature_benchmark_check VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        check_rows,
    )

    # A benchmark comparison is an additional flag, not a correction. Avoid duplicate flags.
    con.execute(
        """
        INSERT INTO quality_flag (record_id, source_row_number, field_name, flag_type, raw_value, cleaned_value, reason, primary_analysis_effect)
        SELECT c.record_id, c.source_row_number, 'temperature_c', 'outlier', CAST(c.raw_temperature_c AS TEXT), CAST(c.raw_temperature_c AS TEXT),
               'Temperature is outside the 2016-01-01 through 2026-10-01 NASA POWER city benchmark range.',
               'Retained unchanged; exclude from temperature interpretation pending exact station-level confirmation.'
        FROM temperature_benchmark_check c
        WHERE c.benchmark_status IN ('below_benchmark','above_benchmark')
          AND NOT EXISTS (
              SELECT 1 FROM quality_flag q
              WHERE q.record_id=c.record_id AND q.field_name='temperature_c'
                AND q.flag_type='outlier'
                AND q.reason LIKE 'Temperature is outside the 2016-01-01 through 2026-10-01 NASA POWER city benchmark range.%'
          )
        """
    )
    con.execute("DELETE FROM quality_flag_summary")
    con.execute(
        """
        INSERT INTO quality_flag_summary (flag_type, field_name, flag_count)
        SELECT flag_type, field_name, COUNT(*)
        FROM quality_flag
        GROUP BY flag_type, field_name
        """
    )

    con.execute(
        "INSERT OR REPLACE INTO data_contract VALUES (?,?,?,?,?)",
        (
            "temperature_benchmark",
            "Quality",
            "For each known city, benchmark_low_c is the lowest NASA POWER daily T2M_MIN and benchmark_high_c is the highest NASA POWER daily T2M_MAX from 2016-01-01 through 2026-10-01 at the city-center coordinate.",
            "COMPLETED_STAGE_4_BENCHMARK_APPLIED",
            "Retain every dataset temperature. Treat within_benchmark as unchanged. Treat outside-benchmark values as flagged unknowns requiring station-level confirmation before any correction.",
        ),
    )
    con.execute(
        "INSERT OR REPLACE INTO analysis_run VALUES (?,?,?,?)",
        (
            "temperature_benchmark",
            "City temperature benchmarks applied from NASA POWER; values were not overwritten.",
            None,
            json.dumps({"period_start": START_ISO, "period_end": END_ISO, "cities": len(benchmarks), "replacement_count": 0, "source_type": "gridded_area_benchmark"}),
        ),
    )
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    status_counts = dict(con.execute("SELECT benchmark_status, COUNT(*) FROM temperature_benchmark_check GROUP BY benchmark_status" ).fetchall())
    outlier_city_counts = dict(con.execute("SELECT city, COUNT(*) FROM temperature_benchmark_check WHERE benchmark_status IN ('below_benchmark','above_benchmark') GROUP BY city ORDER BY city").fetchall())
    con.commit()
    con.close()

    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["city", "latitude", "longitude", "period_start", "period_end", "benchmark_low_c", "benchmark_low_date", "benchmark_high_c", "benchmark_high_date", "source_name", "source_url", "source_observation_count", "retrieved_at_utc"])
        for b in benchmarks:
            writer.writerow([b[k] for k in ["city", "latitude", "longitude", "period_start", "period_end", "benchmark_low_c", "benchmark_low_date", "benchmark_high_c", "benchmark_high_date"]] + ["NASA POWER Daily API", b["source_url"], b["source_observation_count"], retrieved_at])

    lines = [
        "# UrbanPulse City Temperature Benchmarks",
        "",
        "## Rule applied",
        "",
        "The immutable raw layer and canonical temperature values were not overwritten. Each dataset temperature was compared with a city-level external benchmark. Values within the benchmark range were retained unchanged. Values outside it were retained but flagged for station-level review.",
        "",
        f"Benchmark period: `{START_ISO}` through `{END_ISO}`.",
        "Source: NASA POWER Daily API, using daily `T2M_MIN` and `T2M_MAX` at each city-center coordinate, in local solar time.",
        "",
        "## Benchmarks",
        "",
        "| City | Low benchmark °C | Date | High benchmark °C | Date | Daily observations |",
        "|---|---:|---|---:|---|---:|",
    ]
    for b in benchmarks:
        lines.append(f"| {b['city']} | {b['benchmark_low_c']:.2f} | {b['benchmark_low_date']} | {b['benchmark_high_c']:.2f} | {b['benchmark_high_date']} | {b['source_observation_count']:,} |")
    lines += [
        "",
        "## Dataset comparison",
        "",
        "| Status | Rows | Treatment |",
        "|---|---:|---|",
        f"| within_benchmark | {status_counts.get('within_benchmark', 0):,} | Retained unchanged |",
        f"| above_benchmark | {status_counts.get('above_benchmark', 0):,} | Retained and flagged, not overwritten |",
        f"| below_benchmark | {status_counts.get('below_benchmark', 0):,} | Retained and flagged, not overwritten |",
        f"| missing | {status_counts.get('missing', 0):,} | Preserved missing; no imputation |",
        f"| unknown_city | {status_counts.get('unknown_city', 0):,} | Preserved and flagged |",
        "",
        "Out-of-benchmark counts by city: " + ", ".join(f"{city} {count}" for city, count in outlier_city_counts.items()) + ".",
        "",
        "## Interpretation",
        "",
        "These are gridded area benchmarks, not exact station certificates for each 4-hour record. An out-of-benchmark value is therefore an evidence flag, not proof of an error. The next correction step would require an exact station/date/time match from an authoritative station record. Until that exists, the dataset value remains unchanged.",
        "",
        f"NASA POWER Daily API documentation: {NASA_POWER_DOC_URL}",
        f"NASA POWER processing methodology: {NASA_POWER_PROCESSING_URL}",
        "",
        f"SQLite integrity check: `{integrity}`.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(REPORT_PATH), "csv": str(CSV_PATH), "status_counts": status_counts, "outlier_city_counts": outlier_city_counts, "integrity": integrity, "replacements": 0}, indent=2))


if __name__ == "__main__":
    main()
