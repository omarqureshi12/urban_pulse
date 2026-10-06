import sqlite3

from project_config import DB_PATH, OUTPUT_DIR

CONTRACT_PATH = OUTPUT_DIR / "urbanpulse_data_contract.md"


def main():
    con = sqlite3.connect(DB_PATH)
    con.execute("UPDATE data_contract SET current_status=?, action_required=? WHERE contract_key='row_grain'", (
        "CONFIRMED_INTENTIONAL_SAMPLE",
        "Treat each row as a sampled observation at a four-hour timestamp; do not infer a complete city-zone panel.",
    ))
    con.execute("INSERT OR REPLACE INTO analysis_run VALUES (?,?,?,?)", (
        "grain_confirmation",
        "Data owner confirmed that the dataset is intentionally sampled.",
        None,
        '{"row_grain":"intentional_sample","full_panel_inference":false}',
    ))
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.commit()
    con.close()

    text = open(CONTRACT_PATH, encoding="utf-8").read()
    text = text.replace("PAUSED_FOR_GRAIN_CONFIRMATION", "CONFIRMED_INTENTIONAL_SAMPLE")
    text = text.replace("Step 2 is complete and paused. No inferential modeling, city ranking, or operational conclusion will begin until the data owner confirms whether one sampled observation per timestamp is intentional or whether city-zone combinations are missing from the source.", "Step 2 is complete. The data owner confirmed that one sampled observation per timestamp is intentional. Analyses must treat the data as an intentionally sampled stream, not as a complete city-zone-time panel.")
    with open(CONTRACT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print({"status": "CONFIRMED_INTENTIONAL_SAMPLE", "integrity": integrity})


if __name__ == "__main__":
    main()
