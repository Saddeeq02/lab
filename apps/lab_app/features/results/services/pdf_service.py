# apps/lab_app/features/results/services/pdf_service.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


# ==============================
# DESIGN SYSTEM (IMPROVED)
# ==============================

SPACE_XS = 2 * mm
SPACE_SM = 5 * mm
SPACE_MD = 8 * mm
SPACE_LG = 12 * mm
SPACE_XL = 18 * mm

FONT_TITLE = ("Helvetica-Bold", 22)   # 🔼 bigger header
FONT_SUBTITLE = ("Helvetica", 11)
FONT_SECTION = ("Helvetica-Bold", 14)
FONT_BODY = ("Helvetica", 11)


def _safe_set_alpha(c: canvas.Canvas, a: float) -> None:
    try:
        c.setFillAlpha(a)
    except Exception:
        pass


def generate_bundle_pdf(
    output_path: str,
    lab_profile: dict,
    patient_row: dict,
    bundle_results: dict[str, dict],
    paper_size: str = "A4",   # ✅ NEW SUPPORT
) -> str:

    # ==============================
    # PAGE SIZE SWITCH
    # ==============================
    PAGE = A5 if paper_size.upper() == "A5" else A4

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(out), pagesize=PAGE)
    w, h = PAGE

    # ==============================
    # WATERMARK
    # ==============================
    logo_path = (lab_profile.get("logo_path") or "").strip()
    watermark = bool(lab_profile.get("watermark_enabled", True))

    if watermark and logo_path:
        try:
            img = ImageReader(logo_path)
            _safe_set_alpha(c, 0.05)
            size = (120 if PAGE == A5 else 150) * mm
            c.drawImage(img, (w - size) / 2, (h - size) / 2, size, size, mask="auto")
            _safe_set_alpha(c, 1.0)
        except Exception:
            pass

    # ==============================
    # HEADER (ENHANCED)
    # ==============================
    lab_name = lab_profile.get("lab_name", "Laboratory")
    address = lab_profile.get("address", "")
    phone = lab_profile.get("phone", "")
    email = lab_profile.get("email", "")

    top_y = h - SPACE_XL

    if logo_path:
        try:
            img = ImageReader(logo_path)
            size = 26 * mm
            c.drawImage(img, 15 * mm, h - 42 * mm, size, size, mask="auto")
            c.drawImage(img, w - 15 * mm - size, h - 42 * mm, size, size, mask="auto")
        except Exception:
            pass

    c.setFont(*FONT_TITLE)
    c.drawCentredString(w / 2, top_y, str(lab_name))

    c.setFont(*FONT_SUBTITLE)
    y_txt = top_y - SPACE_MD

    if address:
        c.drawCentredString(w / 2, y_txt, address)
        y_txt -= SPACE_SM

    contact = "  |  ".join([x for x in [phone, email] if x])
    if contact:
        c.drawCentredString(w / 2, y_txt, contact)

    c.setStrokeColor(colors.grey)
    c.setLineWidth(1.2)
    c.line(15 * mm, h - 45 * mm, w - 15 * mm, h - 45 * mm)

    # ==============================
    # PATIENT INFO (ENLARGED + SPACED)
    # ==============================
    pid = patient_row.get("Patient ID", "-")
    name = patient_row.get("Name", "-")
    sex = patient_row.get("Sex", "-")
    age = patient_row.get("Age", "-")
    dt = datetime.now().strftime("%Y-%m-%d %H:%M")

    c.setFont("Helvetica-Bold", 15)  # 🔼 bigger
    c.drawString(15 * mm, h - 52 * mm, "Patient Information")

    c.setFont("Helvetica", 12)  # 🔼 bigger body

    y_info = h - 60 * mm

    c.drawString(15 * mm, y_info, f"Name: {name}")
    c.drawString(15 * mm, y_info - SPACE_MD, f"Patient ID: {pid}")

    c.drawString(w / 2, y_info, f"Sex: {sex}")
    c.drawString(w / 2, y_info - SPACE_MD, f"Age: {age}")

    c.drawRightString(w - 15 * mm, y_info, f"Printed: {dt}")

    # 🔥 EXTRA GAP BEFORE TABLES
    y = h - 80 * mm

    # ==============================
    # RESULTS
    # ==============================
    for _, payload in bundle_results.items():

        test_name = payload.get("request", {}).get("test_name", "Test")

        # Section Title
        c.setFont(*FONT_SECTION)
        c.drawString(15 * mm, y, test_name.upper())

        c.setStrokeColor(colors.lightgrey)
        c.line(15 * mm, y - 1, w - 15 * mm, y - 1)

        y -= SPACE_LG  # 🔼 more breathing

        typ = payload.get("type")

        # ==========================
        # STRUCTURED TABLE
        # ==========================
        if typ == "structured":

            rows = payload.get("rows", [])
            data = [["Parameter", "Result", "Unit", "Ref. Range", "Flag"]]

            for r in rows:
                data.append([
                    r.get("parameter", ""),
                    r.get("result", ""),
                    r.get("unit", ""),
                    r.get("ref_range", ""),
                    r.get("flag", ""),
                ])

            tbl = Table(
                data,
                colWidths=[w * 0.30, w * 0.15, w * 0.12, w * 0.25, w * 0.12]
            )

            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF7")),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONT", (0, 1), (-1, -1), "Helvetica"),

                ("FONTSIZE", (0, 0), (-1, -1), 10),

                ("ALIGN", (1, 1), (-1, -1), "CENTER"),

                ("LEFTPADDING", (0,0), (-1,-1), 8),
                ("RIGHTPADDING", (0,0), (-1,-1), 8),
                ("TOPPADDING", (0,0), (-1,-1), 6),
                ("BOTTOMPADDING", (0,0), (-1,-1), 6),

                ("GRID", (0,0), (-1,-1), 0.25, colors.grey),

                ("ROWBACKGROUNDS", (0,1), (-1,-1), [
                    colors.white,
                    colors.whitesmoke
                ]),
            ]))

            tw, th = tbl.wrapOn(c, w - 30 * mm, y)

            if y - th < 30 * mm:
                c.showPage()
                y = h - 30 * mm

            tbl.drawOn(c, 15 * mm, y - th)
            y -= (th + SPACE_LG)

        # ==========================
        # RAW TABLE
        # ==========================
        elif typ == "table":

            grid = payload.get("grid", {})
            cells = grid.get("cells", [])

            if not cells:
                c.setFont(*FONT_BODY)
                c.drawString(15 * mm, y, "(No table data)")
                y -= SPACE_MD
                continue

            ncols = max((len(r) for r in cells), default=0)

            padded = [list(r) + [""] * (ncols - len(r)) for r in cells]

            col_w = (w - 30 * mm) / ncols
            tbl = Table(padded, colWidths=[col_w] * ncols)

            tbl.setStyle(TableStyle([
                ("FONT", (0,0), (-1,-1), "Helvetica"),
                ("FONTSIZE", (0,0), (-1,-1), 10),

                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#F0F0F0")),
                ("FONT", (0,0), (-1,0), "Helvetica-Bold"),

                ("GRID", (0,0), (-1,-1), 0.25, colors.grey),

                ("LEFTPADDING", (0,0), (-1,-1), 5),
                ("RIGHTPADDING", (0,0), (-1,-1), 5),

                ("ROWBACKGROUNDS", (0,1), (-1,-1), [
                    colors.white,
                    colors.HexColor("#FAFAFA")
                ]),
            ]))

            tw, th = tbl.wrapOn(c, w - 30 * mm, y)

            if y - th < 25 * mm:
                c.showPage()
                y = h - 25 * mm

            tbl.drawOn(c, 15 * mm, y - th)
            y -= (th + SPACE_MD)

        # ==========================
        # WRITTEN TEXT
        # ==========================
        elif typ == "written":

            text = payload.get("text", {}) or {}

            sections = [
                ("Clinical Findings", text.get("findings", "")),
                ("Interpretation", text.get("interpretation", "")),
                ("Conclusion", text.get("impression", "")),
                ("Recommendations", text.get("recommendations", "")),
            ]

            for title, body in sections:

                body = (body or "").strip()
                if not body:
                    continue

                c.setFont(*FONT_SECTION)

                if y < 25 * mm:
                    c.showPage()
                    y = h - 25 * mm

                c.drawString(15 * mm, y, title + ":")
                y -= SPACE_SM

                c.setFont(*FONT_BODY)

                words = body.split()
                line = ""

                for wd in words:
                    test = (line + " " + wd).strip()
                    if c.stringWidth(test, "Helvetica", 10) < (w - 30 * mm):
                        line = test
                    else:
                        c.drawString(18 * mm, y, line)
                        y -= SPACE_SM
                        line = wd

                if line:
                    c.drawString(18 * mm, y, line)
                    y -= SPACE_SM

                y -= SPACE_SM

        # ==========================
        # TEMPLATE TEXT
        # ==========================
        elif typ == "pc_template":

            rendered = (payload.get("rendered") or "").strip()

            c.setFont(*FONT_BODY)

            for line in rendered.split("\n"):

                line = line.strip()
                if not line:
                    y -= SPACE_SM
                    continue

                words = line.split()
                cur = ""

                for wd in words:
                    test = (cur + " " + wd).strip()
                    if c.stringWidth(test, "Helvetica", 10) < (w - 30 * mm):
                        cur = test
                    else:
                        c.drawString(15 * mm, y, cur)
                        y -= SPACE_SM
                        cur = wd

                if cur:
                    c.drawString(15 * mm, y, cur)
                    y -= SPACE_SM

            y -= SPACE_MD

        else:
            c.setFont(*FONT_BODY)
            c.drawString(15 * mm, y, "(Unsupported result type)")
            y -= SPACE_MD

    # ==============================
    # SIGNATURE
    # ==============================
    scientist = lab_profile.get("scientist_name", "")
    qual = lab_profile.get("scientist_qualification", "")
    notes = lab_profile.get("report_notes", "")

    y_sig = 32 * mm

    c.setStrokeColor(colors.grey)
    c.line(15 * mm, y_sig + 10 * mm, 70 * mm, y_sig + 10 * mm)

    c.setFont("Helvetica-Bold", 10)
    c.drawString(15 * mm, y_sig + SPACE_SM, scientist)

    c.setFont("Helvetica", 9)
    c.drawString(15 * mm, y_sig, qual)

    if notes:
        c.setFont("Helvetica-Oblique", 9)
        c.drawRightString(w - 15 * mm, y_sig, f"Notes: {notes}")

    # ==============================
    # FOOTER
    # ==============================
    c.setStrokeColor(colors.grey)
    c.line(15 * mm, 28 * mm, w - 15 * mm, 28 * mm)

    c.setFont("Helvetica", 9)
    c.drawString(15 * mm, 22 * mm,
        "Authorized Laboratory Report — Generated by Solunex Technologies")

    c.drawString(15 * mm, 17 * mm,
        "Visit: www.iandelaboratory.com for online result access")

    c.save()
    return str(out)