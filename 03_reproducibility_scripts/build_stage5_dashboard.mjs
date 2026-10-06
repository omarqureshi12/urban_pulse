import fs from "node:fs/promises";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const projectRoot = "/Users/apple/Desktop/urban city project";
const outputPath = process.env.URBANPULSE_STAGE5_OUTPUT || `${projectRoot}/02_final_outputs/urbanpulse_phase5_dashboard.xlsx`;
const data = {
  city: JSON.parse(await fs.readFile("/tmp/urbanpulse_stage5_city.json", "utf8")),
  zone: JSON.parse(await fs.readFile("/tmp/urbanpulse_stage5_zone.json", "utf8")),
  month: JSON.parse(await fs.readFile("/tmp/urbanpulse_stage5_month.json", "utf8")),
};
const observedCount = data.city.reduce((sum, row) => sum + Number(row.records || 0), 0);
const zoneCount = data.zone.reduce((sum, row) => sum + Number(row.records || 0), 0);
const unknownZoneCount = observedCount - zoneCount;

const wb = Workbook.create();
const dash = wb.worksheets.add("Dashboard");
const source = wb.worksheets.add("Source_Data");
const font = "Arial";
const navy = "#1F4E78";
const blue = "#4472C4";
const teal = "#2F75B5";
const orange = "#ED7D31";

dash.showGridLines = false;
source.showGridLines = false;
dash.tabColor = navy;
source.tabColor = "#A6A6A6";

dash.getRange("A1:N1").merge();
dash.getRange("A1").values = [["UrbanPulse Compact Dashboard"]];
dash.getRange("A2:N2").merge();
dash.getRange("A2").values = [[`Observed-only traffic-volume summaries. City/month: ${observedCount.toLocaleString()} records. Zone: ${zoneCount.toLocaleString()} known-zone records.`]];
dash.getRange("A1:N1").format = { font: { name: font, size: 16, bold: true, color: navy }, verticalAlignment: "center" };
dash.getRange("A2:N2").format = { font: { name: font, size: 10, italic: true, color: "#666666" }, verticalAlignment: "center" };
dash.getRange("A1:N1").format.rowHeight = 28;
dash.getRange("A2:N2").format.rowHeight = 22;

const cityRows = [["City", "Traffic volume", "Records"], ...data.city.map(d => [d.label, d.traffic_volume, d.records])];
const zoneRows = [["Zone", "Traffic volume", "Records"], ...data.zone.map(d => [d.label, d.traffic_volume, d.records])];
const monthRows = [["Month", "Traffic volume", "Records"], ...data.month.map(d => [String(d.label), d.traffic_volume, d.records])];
dash.getRange(`A4:C${3 + cityRows.length}`).values = cityRows;
dash.getRange(`E4:G${3 + zoneRows.length}`).values = zoneRows;
dash.getRange(`I4:K${3 + monthRows.length}`).values = monthRows;

for (const range of [dash.getRange("A4:C11"), dash.getRange("E4:G9"), dash.getRange("I4:K13")]) {
  range.format.font = { name: font, size: 10, color: "#222222" };
  range.format.verticalAlignment = "center";
  range.format.borders = { preset: "all", style: "thin", color: "#D9E2F3" };
}
for (const range of [dash.getRange("A4:C4"), dash.getRange("E4:G4"), dash.getRange("I4:K4")]) {
  range.format = { fill: navy, font: { name: font, size: 10, bold: true, color: "#FFFFFF" }, verticalAlignment: "center" };
}
for (const range of [dash.getRange("B5:B11"), dash.getRange("F5:F9"), dash.getRange("J5:J13")]) range.format.numberFormat = "#,##0";
for (const range of [dash.getRange("C5:C11"), dash.getRange("G5:G9"), dash.getRange("K5:K13")]) range.format.numberFormat = "#,##0";

dash.getRange("A15:F15").merge();
dash.getRange("A15").values = [["Traffic volume by city"]];
dash.getRange("G15:L15").merge();
dash.getRange("G15").values = [["Traffic volume by zone"]];
dash.getRange("A32:L32").merge();
dash.getRange("A32").values = [["Traffic volume by month"]];
for (const range of [dash.getRange("A15:F15"), dash.getRange("G15:L15"), dash.getRange("A32:L32")]) {
  range.format = { fill: "#D9E2F3", font: { name: font, size: 11, bold: true, color: navy }, verticalAlignment: "center" };
}

const cityChart = dash.charts.add("bar", dash.getRange("A4:B11"));
cityChart.title = "Traffic volume by city";
cityChart.setPosition("A16", "F30");
cityChart.hasLegend = false;
cityChart.titleTextStyle.typeface = font;
cityChart.titleTextStyle.fontSize = 12;
cityChart.xAxis = { axisType: "textAxis", textStyle: { typeface: font, fontSize: 10 } };
cityChart.yAxis = { numberFormatCode: "#,##0", numberFormatSourceLinked: false, textStyle: { typeface: font, fontSize: 9 } };
cityChart.series.items[0].fill = blue;

const zoneChart = dash.charts.add("bar", dash.getRange("E4:F9"));
zoneChart.title = "Traffic volume by zone";
zoneChart.setPosition("G16", "L30");
zoneChart.hasLegend = false;
zoneChart.titleTextStyle.typeface = font;
zoneChart.titleTextStyle.fontSize = 12;
zoneChart.xAxis = { axisType: "textAxis", textStyle: { typeface: font, fontSize: 10 } };
zoneChart.yAxis = { numberFormatCode: "#,##0", numberFormatSourceLinked: false, textStyle: { typeface: font, fontSize: 9 } };
zoneChart.series.items[0].fill = teal;

const monthChart = dash.charts.add("line", dash.getRange("I4:J13"));
monthChart.title = "Traffic volume by month";
monthChart.setPosition("A33", "L48");
monthChart.hasLegend = false;
monthChart.titleTextStyle.typeface = font;
monthChart.titleTextStyle.fontSize = 12;
monthChart.xAxis = { axisType: "textAxis", textStyle: { typeface: font, fontSize: 10 } };
monthChart.yAxis = { numberFormatCode: "#,##0", numberFormatSourceLinked: false, textStyle: { typeface: font, fontSize: 9 } };
monthChart.series.items[0].line = { fill: orange, style: "solid", width: 2 };

dash.getRange("A50:L52").merge(true);
dash.getRange("A50").values = [[`Scope note: These charts summarize observed values only. The zone view excludes ${unknownZoneCount.toLocaleString()} records with unknown zone. Imputed values are not included.`]];
dash.getRange("A50:L52").format = { font: { name: font, size: 9, italic: true, color: "#666666" }, wrapText: true, verticalAlignment: "top" };

dash.getRange("A:A").format.columnWidth = 16;
dash.getRange("B:B").format.columnWidth = 15;
dash.getRange("C:C").format.columnWidth = 10;
dash.getRange("D:D").format.columnWidth = 3;
dash.getRange("E:E").format.columnWidth = 14;
dash.getRange("F:F").format.columnWidth = 15;
dash.getRange("G:G").format.columnWidth = 10;
dash.getRange("H:H").format.columnWidth = 3;
dash.getRange("I:I").format.columnWidth = 10;
dash.getRange("J:J").format.columnWidth = 15;
dash.getRange("K:K").format.columnWidth = 10;
dash.getRange("L:N").format.columnWidth = 12;

source.getRange("A1:D1").values = [["UrbanPulse Stage 5 Dashboard Source", "Value", "Records", "Population"]];
source.getRange("A2:D2").values = [["City summaries", "Traffic volume", "Records", `Observed-only (${observedCount.toLocaleString()} rows)`]];
source.getRange("A3:C3").values = cityRows;
source.getRange("A12:D12").values = [["Zone summaries", "Traffic volume", "Records", `Known-zone observed-only (${zoneCount.toLocaleString()} rows)`]];
source.getRange("A13:C13").values = zoneRows;
source.getRange("A21:D21").values = [["Month summaries", "Traffic volume", "Records", `Observed-only (${observedCount.toLocaleString()} rows)`]];
source.getRange("A22:C22").values = monthRows;
source.getRange("A34:D36").values = [
  ["Source", "02_final_outputs/urbanpulse_rdbms.sqlite", "", "Authoritative SQLite summary views"],
  ["Primary views", "v_primary_observed; v_primary_zone_complete", "", "No imputed values"],
  ["Use", "Presentation companion", "", "Native PivotTables remain in urbanpulse_phase4_working.xlsx"],
];
source.getRange("A1:D36").format.font = { name: font, size: 10, color: "#222222" };
source.getRange("A1:D1").format = { fill: navy, font: { name: font, size: 11, bold: true, color: "#FFFFFF" } };
source.getRange("A2:D2").format = { fill: "#D9E2F3", font: { name: font, size: 10, bold: true, color: navy } };
source.getRange("A12:D12").format = { fill: "#D9E2F3", font: { name: font, size: 10, bold: true, color: navy } };
source.getRange("A21:D21").format = { fill: "#D9E2F3", font: { name: font, size: 10, bold: true, color: navy } };
source.getRange("A1:D36").format.borders = { preset: "all", style: "thin", color: "#D9E2F3" };
source.getRange("B4:B10").format.numberFormat = "#,##0";
source.getRange("B14:B18").format.numberFormat = "#,##0";
source.getRange("B23:B31").format.numberFormat = "#,##0";
source.getRange("A:A").format.columnWidth = 28;
source.getRange("B:B").format.columnWidth = 36;
source.getRange("C:C").format.columnWidth = 12;
source.getRange("D:D").format.columnWidth = 40;

wb.recalculate();
const summary = await wb.inspect({ kind: "sheet,table,drawing", maxChars: 12000, tableMaxRows: 8, tableMaxCols: 8 });
console.log(summary.ndjson);
const errors = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!", options: { useRegex: true, maxResults: 100 }, summary: "Stage 5 formula error scan" });
console.log(errors.ndjson);
const preview = await wb.render({ sheetName: "Dashboard", autoCrop: "all", scale: 1, format: "png" });
await fs.writeFile("/tmp/urbanpulse_stage5_dashboard_preview.png", new Uint8Array(await preview.arrayBuffer()));
const out = await SpreadsheetFile.exportXlsx(wb);
await out.save(outputPath);
console.log(`saved ${outputPath}`);
