#!/usr/bin/env python3
"""Record the evidence-based Step 9 fitness decision for UrbanPulse."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from project_config import DB_PATH, OUTPUT_DIR

DB = DB_PATH
REPORT = OUTPUT_DIR / "urbanpulse_step9_fitness_decision.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    canonical = con.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(primary_analysis_eligible), 0) AS eligible FROM canonical_cleaned"
    ).fetchone()
    raw = con.execute(
        "SELECT COUNT(*) AS n, COUNT(DISTINCT record_id) AS distinct_ids FROM raw_urbanpulse"
    ).fetchone()
    unknown = con.execute(
        "SELECT COALESCE(SUM(observed_count), 0) AS n FROM quality_decision WHERE decision_class='unknown'"
    ).fetchone()["n"]
    valid_extremes = con.execute(
        "SELECT COALESCE(SUM(observed_count), 0) AS n FROM quality_decision WHERE decision_class='valid_extreme'"
    ).fetchone()["n"]
    confirmed_errors = con.execute(
        "SELECT COALESCE(SUM(observed_count), 0) AS n FROM quality_decision WHERE decision_class='confirmed_error'"
    ).fetchone()["n"]
    provenance_flags = con.execute(
        "SELECT COUNT(*) FROM provenance_diagnostic WHERE run_id='step8_provenance_20261008' AND flagged=1"
    ).fetchone()[0]
    hypotheses = con.execute(
        "SELECT COUNT(*) AS n, COALESCE(SUM(significant_at_99), 0) AS supported FROM inferential_hypothesis_result"
    ).fetchone()
    step7_rel = con.execute(
        "SELECT COUNT(*) AS n, SUM(CASE WHEN ci99_lower <= 0 AND ci99_upper >= 0 THEN 1 ELSE 0 END) AS intervals_include_null FROM step7_relationship_effect"
    ).fetchone()
    forecast = con.execute(
        "SELECT COUNT(*) AS n, AVG(model_r2) AS mean_r2, AVG(mae_improvement) AS mean_improvement FROM step7_forecast_result"
    ).fetchone()
    contracts = {
        row["contract_key"]: row["current_status"]
        for row in con.execute("SELECT contract_key, current_status FROM data_contract")
    }

    decision = "Fit only for descriptive reporting"
    decision_code = "FIT_ONLY_DESCRIPTIVE_REPORTING"
    now = utc_now()
    evidence = {
        "canonical_rows": canonical["n"],
        "primary_analysis_eligible_rows": canonical["eligible"],
        "primary_analysis_ineligible_rows": canonical["n"] - canonical["eligible"],
        "raw_rows": raw["n"],
        "raw_distinct_record_ids": raw["distinct_ids"],
        "confirmed_error_items": confirmed_errors,
        "valid_extreme_items": valid_extremes,
        "unknown_decision_items": unknown,
        "step6_hypotheses": hypotheses["n"],
        "step6_supported_at_99_percent": hypotheses["supported"],
        "step7_relationship_models": step7_rel["n"],
        "step7_relationship_intervals_including_null": step7_rel["intervals_include_null"],
        "step7_forecast_metric_folds": forecast["n"],
        "step7_mean_r2": forecast["mean_r2"],
        "step7_mean_mae_improvement": forecast["mean_improvement"],
        "step8_provenance_flags": provenance_flags,
        "decision_basis": "intentional sample, unresolved semantic/quality decisions, weak/non-generalizable inferential and forecasting evidence, and no provenance flags under the stated null model",
    }
    conditions = (
        "Use for aggregate summaries, distributions, ranges, coverage, exploratory charts, and documented descriptive reporting. "
        "Do not use the current file alone for operational control, safety-critical decisions, KPI commitments, causal claims, or production forecasting. "
        "An upgrade to operational analysis requires sampling-frame/representativeness documentation, owner confirmation of speed/parking/outage/temperature/zone semantics, "
        "source or station metadata, and a repeat validation after remediation."
    )

    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS step9_fitness_decision (
            decision_id TEXT PRIMARY KEY,
            classification TEXT NOT NULL,
            classification_code TEXT NOT NULL,
            decision_confidence TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            permitted_use TEXT NOT NULL,
            restrictions TEXT NOT NULL,
            decided_at_utc TEXT NOT NULL
        );
        """
    )
    con.execute("DELETE FROM step9_fitness_decision WHERE decision_id='step9_final_fitness'")
    con.execute(
        "INSERT INTO step9_fitness_decision VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "step9_final_fitness",
            decision,
            decision_code,
            "High for current-use classification; not a claim of 99% provenance certainty",
            json.dumps(evidence, sort_keys=True),
            "Descriptive reporting and exploratory analysis with limitations disclosed",
            conditions,
            now,
        ),
    )
    con.execute(
        "INSERT OR REPLACE INTO data_contract(contract_key, category, specification, current_status, action_required) VALUES (?, ?, ?, ?, ?)",
        (
            "step9_fitness_decision",
            "final_use_classification",
            "Classify current dataset for permitted analytical use after Steps 1-8.",
            "COMPLETED_STEP_9_FIT_ONLY_DESCRIPTIVE_REPORTING",
            "Remediate unresolved semantic, source, and representativeness issues before operational use.",
        ),
    )
    con.execute(
        "INSERT OR REPLACE INTO analysis_run(run_key, value_text, value_num, details_json) VALUES (?, ?, ?, ?)",
        (
            "step9_fitness_decision",
            decision,
            1.0,
            json.dumps({"classification_code": decision_code, "evidence": evidence, "decided_at_utc": now}),
        ),
    )
    con.commit()

    with REPORT.open("w", encoding="utf-8") as f:
        f.write("# UrbanPulse Step 9: Fitness Decision\n\n")
        f.write(f"## Final classification\n\n**{decision}**\n\n")
        f.write("This is the appropriate current-use classification for the dataset as loaded and documented through Steps 1–8. It is not classified as fit for operational analysis because the data are intentionally sampled, several semantic/source decisions remain unresolved, and model/forecast evidence does not establish reliable operational relationships or prediction.\n\n")
        f.write("## Evidence considered\n\n")
        f.write(f"- Canonical layer: {canonical['n']:,} rows; {canonical['eligible']:,} primary-analysis eligible and {canonical['n'] - canonical['eligible']:,} not eligible under the quality rules.\n")
        f.write(f"- Raw layer: {raw['n']:,} rows and {raw['n'] - raw['distinct_ids']:,} duplicate record IDs retained in the audit trail; canonical deduplication is separate.\n")
        f.write(f"- Quality decisions: {confirmed_errors:,} confirmed-error items, {valid_extremes:,} valid-extreme items, and {unknown:,} unknown-decision items.\n")
        f.write(f"- Step 6: {hypotheses['supported']:,} of {hypotheses['n']:,} registered hypotheses supported at the predefined 99% threshold.\n")
        f.write(f"- Step 7: {step7_rel['intervals_include_null']:,} of {step7_rel['n']:,} adjusted relationship intervals included the null effect; mean forecast R² was {forecast['mean_r2']:.3f}.\n")
        f.write(f"- Step 8: {provenance_flags:,} provenance diagnostics were flagged under the independent-permutation null. This is not proof of authentic or synthetic origin.\n\n")
        f.write("## Permitted use\n\n")
        f.write("Use for aggregate summaries, distributions, ranges, coverage, exploratory charts, and descriptive reporting with limitations disclosed. It may also support controlled training, dashboard prototyping, and pipeline testing, but those uses do not upgrade its operational fitness.\n\n")
        f.write("## Restrictions and upgrade conditions\n\n")
        f.write(conditions + "\n\n")
        f.write("Raw and canonical layers remain unchanged.\n")

    con.close()
    print(json.dumps({"decision": decision, "decision_code": decision_code, "report": str(REPORT), "integrity_pending": True}, indent=2))


if __name__ == "__main__":
    main()
