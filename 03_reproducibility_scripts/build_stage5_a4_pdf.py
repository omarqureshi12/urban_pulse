import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas


PROJECT = Path('/Users/apple/Desktop/urban city project')
OUT = PROJECT / '02_final_outputs/urbanpulse_phase5_dashboard_A4.pdf'


def read_json(name):
    return json.loads(Path('/tmp') .joinpath(name).read_text())


city = read_json('urbanpulse_stage5_city.json')
zone = read_json('urbanpulse_stage5_zone.json')
month = read_json('urbanpulse_stage5_month.json')

PAGE_W, PAGE_H = landscape(A4)
NAVY = colors.HexColor('#1F4E78')
BLUE = colors.HexColor('#4472C4')
TEAL = colors.HexColor('#2F75B5')
ORANGE = colors.HexColor('#ED7D31')
LIGHT = colors.HexColor('#D9E2F3')
GRID = colors.HexColor('#D9E2F3')
TEXT = colors.HexColor('#222222')
MUTED = colors.HexColor('#666666')


def fmt(value):
    return f'{int(value):,}'


def draw_table(c, x, y_top, width, title, rows):
    title_h = 16
    row_h = 13
    c.setFillColor(LIGHT)
    c.rect(x, y_top - title_h, width, title_h, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.setFont('Helvetica-Bold', 8)
    c.drawString(x + 4, y_top - 11, title)
    col_w = [width * 0.48, width * 0.31, width * 0.21]
    headers = ['Label', 'Traffic volume', 'Records']
    y = y_top - title_h - row_h
    c.setFillColor(NAVY)
    c.rect(x, y, width, row_h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 7)
    xx = x
    for header, cw in zip(headers, col_w):
        c.drawString(xx + 3, y + 4, header)
        xx += cw
    for item in rows:
        y -= row_h
        c.setFillColor(colors.white)
        c.rect(x, y, width, row_h, fill=1, stroke=0)
        c.setStrokeColor(GRID)
        c.rect(x, y, width, row_h, fill=0, stroke=1)
        c.setFillColor(TEXT)
        c.setFont('Helvetica', 7)
        c.drawString(x + 3, y + 4, str(item['label']))
        c.drawRightString(x + col_w[0] + col_w[1] - 3, y + 4, fmt(item['traffic_volume']))
        c.drawRightString(x + width - 3, y + 4, fmt(item['records']))
        xx = x
        for cw in col_w[:-1]:
            xx += cw
            c.setStrokeColor(GRID)
            c.line(xx, y, xx, y + row_h)
    return y - 5


def draw_bar_chart(c, x, y, width, height, title, rows, color):
    c.setStrokeColor(GRID)
    c.rect(x, y, width, height, fill=0, stroke=1)
    c.setFillColor(TEXT)
    c.setFont('Helvetica-Bold', 9)
    c.drawCentredString(x + width / 2, y + height - 14, title)
    left = x + 55
    right = x + width - 12
    bottom = y + 24
    top = y + height - 28
    max_v = max(r['traffic_volume'] for r in rows)
    bar_h = (top - bottom) / max(len(rows), 1) * 0.56
    gap = (top - bottom) / max(len(rows), 1)
    c.setFont('Helvetica', 6.5)
    for i, item in enumerate(rows):
        cy = top - i * gap - gap * 0.5
        c.setFillColor(TEXT)
        c.drawRightString(left - 4, cy - 2, str(item['label']))
        c.setFillColor(color)
        bw = (right - left) * item['traffic_volume'] / max_v
        c.rect(left, cy - bar_h / 2, bw, bar_h, fill=1, stroke=0)
    c.setStrokeColor(GRID)
    c.line(left, bottom - 4, right, bottom - 4)
    c.setFillColor(MUTED)
    c.setFont('Helvetica', 6)
    c.drawString(left, bottom - 14, '0')
    c.drawRightString(right, bottom - 14, fmt(max_v))


def draw_line_chart(c, x, y, width, height, title, rows):
    c.setStrokeColor(GRID)
    c.rect(x, y, width, height, fill=0, stroke=1)
    c.setFillColor(TEXT)
    c.setFont('Helvetica-Bold', 9)
    c.drawCentredString(x + width / 2, y + height - 14, title)
    left = x + 35
    right = x + width - 15
    bottom = y + 25
    top = y + height - 28
    vals = [r['traffic_volume'] for r in rows]
    lo, hi = 0, max(vals) * 1.08
    for tick in range(5):
        gy = bottom + (top - bottom) * tick / 4
        c.setStrokeColor(GRID)
        c.line(left, gy, right, gy)
        c.setFillColor(MUTED)
        c.setFont('Helvetica', 6)
        c.drawRightString(left - 4, gy - 2, fmt(hi * tick / 4))
    points = []
    for i, item in enumerate(rows):
        px = left + (right - left) * i / max(len(rows) - 1, 1)
        py = bottom + (top - bottom) * item['traffic_volume'] / hi
        points.append((px, py))
        c.setFillColor(MUTED)
        c.setFont('Helvetica', 6)
        c.drawCentredString(px, bottom - 13, str(item['label']))
    c.setStrokeColor(ORANGE)
    c.setLineWidth(1.5)
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        c.line(x1, y1, x2, y2)
    c.setFillColor(ORANGE)
    for px, py in points:
        c.circle(px, py, 2, fill=1, stroke=0)


c = canvas.Canvas(str(OUT), pagesize=landscape(A4))
c.setTitle('UrbanPulse Compact Dashboard - A4')
c.setAuthor('UrbanPulse project')
c.setFillColor(NAVY)
c.setFont('Helvetica-Bold', 16)
c.drawString(28, PAGE_H - 30, 'UrbanPulse Compact Dashboard')
c.setFillColor(MUTED)
c.setFont('Helvetica-Oblique', 8)
c.drawString(28, PAGE_H - 44, 'Observed-only traffic-volume summaries. City/month: 1,491 records. Zone: 1,462 known-zone records.')

table_y = PAGE_H - 55
draw_table(c, 28, table_y, 235, 'City summary', city)
draw_table(c, 303, table_y, 210, 'Zone summary', zone)
draw_table(c, 553, table_y, 260, 'Month summary', month)

draw_bar_chart(c, 28, 188, 385, 190, 'Traffic volume by city', city, BLUE)
draw_bar_chart(c, 429, 188, 385, 190, 'Traffic volume by zone', zone, TEAL)
draw_line_chart(c, 28, 28, 786, 145, 'Traffic volume by month', month)

c.setFillColor(MUTED)
c.setFont('Helvetica-Oblique', 7)
c.drawString(28, 15, 'Scope: zone view excludes 29 records with unknown zone. Imputed values are not included. Source: urbanpulse_rdbms.sqlite.')
c.showPage()
c.save()
print(OUT)
