import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const sourcePath = "/Users/apple/Desktop/urban city project/02_final_outputs/urbanpulse_refreshable.xlsx";
const outputPath = "/tmp/urbanpulse_stage6_controlled_refresh.xlsx";
const controlledRow = [
  "URB_TEST_STAGE6",
  "Jaipur",
  "Central",
  "2026-01-03 00:00:00",
  2500,
  40,
  1000,
  70.0,
  1,
  0,
  10.0,
  5,
  25.0,
];

const wb = await SpreadsheetFile.importXlsx(await FileBlob.load(sourcePath));
const sheet = wb.worksheets.getItem("Sheet1");
const table = sheet.tables.items.find((item) => item.name === "tbl_raw");
if (!table) throw new Error("tbl_raw was not found");
table.rows.add(null, [controlledRow]);
wb.recalculate();
const check = await wb.inspect({ kind: "table", sheetId: "Sheet1", range: "A1635:M1637", include: "values", tableMaxRows: 5, tableMaxCols: 13, maxChars: 5000 });
console.log(check.ndjson);
const out = await SpreadsheetFile.exportXlsx(wb);
await out.save(outputPath);
console.log(`saved ${outputPath}`);
