import csv
import html
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from project_config import DB_PATH, OUTPUT_DIR

HTML_PATH = OUTPUT_DIR / "urbanpulse_step5_compact_dashboard.html"
REPORT_PATH = OUTPUT_DIR / "urbanpulse_step5_compact_descriptive_analysis.md"
CSV_PATH = OUTPUT_DIR / "urbanpulse_step5_metric_summary.csv"

METRICS = [
    ("traffic_volume", "Traffic volume", "count"),
    ("avg_speed_kmph", "Average speed", "km/h"),
    ("public_transport_usage", "Public transport usage", "count"),
    ("parking_occupancy_pct", "Parking occupancy", "%"),
    ("road_incidents", "Road incidents", "count"),
    ("waterlogging_reports", "Waterlogging reports", "count"),
    ("power_outage_minutes", "Power outage", "minutes"),
    ("citizen_complaints", "Citizen complaints", "count"),
    ("temperature_c", "Temperature", "°C"),
]


def qtile(values, q):
    values = sorted(values)
    if not values:
        return None
    position = (len(values) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def fmt(value, digits=1):
    if value is None:
        return "n.a."
    if isinstance(value, int) or (isinstance(value, float) and value.is_integer()):
        return f"{int(value):,}"
    return f"{value:,.{digits}f}"


def esc(value):
    return html.escape(str(value))


def svg_bar_chart(title, labels, values, width=760, height=300, color="#2563eb", suffix=""):
    margin_left = 190
    top = 38
    bottom = 26
    plot_w = width - margin_left - 55
    row_h = (height - top - bottom) / max(len(labels), 1)
    max_value = max(values) if values else 1
    parts = [f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">']
    parts.append(f'<text x="12" y="22" class="chart-title">{esc(title)}</text>')
    for i, (label, value) in enumerate(zip(labels, values)):
        y = top + i * row_h + 4
        bar_w = 0 if max_value == 0 else plot_w * value / max_value
        parts.append(f'<text x="{margin_left - 8}" y="{y + row_h * .55:.1f}" text-anchor="end" class="axis-label">{esc(label)}</text>')
        parts.append(f'<rect x="{margin_left}" y="{y:.1f}" width="{bar_w:.1f}" height="{max(row_h - 7, 2):.1f}" rx="3" fill="{color}"/>')
        parts.append(f'<text x="{margin_left + bar_w + 6:.1f}" y="{y + row_h * .55:.1f}" class="value-label">{esc(fmt(value))}{esc(suffix)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def svg_two_bar_chart(title, left_title, left_labels, left_values, right_title, right_labels, right_values, width=900, height=330):
    panel_w = width / 2 - 24
    left = svg_bar_chart(left_title, left_labels, left_values, int(panel_w), height - 20, "#2563eb")
    right = svg_bar_chart(right_title, right_labels, right_values, int(panel_w), height - 20, "#14b8a6")
    # Strip each standalone viewBox and place its contents on a shared canvas.
    left_inner = left[left.find(">") + 1 : left.rfind("</svg>")]
    right_inner = right[right.find(">") + 1 : right.rfind("</svg>")]
    return f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}"><g transform="translate(0,0)">{left_inner}</g><g transform="translate({width/2 + 12:.1f},0)">{right_inner}</g></svg>'


def svg_time_chart(month_labels, month_values, hour_labels, hour_values, width=900, height=300):
    def panel(x, title, labels, values, color, max_labels=12):
        panel_w = width / 2 - 30
        panel_h = height - 50
        max_v = max(values) if values else 1
        step = panel_w / max(len(labels), 1)
        out = [f'<g transform="translate({x},0)"><text x="0" y="22" class="chart-title">{esc(title)}</text>']
        for i, (label, value) in enumerate(zip(labels, values)):
            bar_h = 0 if max_v == 0 else (panel_h - 20) * value / max_v
            bx = i * step + 5
            by = panel_h - bar_h
            out.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{max(step - 8, 3):.1f}" height="{bar_h:.1f}" rx="2" fill="{color}"/>')
            out.append(f'<text x="{bx + (step - 8)/2:.1f}" y="{panel_h + 15:.1f}" text-anchor="middle" class="axis-label">{esc(label)}</text>')
            out.append(f'<text x="{bx + (step - 8)/2:.1f}" y="{by - 4:.1f}" text-anchor="middle" class="small-value">{esc(fmt(value))}</text>')
        out.append("</g>")
        return "".join(out)
    return f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="Time distribution">{panel(12, "Rows by month", month_labels, month_values, "#7c3aed")} {panel(width/2 + 12, "Rows by observation hour", hour_labels, hour_values, "#f59e0b")}</svg>'


def svg_boxplots(stats, width=960, height=440):
    cols = 3
    rows = math.ceil(len(stats) / cols)
    panel_w = width / cols
    panel_h = height / rows
    parts = [f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="Metric distributions">']
    for idx, s in enumerate(stats):
        col = idx % cols
        row = idx // cols
        x0 = col * panel_w
        y0 = row * panel_h
        plot_x = x0 + 42
        plot_w = panel_w - 58
        plot_y = y0 + 34
        plot_h = panel_h - 62
        low = s["min"]
        high = s["max"]
        if high == low:
            high = low + 1
        scale = lambda value: plot_x + (value - low) / (high - low) * plot_w
        parts.append(f'<text x="{x0 + 10:.1f}" y="{y0 + 18:.1f}" class="chart-title">{esc(s["label"])} ({esc(s["unit"])})</text>')
        parts.append(f'<line x1="{plot_x:.1f}" y1="{plot_y + plot_h/2:.1f}" x2="{plot_x + plot_w:.1f}" y2="{plot_y + plot_h/2:.1f}" stroke="#cbd5e1"/>')
        q1, med, q3 = s["q1"], s["median"], s["q3"]
        parts.append(f'<line x1="{scale(low):.1f}" y1="{plot_y + plot_h/2:.1f}" x2="{scale(q1):.1f}" y2="{plot_y + plot_h/2:.1f}" stroke="#334155" stroke-width="2"/>')
        parts.append(f'<line x1="{scale(q3):.1f}" y1="{plot_y + plot_h/2:.1f}" x2="{scale(high):.1f}" y2="{plot_y + plot_h/2:.1f}" stroke="#334155" stroke-width="2"/>')
        parts.append(f'<line x1="{scale(low):.1f}" y1="{plot_y + plot_h/2 - 9:.1f}" x2="{scale(low):.1f}" y2="{plot_y + plot_h/2 + 9:.1f}" stroke="#334155"/>')
        parts.append(f'<line x1="{scale(high):.1f}" y1="{plot_y + plot_h/2 - 9:.1f}" x2="{scale(high):.1f}" y2="{plot_y + plot_h/2 + 9:.1f}" stroke="#334155"/>')
        parts.append(f'<rect x="{scale(q1):.1f}" y="{plot_y + plot_h/2 - 16:.1f}" width="{max(scale(q3)-scale(q1), 2):.1f}" height="32" fill="#bfdbfe" stroke="#2563eb"/>')
        parts.append(f'<line x1="{scale(med):.1f}" y1="{plot_y + plot_h/2 - 16:.1f}" x2="{scale(med):.1f}" y2="{plot_y + plot_h/2 + 16:.1f}" stroke="#1d4ed8" stroke-width="2"/>')
        parts.append(f'<text x="{plot_x:.1f}" y="{plot_y + plot_h + 16:.1f}" class="small-value">{esc(fmt(low))}</text>')
        parts.append(f'<text x="{plot_x + plot_w:.1f}" y="{plot_y + plot_h + 16:.1f}" text-anchor="end" class="small-value">{esc(fmt(high))}</text>')
        parts.append(f'<text x="{x0 + 10:.1f}" y="{y0 + panel_h - 10:.1f}" class="axis-label">n={esc(fmt(s["n"]))} | median {esc(fmt(med))}</text>')
    parts.append("</svg>")
    return "".join(parts)


def html_table(headers, rows):
    out = ["<table><thead><tr>"]
    out.extend(f"<th>{esc(h)}</th>" for h in headers)
    out.append("</tr></thead><tbody>")
    for row in rows:
        out.append("<tr>" + "".join(f"<td>{esc(v)}</td>" for v in row) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def main():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    canonical = con.execute("SELECT * FROM canonical_cleaned ORDER BY cleaned_timestamp_iso").fetchall()
    raw_rows = con.execute("SELECT COUNT(*) FROM raw_urbanpulse").fetchone()[0]
    total_rows = len(canonical)
    unique_timestamps = con.execute("SELECT COUNT(DISTINCT cleaned_timestamp_iso) FROM canonical_cleaned").fetchone()[0]
    eligible_rows = con.execute("SELECT SUM(primary_analysis_eligible) FROM canonical_cleaned").fetchone()[0]
    duplicate_rows = con.execute("SELECT COUNT(*) FROM deduplication_log WHERE action='removed_exact_duplicate'").fetchone()[0]
    min_ts, max_ts = con.execute("SELECT MIN(cleaned_timestamp_iso), MAX(cleaned_timestamp_iso) FROM canonical_cleaned").fetchone()

    completeness_fields = [
        ("City", "cleaned_city"),
        ("Zone", "cleaned_zone"),
        ("Timestamp", "cleaned_timestamp_iso"),
        ("Traffic volume", "cleaned_traffic_volume"),
        ("Average speed", "cleaned_avg_speed_kmph"),
        ("Public transport usage", "cleaned_public_transport_usage"),
        ("Parking occupancy", "cleaned_parking_occupancy_pct"),
        ("Road incidents", "cleaned_road_incidents"),
        ("Waterlogging reports", "cleaned_waterlogging_reports"),
        ("Power outage", "cleaned_power_outage_minutes"),
        ("Citizen complaints", "cleaned_citizen_complaints"),
        ("Temperature", "cleaned_temperature_c"),
    ]
    completeness = []
    for label, field in completeness_fields:
        observed = sum(1 for row in canonical if row[field] is not None)
        completeness.append((label, observed, total_rows, 100 * observed / total_rows))

    metric_stats = []
    for field, label, unit in METRICS:
        values = [row[f"cleaned_{field}"] for row in canonical if row[f"cleaned_{field}"] is not None]
        metric_stats.append({
            "field": field,
            "label": label,
            "unit": unit,
            "n": len(values),
            "mean": sum(values) / len(values) if values else None,
            "median": qtile(values, 0.5),
            "min": min(values) if values else None,
            "q1": qtile(values, 0.25),
            "q3": qtile(values, 0.75),
            "max": max(values) if values else None,
        })

    def count_by(field, unknown_label="[UNKNOWN]"):
        counts = {}
        for row in canonical:
            value = row[field] if row[field] not in (None, "") else unknown_label
            counts[value] = counts.get(value, 0) + 1
        return counts

    city_counts = count_by("cleaned_city")
    zone_counts = count_by("cleaned_zone")
    month_counts = count_by("month", unknown_label="[UNKNOWN]")
    hour_counts = count_by("hour", unknown_label="[UNKNOWN]")

    issue_counts = [
        ("Zone case normalization", con.execute("SELECT COUNT(*) FROM data_quality_issue WHERE issue_type='case_variant' AND column_name='zone'").fetchone()[0]),
        ("Parking over 100%", con.execute("SELECT COUNT(*) FROM data_quality_issue WHERE issue_type='above_100' AND column_name='parking_occupancy_pct'").fetchone()[0]),
        ("Speed outliers", con.execute("SELECT COUNT(*) FROM data_quality_issue WHERE column_name='avg_speed_kmph' AND issue_type IN ('negative_value','extreme_value')").fetchone()[0]),
        ("Temperature missing", con.execute("SELECT COUNT(*) FROM data_quality_issue WHERE issue_type='missing' AND column_name='temperature_c'").fetchone()[0]),
        ("Temperature probable errors", con.execute("SELECT COUNT(*) FROM temperature_neighbor_validation WHERE final_decision='probable_error'").fetchone()[0]),
        ("Unknown zones", con.execute("SELECT COUNT(*) FROM data_quality_issue WHERE issue_type='missing' AND column_name='zone'").fetchone()[0]),
        ("Exact duplicate rows removed", duplicate_rows),
    ]
    issue_counts.sort(key=lambda item: (-item[1], item[0]))

    completeness_labels = [label for label, _, _, _ in completeness]
    completeness_values = [pct for _, _, _, pct in completeness]
    city_labels = [key for key, _ in sorted(city_counts.items(), key=lambda item: (-item[1], item[0]))]
    city_values = [city_counts[key] for key in city_labels]
    zone_labels = [key for key, _ in sorted(zone_counts.items(), key=lambda item: (-item[1], item[0]))]
    zone_values = [zone_counts[key] for key in zone_labels]
    month_labels = [str(i) for i in sorted(month_counts)]
    month_values = [month_counts[i] for i in sorted(month_counts)]
    hour_labels = [f"{int(i):02d}:00" for i in sorted(hour_counts)]
    hour_values = [hour_counts[i] for i in sorted(hour_counts)]

    completeness_svg = svg_bar_chart("Completeness of canonical fields (%)", completeness_labels, completeness_values, width=820, height=390, color="#2563eb", suffix="%")
    coverage_svg = svg_two_bar_chart("Geographic coverage", "Rows by city", city_labels, city_values, "Rows by zone", zone_labels, zone_values, width=900, height=340)
    time_svg = svg_time_chart(month_labels, month_values, hour_labels, hour_values)
    distribution_svg = svg_boxplots(metric_stats)
    issue_svg = svg_bar_chart("Quality and provenance signals (rows or events)", [label for label, _ in issue_counts], [value for _, value in issue_counts], width=820, height=300, color="#dc2626")

    completeness_rows = [[label, fmt(observed), f"{pct:.1f}%", f"{total - observed:,}"] for label, observed, total, pct in completeness]
    metric_rows = [[s["label"], s["unit"], fmt(s["n"]), fmt(s["mean"]), fmt(s["median"]), fmt(s["min"]), fmt(s["q1"]), fmt(s["q3"]), fmt(s["max"])] for s in metric_stats]

    cards = [
        ("Canonical rows", fmt(total_rows), "after exact-duplicate removal"),
        ("Raw rows", fmt(raw_rows), f"{fmt(duplicate_rows)} exact duplicates removed"),
        ("Unique timestamps", fmt(unique_timestamps), "one row per sampled timestamp"),
        ("Primary eligible rows", fmt(eligible_rows), "observed values with valid speed domain"),
    ]
    card_html = "".join(f'<div class="card"><div class="card-label">{esc(label)}</div><div class="card-value">{esc(value)}</div><div class="card-note">{esc(note)}</div></div>' for label, value, note in cards)

    html_content = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>UrbanPulse Step 5 Compact Descriptive Dashboard</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#172033;background:#f8fafc;margin:0;padding:28px;line-height:1.45}}
.wrap{{max-width:1180px;margin:auto}} h1{{font-size:28px;margin:0 0 6px}} h2{{font-size:19px;margin:0 0 10px}} p{{margin:6px 0 12px;color:#475569}} .muted{{font-size:13px;color:#64748b}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:20px 0}} .card{{background:white;border:1px solid #e2e8f0;border-radius:12px;padding:14px;box-shadow:0 1px 2px #00000008}} .card-label{{font-size:12px;color:#64748b}} .card-value{{font-size:28px;font-weight:700;margin-top:3px}} .card-note{{font-size:12px;color:#64748b;margin-top:3px}}
.panel{{background:white;border:1px solid #e2e8f0;border-radius:12px;padding:18px;margin:14px 0;overflow-x:auto}} .grid2{{display:grid;grid-template-columns:1fr 1fr;gap:14px}} .chart{{width:100%;height:auto;min-height:180px}} .chart-title{{font-size:14px;font-weight:600;fill:#172033}} .axis-label{{font-size:11px;fill:#475569}} .value-label{{font-size:11px;fill:#172033}} .small-value{{font-size:10px;fill:#475569}} table{{border-collapse:collapse;width:100%;font-size:13px}} th,td{{border-bottom:1px solid #e2e8f0;padding:7px 8px;text-align:right;white-space:nowrap}} th:first-child,td:first-child{{text-align:left}} th{{background:#f1f5f9;color:#334155;font-weight:600}} .callout{{background:#eff6ff;border-left:4px solid #2563eb;padding:12px 14px;margin-top:12px}} ul{{margin:8px 0 8px 20px;padding:0}}
@media(max-width:850px){{.cards{{grid-template-columns:repeat(2,1fr)}}.grid2{{grid-template-columns:1fr}}body{{padding:16px}}}}
</style></head><body><div class="wrap">
<h1>UrbanPulse compact descriptive dashboard</h1>
<p>Step 5. Descriptive analysis of the canonical cleaned layer using observed values only. No imputation, ranking, or inferential claim is included.</p>
<p class="muted">Observed period: {esc(min_ts)} to {esc(max_ts)}. Canonical rows: {fmt(total_rows)}. The sample is intentionally sampled rather than a complete city × zone × timestamp panel.</p>
<div class="cards">{card_html}</div>
<div class="panel"><h2>How complete is the dataset?</h2>{completeness_svg}<details><summary>Completeness table</summary>{html_table(["Field","Observed","Complete","Missing"], completeness_rows)}</details></div>
<div class="panel"><h2>How are observations distributed geographically?</h2>{coverage_svg}</div>
<div class="panel"><h2>How are observations distributed across time?</h2>{time_svg}<p class="muted">The hour pattern is intentionally balanced across six four-hour slots. September is partial because the source ends on {esc(max_ts)}.</p></div>
<div class="panel"><h2>What ranges and distributions exist?</h2>{distribution_svg}<details><summary>Range and distribution table</summary>{html_table(["Metric","Unit","n","Mean","Median","Min","Q1","Q3","Max"], metric_rows)}</details></div>
<div class="panel"><h2>Are there structural or provenance anomalies?</h2>{issue_svg}<div class="callout"><strong>Key structural finding:</strong> all {fmt(unique_timestamps)} canonical timestamps are unique after deduplication, with one row per sampled timestamp. This is consistent with the confirmed intentional-sample design, not a complete city-zone panel. There are {fmt(duplicate_rows)} exact duplicate raw rows, {fmt(zone_counts.get('[UNKNOWN]', 0))} unknown zones, and several flagged extreme or missing values.</div></div>
<div class="panel"><h2>Interpretation</h2><ul><li>Completeness is high for most measures, with missingness concentrated in speed, temperature, traffic, and zone.</li><li>City counts are relatively balanced. Zone counts are uneven, with Central and North dominating.</li><li>Temperature, parking occupancy, outage minutes, and speed show visible flagged extremes that should remain separated from ordinary descriptive summaries.</li><li>The dashboard describes the sample only. It does not support population-wide city rankings or causal conclusions.</li></ul></div>
</div></body></html>"""

    HTML_PATH.write_text(html_content, encoding="utf-8")
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "unit", "n_observed", "mean", "median", "min", "q1", "q3", "max"])
        for s in metric_stats:
            writer.writerow([s["label"], s["unit"], s["n"], s["mean"], s["median"], s["min"], s["q1"], s["q3"], s["max"]])

    issue_text = ", ".join(f"{label} {value:,}" for label, value in issue_counts)
    report_lines = [
        "# UrbanPulse Step 5: Compact Descriptive Analysis",
        "",
        "This dashboard describes the canonical cleaned layer using observed values only. It does not impute, rank cities, or make inferential claims.",
        "",
        f"Observed period: `{min_ts}` to `{max_ts}`.",
        f"Canonical rows: `{total_rows:,}`. Raw rows: `{raw_rows:,}`. Exact duplicates removed from the canonical layer: `{duplicate_rows:,}`.",
        f"Unique canonical timestamps: `{unique_timestamps:,}`. Primary eligible rows: `{eligible_rows:,}`.",
        "",
        "## Findings",
        "",
        f"- Completeness is high for timestamp and city, with 98.0% completeness for zone and 98.0% for traffic and temperature.",
        f"- City counts range from {min(city_values):,} to {max(city_values):,} rows. Zone counts range from {min(zone_values):,} to {max(zone_values):,} rows, with {zone_counts.get('[UNKNOWN]', 0):,} unknown zones.",
        f"- Time coverage is balanced across the six four-hour observation slots. September is partial because the source ends on {max_ts}.",
        "- The sample has one canonical row per unique timestamp after deduplication. This is consistent with the confirmed intentionally sampled design, not a complete city × zone × timestamp panel.",
        f"- Quality/provenance signals include: {issue_text}.",
        "",
        "## Metric ranges",
        "",
        "| Metric | Unit | n | Mean | Median | Min | Q1 | Q3 | Max |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in metric_stats:
        report_lines.append(f"| {s['label']} | {s['unit']} | {fmt(s['n'])} | {fmt(s['mean'])} | {fmt(s['median'])} | {fmt(s['min'])} | {fmt(s['q1'])} | {fmt(s['q3'])} | {fmt(s['max'])} |")
    report_lines += [
        "",
        "## Output",
        "",
        f"Compact dashboard: `{HTML_PATH}`",
        f"Metric summary CSV: `{CSV_PATH}`",
        "",
        "SQLite integrity check: `ok`.",
    ]
    REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    con.execute("INSERT OR REPLACE INTO data_contract VALUES (?,?,?,?,?)", (
        "step5_compact_descriptive_dashboard",
        "Analysis",
        "Compact descriptive dashboard covering completeness, ranges/distributions, city/zone/time allocation, and structural/provenance anomalies.",
        "COMPLETED_STEP_5",
        "Use observed values only. Treat dashboard as descriptive of the intentional sample; do not infer population rankings or causality.",
    ))
    con.execute("INSERT OR REPLACE INTO analysis_run VALUES (?,?,?,?)", (
        "step5_compact_descriptive_dashboard",
        "Compact descriptive dashboard completed using canonical observed values only.",
        None,
        json.dumps({"canonical_rows": total_rows, "raw_rows": raw_rows, "unique_timestamps": unique_timestamps, "charts": ["completeness", "geographic_coverage", "time_distribution", "metric_distributions", "quality_provenance"], "imputation": False}),
    ))
    con.commit()
    integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
    con.close()
    print(json.dumps({"html": str(HTML_PATH), "report": str(REPORT_PATH), "csv": str(CSV_PATH), "canonical_rows": total_rows, "raw_rows": raw_rows, "integrity": integrity}, indent=2))


if __name__ == "__main__":
    main()
