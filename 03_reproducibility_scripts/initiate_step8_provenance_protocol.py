import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from project_config import DB_PATH, OUTPUT_DIR

REPORT_PATH = OUTPUT_DIR / "urbanpulse_step8_provenance_protocol.md"


def main():
    initiated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    con = sqlite3.connect(DB_PATH)
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS provenance_protocol (
            protocol_id TEXT PRIMARY KEY,
            null_model TEXT NOT NULL,
            preserved_features TEXT NOT NULL,
            broken_features TEXT NOT NULL,
            diagnostics TEXT NOT NULL,
            simulation_repetitions INTEGER NOT NULL,
            flag_threshold TEXT NOT NULL,
            interpretation_limit TEXT NOT NULL,
            status TEXT NOT NULL,
            initiated_at_utc TEXT NOT NULL
        );
        """
    )
    con.execute("DELETE FROM provenance_protocol")
    row = (
        "P1",
        "Independent within-field permutation null: for each non-structural field, randomly permute its observed non-missing values across canonical rows while restoring the exact original missingness mask. Timestamps and row IDs remain fixed.",
        "Canonical row count; field-level marginal distributions; per-field missingness count and positions; timestamp grid; city/zone/time labels for conditioning.",
        "Cross-field row alignment; cross-metric correlations; metric-to-city/zone alignment; metric-to-time alignment; within-city temporal serial dependence.",
        "Absolute Spearman correlations; city and zone eta-squared; within-city lag-1 autocorrelation; discrete-value entropy and unique-value rates; repeated-row structure as a separate raw-layer diagnostic.",
        5000,
        "Flag an observed diagnostic when it falls outside the simulated 0.5th-99.5th percentile interval. Report effect direction and interval, not a binary proof claim.",
        "A flagged result means the observed structure is unusual under this specific marginal-preserving null model. It does not prove the data are synthetic and cannot replace source documentation or collection metadata.",
        "predefined",
        initiated_at,
    )
    con.execute("INSERT INTO provenance_protocol VALUES (?,?,?,?,?,?,?,?,?,?)", row)
    con.execute("INSERT OR REPLACE INTO data_contract VALUES (?,?,?,?,?)", (
        "step8_provenance_check",
        "Provenance",
        "Compare the observed canonical data with independently permuted simulations that preserve row count, field marginals, and missingness masks.",
        "INITIATED_STEP_8_PROTOCOL_PENDING_SIMULATION",
        "Run 5,000 simulations after confirmation. Treat out-of-null-range diagnostics as synthetic-looking flags only, never proof without source documentation.",
    ))
    con.execute("INSERT OR REPLACE INTO analysis_run VALUES (?,?,?,?)", (
        "step8_provenance_protocol",
        "Step 8 provenance simulation protocol predefined; simulation not yet run.",
        None,
        json.dumps({"simulations": 5000, "interval": [0.005, 0.995], "null_model": "independent_within_field_permutation", "source_documentation_required": True, "simulation_started": False}),
    ))
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.commit()
    con.close()

    lines = [
        "# UrbanPulse Step 8: Provenance-Check Protocol",
        "",
        "This protocol compares the canonical observed data with simulations that preserve the same marginal distributions and missingness pattern while breaking cross-field and temporal alignment.",
        "",
        "## Null simulation",
        "",
        "- Keep the 1,600 canonical rows, timestamps, row IDs, and missingness mask unchanged.",
        "- Independently permute observed non-missing values within each non-structural field.",
        "- Preserve every field's marginal distribution exactly.",
        "- Generate 5,000 simulated datasets.",
        "",
        "## Diagnostics",
        "",
        "- Absolute pairwise Spearman correlations.",
        "- City and zone eta-squared alignment.",
        "- Within-city lag-1 temporal autocorrelation.",
        "- Entropy and unique-value rates for discrete measures.",
        "- Raw-layer duplicate structure reported separately because exact duplicates were already removed from the canonical layer.",
        "",
        "## Flag rule",
        "",
        "An observed statistic will be flagged when it falls outside the simulated 0.5th-99.5th percentile interval. The result will be described as unusual or synthetic-looking under this null model only. It will not be presented as proof of synthetic origin.",
        "",
        "Step 8 simulation has not yet been run. Source documentation or collection metadata remains necessary for any provenance conclusion.",
        "",
        f"SQLite integrity check: `{integrity}`.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(REPORT_PATH), "simulations": 5000, "simulation_started": False, "integrity": integrity}, indent=2))


if __name__ == "__main__":
    main()
