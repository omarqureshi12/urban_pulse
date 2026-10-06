import os
import sqlite3

from project_config import DB_PATH, OUTPUT_DIR

CONTRACT_PATH = OUTPUT_DIR / "urbanpulse_data_contract.md"


def main():
    con = sqlite3.connect(DB_PATH)
    con.execute("UPDATE data_contract SET current_status=?, action_required=? WHERE contract_key='row_grain'", (
        "PAUSED_FOR_GRAIN_CONFIRMATION",
        "Confirm whether one sampled observation per timestamp is intentional or whether city-zone combinations are missing.",
    ))
    con.execute("INSERT OR REPLACE INTO analysis_run VALUES (?,?,?,?)", (
        "step2_status",
        "Step 2 complete and paused for row-grain confirmation. No inferential modeling authorized.",
        None,
        '{"step":"2","status":"paused","next_gate":"grain_confirmation"}',
    ))
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.commit()
    con.close()

    text = open(CONTRACT_PATH, encoding="utf-8").read()
    text = text.replace("BLOCKED_FOR_FULL_PANEL_INFERENCE", "PAUSED_FOR_GRAIN_CONFIRMATION")
    text = text.replace("The dataset may proceed to descriptive and sensitivity analysis. Full panel inference, city ranking, and operational conclusions remain blocked until the data owner confirms whether one sampled observation per timestamp is intentional or whether city-zone combinations are missing from the source.", "Step 2 is complete and paused. No inferential modeling, city ranking, or operational conclusion will begin until the data owner confirms whether one sampled observation per timestamp is intentional or whether city-zone combinations are missing from the source.")
    with open(CONTRACT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print({"status": "PAUSED_FOR_GRAIN_CONFIRMATION", "integrity": integrity})


if __name__ == "__main__":
    main()
