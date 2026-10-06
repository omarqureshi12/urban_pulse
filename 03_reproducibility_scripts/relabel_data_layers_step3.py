import sqlite3

from project_config import DB_PATH, OUTPUT_DIR

DATA_LAYERS_REPORT = OUTPUT_DIR / "urbanpulse_data_layers.md"
CONTRACT_PATH = OUTPUT_DIR / "urbanpulse_data_contract.md"


def main():
    con = sqlite3.connect(DB_PATH)
    con.execute("UPDATE data_contract SET current_status=?, action_required=? WHERE contract_key='data_layers'", (
        "COMPLETED_STEP_3",
        "Use v_primary_observed for primary statistics; use sensitivity tables for imputation scenarios only.",
    ))
    con.execute("UPDATE data_contract SET current_status=? WHERE contract_key='imputation_policy'", ("COMPLETED_STEP_3",))
    con.execute("INSERT OR REPLACE INTO analysis_run VALUES (?,?,?,?)", (
        "step3_data_layers",
        "Step 3 completed: two-layer raw/canonical RDBMS design with normalized flags and separate change log.",
        None,
        '{"step":"3","primary_imputation":false,"sensitivity_imputation":true}',
    ))
    con.execute("INSERT OR REPLACE INTO analysis_run VALUES (?,?,?,?)", (
        "step4_inferential_reclassified",
        "Previously completed inferential analysis retained and reclassified as the next stage after Step 3.",
        None,
        '{"prior_label":"step3_inferential","new_workflow_stage":"step4"}',
    ))
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.commit()
    con.close()

    text = open(DATA_LAYERS_REPORT, encoding="utf-8").read()
    text = text.replace("# UrbanPulse Two-Layer Data Model", "# UrbanPulse Step 3: Two-Layer Data Model")
    text = text.replace("Step 2 now uses an auditable two-layer RDBMS design.", "Step 3 uses an auditable two-layer RDBMS design.")
    with open(DATA_LAYERS_REPORT, "w", encoding="utf-8") as f:
        f.write(text)

    text = open(CONTRACT_PATH, encoding="utf-8").read()
    text = text.replace("## Two-layer data model", "## Step 3: Two-layer data model")
    with open(CONTRACT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print({"status": "STEP_3_RELABELED", "integrity": integrity})


if __name__ == "__main__":
    main()
