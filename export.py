"""export.py - Build CSV and Excel files from a list of business dicts."""
import csv
import io
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

COLUMNS = [
    ("name", "Business Name", 32),
    ("category", "Category", 22),
    ("address", "Address", 45),
    ("phone", "Phone", 18),
    ("website", "Website", 35),
    ("maps_url", "Google Maps URL", 40),
    ("rating", "Rating", 9),
    ("reviews", "Total Reviews", 14),
]


def to_csv_bytes(rows):
    """CSV with a UTF-8 BOM so Excel opens non-English text correctly."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([label for _, label, _ in COLUMNS])
    for r in rows:
        writer.writerow([r.get(key, "") for key, _, _ in COLUMNS])
    return buf.getvalue().encode("utf-8-sig")


def to_xlsx_bytes(rows):
    """Formatted .xlsx with a styled header, column widths and clickable links."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Leads"
    ws.append([label for _, label, _ in COLUMNS])

    head_fill = PatternFill("solid", fgColor="1D4ED8")
    for i, (_, _, width) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=i)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = head_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[cell.column_letter].width = width

    for r in rows:
        ws.append([r.get(key, "") for key, _, _ in COLUMNS])
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            if isinstance(cell.value, str) and cell.value.startswith("http"):
                cell.hyperlink = cell.value
                cell.font = Font(color="1D4ED8", underline="single")
    ws.freeze_panes = "A2"

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()