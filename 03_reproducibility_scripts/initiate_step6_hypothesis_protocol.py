import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from project_config import DB_PATH, OUTPUT_DIR

REPORT_PATH = OUTPUT_DIR / "urbanpulse_step6_hypothesis_protocol.md"


def main():
    initiated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    con = sqlite3.connect(DB_PATH)
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS hypothesis_registry (
            hypothesis_id TEXT PRIMARY KEY,
            family TEXT NOT NULL,
            statement TEXT NOT NULL,
            expected_direction TEXT NOT NULL,
            primary_method TEXT NOT NULL,
            practical_threshold TEXT NOT NULL,
            statistical_threshold TEXT NOT NULL,
            primary_data_policy TEXT NOT NULL,
            status TEXT NOT NULL,
            preregistered_at_utc TEXT NOT NULL
        );
        """
    )
    con.execute("DELETE FROM hypothesis_registry")
    hypotheses = [
        (
            "H1", "relationship", "Traffic volume is associated with average speed.", "negative",
            "Spearman rank correlation with a 99% confidence interval.",
            "Meaningful association requires absolute rho >= 0.20 and the observed sign must be negative.",
            "Two-sided Holm-adjusted p < 0.01 within the relationship family.",
            "Complete observed pairs; exclude invalid speed values outside 0-120 km/h; no imputation.", "predefined", initiated_at,
        ),
        (
            "H2", "relationship", "Road incidents are associated with waterlogging reports.", "positive",
            "Spearman rank correlation with a 99% confidence interval.",
            "Meaningful association requires absolute rho >= 0.20 and the observed sign must be positive.",
            "Two-sided Holm-adjusted p < 0.01 within the relationship family.",
            "Complete observed pairs; no imputation; flagged valid extremes retained unless classified unknown.", "predefined", initiated_at,
        ),
        (
            "H3", "relationship", "Temperature is associated with power outage minutes.", "positive",
            "Spearman rank correlation with a 99% confidence interval.",
            "Meaningful association requires absolute rho >= 0.20 and the observed sign must be positive.",
            "Two-sided Holm-adjusted p < 0.01 within the relationship family.",
            "Complete observed pairs; exclude temperature values classified probable_error; no imputation.", "predefined", initiated_at,
        ),
        (
            "H4_city", "group_difference", "Cities differ materially on the selected operational metrics.", "not_applicable",
            "Permutation group test with eta-squared effect size and 99% confidence-compatible decision rule.",
            "Meaningful city difference requires eta-squared >= 0.06, equivalent to at least 6% between-city variance; pairwise follow-up requires absolute standardized difference >= 0.50.",
            "Holm-adjusted permutation p < 0.01 within the city-group family, plus the practical effect threshold.",
            "Known cities only; no imputation; exclude invalid speed and probable-error temperature values for those metrics.", "predefined", initiated_at,
        ),
        (
            "H4_zone", "group_difference", "Zones differ materially on the selected operational metrics.", "not_applicable",
            "Permutation group test with eta-squared effect size and 99% confidence-compatible decision rule.",
            "Meaningful zone difference requires eta-squared >= 0.06, equivalent to at least 6% between-zone variance; pairwise follow-up requires absolute standardized difference >= 0.50.",
            "Holm-adjusted permutation p < 0.01 within the zone-group family.",
            "Known zones only; exclude unknown zone; no imputation; exclude invalid speed and probable-error temperature values for those metrics.", "predefined", initiated_at,
        ),
        (
            "H5", "temporal_prediction", "The sampled metrics have useful temporal predictability.", "not_applicable",
            "Blocked time-series validation using three chronological holdouts; compare a simple feature model with a city-month median baseline.",
            "Useful prediction requires at least 10% lower out-of-sample MAE than baseline and out-of-sample R-squared >= 0.10 in at least 2 of 3 holdouts.",
            "A performance gate is used instead of a p-value; no random train/test split.",
            "Chronological split; observed values only; no imputation in the primary predictive test; invalid speed and probable-error temperatures excluded for those targets.", "predefined", initiated_at,
        ),
    ]
    con.executemany("INSERT INTO hypothesis_registry VALUES (?,?,?,?,?,?,?,?,?,?)", hypotheses)
    con.execute("INSERT OR REPLACE INTO data_contract VALUES (?,?,?,?,?)", (
        "step6_hypothesis_protocol",
        "Analysis",
        "Step 6 hypotheses and practical thresholds are predefined before testing. Relationship, group-difference, and temporal-predictive tests use separate decision rules.",
        "INITIATED_STEP_6_PROTOCOL_PENDING_TESTING",
        "Do not change thresholds after seeing test results. Obtain confirmation before running the tests.",
    ))
    con.execute("INSERT OR REPLACE INTO analysis_run VALUES (?,?,?,?)", (
        "step6_hypothesis_protocol",
        "Step 6 hypothesis registry and practical thresholds predefined; testing not yet run.",
        None,
        json.dumps({"hypotheses": [h[0] for h in hypotheses], "alpha": 0.01, "holm_correction": True, "testing_started": False}),
    ))
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.commit()
    con.close()

    lines = [
        "# UrbanPulse Step 6: Hypothesis Protocol",
        "",
        "This is the preregistration layer for Step 6. Hypotheses and practical thresholds are locked before testing. No test results are used to choose these thresholds.",
        "",
        "## Statistical standard",
        "",
        "- Primary alpha: 0.01, corresponding to the 99% confidence standard.",
        "- Holm correction: applied within each testing family.",
        "- Primary data: canonical observed layer only. No imputation.",
        "- Sensitivity data: Step 5A imputed layer, used only after the primary tests.",
        "- Unknown values are excluded from the affected primary test and remain available for separate review.",
        "",
        "## Predefined hypotheses",
        "",
        "| ID | Hypothesis | Method | Practical threshold | Statistical/performance threshold |",
        "|---|---|---|---|---|",
    ]
    for h in hypotheses:
        lines.append(f"| {h[0]} | {h[2]} | {h[4]} | {h[5]} | {h[6]} |")
    lines += [
        "",
        "## Testing boundaries",
        "",
        "For H1-H3, a result is a supported relationship only if it has the expected sign, meets the practical correlation threshold, and passes Holm-adjusted p < 0.01.",
        "",
        "For H4, a city or zone difference is material only if it passes the corrected p-value threshold and reaches eta-squared >= 0.06. Pairwise follow-up is only relevant after that gate and requires an absolute standardized difference >= 0.50.",
        "",
        "For H5, temporal predictability is useful only when the feature model improves out-of-sample MAE by at least 10% over the city-month median baseline and reaches out-of-sample R-squared >= 0.10 in at least two of three chronological holdouts.",
        "",
        "Step 6 testing has not yet been run. SQLite integrity check: `" + integrity + "`.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(REPORT_PATH), "hypotheses": len(hypotheses), "testing_started": False, "integrity": integrity}, indent=2))


if __name__ == "__main__":
    main()
