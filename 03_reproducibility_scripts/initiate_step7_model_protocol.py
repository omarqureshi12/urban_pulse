import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from project_config import DB_PATH, OUTPUT_DIR

REPORT_PATH = OUTPUT_DIR / "urbanpulse_step7_model_protocol.md"


def main():
    initiated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    con = sqlite3.connect(DB_PATH)
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS model_registry (
            model_id TEXT PRIMARY KEY,
            purpose TEXT NOT NULL,
            target_metrics TEXT NOT NULL,
            model_class TEXT NOT NULL,
            predictors TEXT NOT NULL,
            estimand TEXT NOT NULL,
            uncertainty_method TEXT NOT NULL,
            primary_inclusion_policy TEXT NOT NULL,
            effect_size_output TEXT NOT NULL,
            status TEXT NOT NULL,
            preregistered_at_utc TEXT NOT NULL
        );
        """
    )
    con.execute("DELETE FROM model_registry")
    models = [
        (
            "M1_city_zone_continuous", "City/zone comparisons", "avg_speed_kmph;temperature_c;parking_occupancy_pct;power_outage_minutes",
            "Huber robust regression with city and zone effects", "city + zone + month + hour + weekday",
            "Adjusted city and zone marginal contrasts versus the adjusted grand mean, in native units and standardized units.",
            "3,000 resamples of calendar dates with replacement; 99% percentile intervals; resample the whole date block.",
            "Observed values only; invalid speed outside 0-120 excluded; probable-error temperatures excluded; unknown zones excluded from zone contrasts.",
            "Adjusted contrast, standardized contrast, and robust residual scale.", "predefined", initiated_at,
        ),
        (
            "M2_city_zone_counts", "City/zone comparisons", "traffic_volume;public_transport_usage;road_incidents;waterlogging_reports;citizen_complaints",
            "Poisson GLM when dispersion <= 1.5; otherwise negative-binomial GLM",
            "city + zone + month + hour + weekday; log link",
            "Adjusted incidence-rate ratio or multiplicative city/zone contrast versus the adjusted grand mean.",
            "3,000 calendar-date block bootstrap resamples; 99% percentile intervals for rate ratios and contrasts.",
            "Observed non-negative counts only; unknown zones excluded from zone contrasts; no imputation.",
            "Incidence-rate ratio, multiplicative contrast, and overdispersion estimate.", "predefined", initiated_at,
        ),
        (
            "M3_relationship_traffic_speed", "Adjusted relationship", "avg_speed_kmph",
            "Huber robust regression", "traffic_volume + city + zone + month + hour + weekday",
            "Adjusted change in speed per 1,000-unit traffic increase, plus standardized coefficient.",
            "3,000 calendar-date block bootstrap resamples; 99% percentile interval for the adjusted coefficient.",
            "Observed complete pairs; valid speed 0-120; unknown zones retained only in the city/time-adjusted model as an explicit category; no imputation.",
            "Native-unit slope, standardized slope, and partial association.", "predefined", initiated_at,
        ),
        (
            "M4_relationship_incidents_waterlogging", "Adjusted relationship", "road_incidents",
            "Negative-binomial GLM with log link, if overdispersed",
            "waterlogging_reports + city + zone + month + hour + weekday",
            "Adjusted incidence-rate ratio for one additional waterlogging report.",
            "3,000 calendar-date block bootstrap resamples; 99% percentile interval for the rate ratio.",
            "Observed non-negative counts; no imputation; unknown zones represented explicitly for the adjusted relationship.",
            "Incidence-rate ratio and multiplicative change.", "predefined", initiated_at,
        ),
        (
            "M5_relationship_temperature_outage", "Adjusted relationship", "power_outage_minutes",
            "Huber robust regression", "temperature_c + city + zone + month + hour + weekday",
            "Adjusted change in outage minutes per 1°C increase, plus standardized coefficient.",
            "3,000 calendar-date block bootstrap resamples; 99% percentile interval for the adjusted coefficient.",
            "Observed temperatures excluding probable_error values; no imputation; valid outage observations only.",
            "Native-unit slope, standardized slope, and partial association.", "predefined", initiated_at,
        ),
        (
            "M6_repeated_time_dependence", "Repeated time observations", "all model targets",
            "Date-block bootstrap wrapper around each fitted model",
            "Calendar date as the resampling block; retain all observations within each sampled date block.",
            "Uncertainty that respects same-date dependence and avoids treating every row as independent.",
            "3,000 date-block resamples; 99% percentile intervals for all reported effects.",
            "Primary observed layer only; no row-level iid bootstrap; no imputation.",
            "99% uncertainty intervals for coefficients, contrasts, rate ratios, and predictions.", "predefined", initiated_at,
        ),
        (
            "M7_forecasting", "Forecasting", "all metrics",
            "Rolling time-based validation; robust regression for continuous targets and Poisson/negative-binomial model for counts",
            "Known city, zone, month, hour, weekday, and available lagged same-city target values; no future information.",
            "Out-of-sample MAE, RMSE, R-squared, and improvement versus a city-month median baseline.",
            "Three expanding-window chronological holdouts; 99% date-block bootstrap intervals for error metrics and improvement.",
            "Observed target values only; invalid speed and probable-error temperatures excluded; imputation sensitivity separate.",
            "MAE, RMSE, R-squared, and percent improvement versus baseline.", "predefined", initiated_at,
        ),
    ]
    con.executemany("INSERT INTO model_registry VALUES (?,?,?,?,?,?,?,?,?,?,?)", models)
    con.execute("INSERT OR REPLACE INTO data_contract VALUES (?,?,?,?,?)", (
        "step7_model_protocol",
        "Analysis",
        "Fit-for-purpose models are predefined: robust regression for continuous adjusted relationships and comparisons, Poisson/negative-binomial models for counts, date-block bootstrap for repeated dates, and rolling time validation for forecasts.",
        "INITIATED_STEP_7_MODEL_PROTOCOL_PENDING_FITTING",
        "Fit models only after protocol confirmation. Report effect sizes and 99% uncertainty intervals, not p-values alone.",
    ))
    con.execute("INSERT OR REPLACE INTO analysis_run VALUES (?,?,?,?)", (
        "step7_model_protocol",
        "Step 7 fit-for-purpose model protocol predefined; model fitting not yet run.",
        None,
        json.dumps({"models": [m[0] for m in models], "bootstrap_repetitions": 3000, "confidence_level": 0.99, "fitting_started": False, "imputation_primary": False}),
    ))
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.commit()
    con.close()

    lines = [
        "# UrbanPulse Step 7: Fit-for-Purpose Model Protocol",
        "",
        "This protocol defines the models, estimands, inclusion rules, and uncertainty methods before fitting. It is designed for the intentionally sampled stream and does not assume a complete city-zone panel.",
        "",
        "## Primary data rules",
        "",
        "- Primary models use the canonical observed layer only.",
        "- No imputation in primary models.",
        "- Speed values outside 0-120 km/h are excluded from speed models.",
        "- Temperature values classified as probable_error are excluded from temperature models.",
        "- Unknown zones are excluded from zone contrasts, but may be represented explicitly in adjusted relationships.",
        "- The Step 5A imputed layer is a separate sensitivity analysis.",
        "",
        "## Model registry",
        "",
        "| Model | Purpose | Model class | Main estimand | Uncertainty |",
        "|---|---|---|---|---|",
    ]
    for model in models:
        lines.append(f"| {model[0]} | {model[1]} | {model[3]} | {model[5]} | {model[6]} |")
    lines += [
        "",
        "## Reporting standard",
        "",
        "Every fitted model will report effect sizes in interpretable units, standardized effects where useful, and 99% uncertainty intervals. P-values will be secondary diagnostics rather than the only decision criterion.",
        "",
        "Count-model selection will be based on observed dispersion: Poisson when the dispersion ratio is at or below 1.5, otherwise negative binomial. Forecast models will be evaluated only with chronological holdouts against a simple city-month median baseline.",
        "",
        "Step 7 model fitting has not yet started. SQLite integrity check: `" + integrity + "`.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(REPORT_PATH), "models": len(models), "fitting_started": False, "integrity": integrity}, indent=2))


if __name__ == "__main__":
    main()
