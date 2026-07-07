import csv
import io
import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.websocket_manager import manager
from app.models.export import Export, ExportFormat, ExportStatus
from app.models.notification import Notification
from app.services import report_service

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _fmt(n: Decimal | float | int) -> str:
    """Format a number as USD."""
    return f"${float(n):,.2f}"


def _pct(n: float) -> str:
    return f"{n:.1f}%"


def _filename(report_type: str, fmt: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{report_type}_{now}.{fmt}"


# ──────────────────────────────────────────────
# CSV generators
# ──────────────────────────────────────────────


def _csv_income_vs_expenses(data: dict) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Income vs Expenses Report"])
    writer.writerow(["Date From", data["date_from"]])
    writer.writerow(["Date To", data["date_to"]])
    writer.writerow([])
    writer.writerow(["Metric", "Amount"])
    writer.writerow(["Total Income", _fmt(data["total_income"])])
    writer.writerow(["Total Expenses", _fmt(data["total_expenses"])])
    writer.writerow(["Net", _fmt(data["net"])])
    if data.get("monthly_breakdown"):
        writer.writerow([])
        writer.writerow(["Month", "Income", "Expenses", "Net"])
        for m in data["monthly_breakdown"]:
            writer.writerow([m["month"], _fmt(m["income"]), _fmt(m["expenses"]), _fmt(m["net"])])
    return output.getvalue()


def _csv_category_breakdown(data: dict) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Category Breakdown Report"])
    writer.writerow(["Date From", data["date_from"]])
    writer.writerow(["Date To", data["date_to"]])
    writer.writerow([])
    writer.writerow(["Category", "Total Amount", "Transactions", "Percentage"])
    for cat in data["categories"]:
        writer.writerow([cat["category_name"], _fmt(cat["total_amount"]), cat["transaction_count"], _pct(cat["percentage"])])
    writer.writerow([])
    writer.writerow(["Total Income", _fmt(data["total_income"])])
    writer.writerow(["Total Expenses", _fmt(data["total_expenses"])])
    writer.writerow(["Net", _fmt(data["net"])])
    return output.getvalue()


def _csv_monthly_trends(data: dict) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Monthly Trends Report"])
    writer.writerow([])
    writer.writerow(["Month", "Income", "Expenses", "Net"])
    for m in data["data"]:
        writer.writerow([m["month"], _fmt(m["income"]), _fmt(m["expenses"]), _fmt(m["net"])])
    return output.getvalue()


def _csv_net_worth(data: dict) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Net Worth Report"])
    writer.writerow(["As Of", data["as_of_date"]])
    writer.writerow([])
    writer.writerow(["Metric", "Amount"])
    writer.writerow(["Total Assets", _fmt(data["total_assets"])])
    writer.writerow(["Total Liabilities", _fmt(data["total_liabilities"])])
    writer.writerow(["Net Worth", _fmt(data["net_worth"])])
    writer.writerow(["Portfolio Market Value", _fmt(data["portfolio_market_value"])])
    writer.writerow([])
    writer.writerow(["Account Type", "Count", "Total Balance"])
    for at in data["by_account_type"]:
        writer.writerow([at["account_type"], at["count"], _fmt(at["total_balance"])])
    return output.getvalue()


_CSV_GENERATORS: dict[str, callable] = {
    "income_vs_expenses": _csv_income_vs_expenses,
    "category_breakdown": _csv_category_breakdown,
    "monthly_trends": _csv_monthly_trends,
    "net_worth": _csv_net_worth,
}

# ──────────────────────────────────────────────
# PDF generators (ReportLab)
# ──────────────────────────────────────────────


def _pdf_income_vs_expenses(data: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Income vs Expenses Report", styles["Title"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Period: {data['date_from']} — {data['date_to']}", styles["Normal"]))
    elements.append(Spacer(1, 24))

    summary_data = [
        ["Metric", "Amount"],
        ["Total Income", _fmt(data["total_income"])],
        ["Total Expenses", _fmt(data["total_expenses"])],
        ["Net", _fmt(data["net"])],
    ]
    t = Table(summary_data, colWidths=[2.5 * inch, 2 * inch])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a73e8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]))
    elements.append(t)

    if data.get("monthly_breakdown"):
        elements.append(Spacer(1, 24))
        elements.append(Paragraph("Monthly Breakdown", styles["Heading2"]))
        rows = [["Month", "Income", "Expenses", "Net"]]
        for m in data["monthly_breakdown"]:
            rows.append([str(m["month"]), _fmt(m["income"]), _fmt(m["expenses"]), _fmt(m["net"])])
        t2 = Table(rows, colWidths=[1.5 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch])
        t2.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a73e8")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ]))
        elements.append(t2)

    doc.build(elements)
    return buf.getvalue()


def _pdf_category_breakdown(data: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Category Breakdown Report", styles["Title"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Period: {data['date_from']} — {data['date_to']}", styles["Normal"]))
    elements.append(Spacer(1, 24))

    rows = [["Category", "Amount", "Transactions", "%"]]
    for cat in data["categories"]:
        rows.append([cat["category_name"], _fmt(cat["total_amount"]), str(cat["transaction_count"]), _pct(cat["percentage"])])
    t = Table(rows, colWidths=[2 * inch, 1.2 * inch, 1 * inch, 1 * inch])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a73e8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]))
    elements.append(t)

    elements.append(Spacer(1, 12))
    summary = [
        ["Total Income", _fmt(data["total_income"])],
        ["Total Expenses", _fmt(data["total_expenses"])],
        ["Net", _fmt(data["net"])],
    ]
    t2 = Table(summary, colWidths=[2 * inch, 1.2 * inch])
    t2.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]))
    elements.append(t2)

    doc.build(elements)
    return buf.getvalue()


def _pdf_monthly_trends(data: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Monthly Trends Report", styles["Title"]))
    elements.append(Spacer(1, 24))

    rows = [["Month", "Income", "Expenses", "Net"]]
    for m in data["data"]:
        rows.append([str(m["month"]), _fmt(m["income"]), _fmt(m["expenses"]), _fmt(m["net"])])
    t = Table(rows, colWidths=[1.5 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a73e8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]))
    elements.append(t)

    doc.build(elements)
    return buf.getvalue()


def _pdf_net_worth(data: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("Net Worth Report", styles["Title"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"As of: {data['as_of_date']}", styles["Normal"]))
    elements.append(Spacer(1, 24))

    summary = [
        ["Metric", "Amount"],
        ["Total Assets", _fmt(data["total_assets"])],
        ["Total Liabilities", _fmt(data["total_liabilities"])],
        ["Net Worth", _fmt(data["net_worth"])],
        ["Portfolio Market Value", _fmt(data["portfolio_market_value"])],
    ]
    t = Table(summary, colWidths=[2.5 * inch, 2 * inch])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a73e8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]))
    elements.append(t)

    elements.append(Spacer(1, 24))
    elements.append(Paragraph("By Account Type", styles["Heading2"]))
    rows = [["Account Type", "Count", "Total Balance"]]
    for at in data["by_account_type"]:
        rows.append([at["account_type"], str(at["count"]), _fmt(at["total_balance"])])
    t2 = Table(rows, colWidths=[2 * inch, 1 * inch, 1.5 * inch])
    t2.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a73e8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]))
    elements.append(t2)

    doc.build(elements)
    return buf.getvalue()


_PDF_GENERATORS: dict[str, callable] = {
    "income_vs_expenses": _pdf_income_vs_expenses,
    "category_breakdown": _pdf_category_breakdown,
    "monthly_trends": _pdf_monthly_trends,
    "net_worth": _pdf_net_worth,
}

# ──────────────────────────────────────────────
# Main service
# ──────────────────────────────────────────────


def generate_export(
    db: Session,
    *,
    user_id: uuid.UUID,
    report_type: str,
    fmt: str,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> Export:
    export = Export(
        user_id=user_id,
        report_type=report_type,
        format=ExportFormat(fmt),
        status=ExportStatus.PROCESSING,
        params={
            "report_type": report_type,
            "format": fmt,
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
        },
    )
    db.add(export)
    db.flush()

    try:
        data = _fetch_report_data(db, user_id, report_type, date_from, date_to)
        content: str | bytes
        if fmt == "csv":
            generator = _CSV_GENERATORS.get(report_type)
            if not generator:
                raise ValueError(f"Unsupported report type for CSV: {report_type}")
            content = generator(data)
            content_bytes = content.encode("utf-8")
        else:
            generator = _PDF_GENERATORS.get(report_type)
            if not generator:
                raise ValueError(f"Unsupported report type for PDF: {report_type}")
            content_bytes = generator(data)

        filename = _filename(report_type, fmt)
        file_path = _store_file(user_id, export.id, filename, content_bytes)
        export.status = ExportStatus.COMPLETED
        export.filename = filename
        export.file_path = file_path
    except Exception as e:
        export.status = ExportStatus.FAILED
        export.error_message = str(e)
        db.flush()
        raise

    _notify_user(db, user_id, export)
    return export


def _fetch_report_data(
    db: Session,
    user_id: uuid.UUID,
    report_type: str,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> dict[str, Any]:
    today = date.today()
    if date_from is None:
        date_from = date(today.year, 1, 1)
    if date_to is None:
        date_to = today

    fetchers: dict[str, callable] = {
        "income_vs_expenses": lambda: report_service.get_income_vs_expenses(
            db, user_id=user_id, date_from=date_from, date_to=date_to, monthly=True
        ),
        "category_breakdown": lambda: report_service.get_category_breakdown(
            db, user_id=user_id, date_from=date_from, date_to=date_to
        ),
        "monthly_trends": lambda: report_service.get_monthly_trends(
            db, user_id=user_id, months=12
        ),
        "net_worth": lambda: report_service.get_net_worth(
            db, user_id=user_id
        ),
    }
    fetcher = fetchers.get(report_type)
    if not fetcher:
        raise ValueError(f"Unknown report type: {report_type}")
    return fetcher()


def _store_file(user_id: uuid.UUID, export_id: uuid.UUID, filename: str, content: bytes) -> str:
    export_dir = os.path.join(settings.EXPORT_DIR, str(user_id))
    os.makedirs(export_dir, exist_ok=True)
    file_path = os.path.join(export_dir, filename)
    with open(file_path, "wb") as f:
        f.write(content)
    return file_path


def _notify_user(db: Session, user_id: uuid.UUID, export: Export) -> None:
    notification = Notification(
        user_id=user_id,
        type="report_ready",
        title="Report Ready for Download",
        body=f"Your {export.report_type.replace('_', ' ')} report ({export.format.value}) is ready.",
        payload={"export_id": str(export.id), "format": export.format.value},
    )
    db.add(notification)
    db.flush()

    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(
                manager.send_to_user(user_id, {
                    "type": "notification",
                    "notification_type": "report_ready",
                    "title": notification.title,
                    "body": notification.body,
                    "payload": notification.payload,
                })
            )
    except RuntimeError:
        pass
