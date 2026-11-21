"""Fluturașul de salariu în PDF, făcut pe server (reportlab, fără browser): pentru e-mail și pentru „Descarcă PDF”.

Același conținut ca forma de tipar „Fișa de calcul” (apps.payroll.printing.slips_of): pe fiecare raport de muncă al
angajatului — acumulările și reținerile; apoi decontarea lunii — CNAM, scutirea și impozitul reținute la plată, netul,
avansul și salariul achitate, restul de plată. Fontul DejaVu Sans (în
apps/payroll/fonts, licența alături) are diacriticele românești și literele rusești.
"""
import io
from pathlib import Path

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.core.models import Company

from .models import Payment
from .printing import MONTHS, payment_slip_lines, slips_of

FONTS = Path(__file__).resolve().parent / "fonts"
_registered = False


def _fonts():
    global _registered
    if not _registered:
        pdfmetrics.registerFont(TTFont("DejaVu", str(FONTS / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(FONTS / "DejaVuSans-Bold.ttf")))
        pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold")
        _registered = True


def _styles():
    base = ParagraphStyle("base", fontName="DejaVu", fontSize=8.5, leading=11)
    return {
        "base": base,
        "title": ParagraphStyle("title", parent=base, fontName="DejaVu-Bold", fontSize=12, leading=15),
        "sub": ParagraphStyle("sub", parent=base, textColor=colors.HexColor("#555555")),
        "bold": ParagraphStyle("bold", parent=base, fontName="DejaVu-Bold"),
        "right": ParagraphStyle("right", parent=base, alignment=TA_RIGHT),
        "right_bold": ParagraphStyle("right_bold", parent=base, fontName="DejaVu-Bold", alignment=TA_RIGHT),
        "muted": ParagraphStyle("muted", parent=base, fontSize=7.5, leading=9.5, textColor=colors.HexColor("#666666")),
    }


def _esc(text) -> str:
    return str(text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


GRID = TableStyle([
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6F2EB")),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
])


def _job_block(slip: dict, st: dict, width: float) -> list:
    """Un raport de muncă: antetul (funcția, norma), acumulările și reținerile alăturate, totalurile."""
    head = Paragraph(f"<b>{_esc(slip['occupation'])}</b>{' (' + _esc(slip['kind']) + ')' if slip['kind'] else ''}, "
                     f"{_esc(slip['subdivision'])} · norma {_esc(slip['rate'])} · salariul de funcție {_esc(slip['salary'])} · "
                     f"zile / ore {_esc(slip['days'])} / {_esc(slip['hours'])}"
                     + (" · <b>impozitat final (IT Park)</b>" if slip.get("it_park") else ""), st["base"])
    half = (width - 4 * mm) / 2
    acc_rows = [[Paragraph("Acumulări", st["bold"]), Paragraph("Cant.", st["bold"]), Paragraph("%", st["bold"]),
                 Paragraph("Suma", st["right_bold"])]]
    for a in slip["accruals"]:
        name = _esc(a["name"]) + (f"<br/><font size=7 color='#666666'>{_esc(a['note'])}</font>" if a["note"] else "")
        acc_rows.append([Paragraph(name, st["base"]), Paragraph(_esc(a["qty"]), st["right"]), Paragraph(_esc(a["pct"]), st["right"]),
                         Paragraph(_esc(a["amount"]), st["right"])])
    acc_rows.append([Paragraph("Total calculat", st["bold"]), "", "", Paragraph(_esc(slip["gross"]), st["right_bold"])])
    acc = Table(acc_rows, colWidths=[half - 46 * mm, 13 * mm, 12 * mm, 21 * mm])
    acc.setStyle(GRID)
    ded_rows = [[Paragraph("Rețineri", st["bold"]), Paragraph("Suma", st["right_bold"])]]
    for d in slip["deductions_list"]:
        name = _esc(d["name"]) + (f"<br/><font size=7 color='#666666'>{_esc(d['note'])}</font>" if d["note"] else "")
        ded_rows.append([Paragraph(name, st["base"]), Paragraph(_esc(d["amount"]), st["right"])])
    if len(ded_rows) == 1:
        ded_rows.append([Paragraph("—", st["muted"]), ""])
    ded = Table(ded_rows, colWidths=[half - 24 * mm, 24 * mm])
    ded.setStyle(GRID)
    pair = Table([[acc, ded]], colWidths=[half + 2 * mm, half + 2 * mm])
    pair.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm)]))
    return [head, Spacer(1, 1.5 * mm), pair, Spacer(1, 3 * mm)]


def _settle_block(settle: dict, st: dict, width: float) -> list:
    """Decontarea lunii: impozitele reținute la plată, netul, ce s-a achitat și restul."""
    head = "Decontarea lunii" + ("" if settle["final"] else " (impozitele pe tot venitul lunii, cât se rețin la plată)")
    exemption = f" (scutirea {settle['exemption']})" if settle["exemption"] else ""
    if settle.get("it_park_only"):  # IT Park: salariul impozitat final — fără rândurile goale de impozit și CNAM
        taxes = [[Paragraph(f"<b>{_esc(settle['final_note'])}</b>: impozitul pe venit și prima CNAM nu se rețin", st["base"]), ""]]
    else:
        note = " (salariul din CIM — impozitat final, IT Park)" if settle.get("it_park") else ""
        taxes = [[Paragraph("Prima de asigurare medicală (CNAM)", st["base"]), Paragraph(settle["cnam"], st["right"])],
                 [Paragraph("Impozitul pe venit" + _esc(exemption + note), st["base"]), Paragraph(settle["income_tax"], st["right"])]]
    rows = [[Paragraph(head, st["bold"]), Paragraph("Suma", st["right_bold"])],
            [Paragraph("Total calculat", st["base"]), Paragraph(settle["gross"] or "0,00", st["right"])],
            *taxes,
            [Paragraph("Alte rețineri", st["base"]), Paragraph(settle["deductions"], st["right"])],
            [Paragraph("Salariul lunii, net", st["bold"]), Paragraph(settle["net"] or "0,00", st["right_bold"])],
            [Paragraph("Achitat: avans", st["base"]), Paragraph(settle["paid_advance"], st["right"])],
            [Paragraph("Achitat: salariu", st["base"]), Paragraph(settle["paid_salary"], st["right"])],
            [Paragraph("Rest de plată", st["bold"]), Paragraph(settle["rest"] or "0,00", st["right_bold"])]]
    table = Table(rows, colWidths=[width - 30 * mm, 30 * mm])
    table.setStyle(GRID)
    return [table, Spacer(1, 3 * mm)]


def _employee_story(year: int, month: int, slip: dict, company: Company, st: dict, width: float) -> list:
    story = [Paragraph(_esc(company.name_ro), st["bold"]),
             Paragraph(f"Fișa de calcul (fluturașul de salariu) · {MONTHS[month]} {year}", st["title"]),
             Paragraph(f"<b>{_esc(slip['name'])}</b> · nr. de tabel {_esc(slip['tab_number'])}", st["base"]),
             Spacer(1, 3 * mm)]
    for job in slip["jobs"]:
        story.append(KeepTogether(_job_block(job, st, width)))
    if slip["settle"]:
        story.append(KeepTogether(_settle_block(slip["settle"], st, width)))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(f"Întocmit la {timezone.localdate():%d.%m.%Y}. Documentul conține date cu caracter personal.", st["muted"]))
    return story


def build(payment: Payment, employee_ids=None) -> bytes:
    """PDF-ul fluturașilor îndreptării pe salariu: unul pe angajat (toate raporturile lui de muncă din calculele aprobate ale
    lunii), fiecare pe pagina lui; cu `employee_ids` — doar ai lor."""
    _fonts()
    st = _styles()
    company = Company.get()
    year, month = payment.year, payment.month
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
                            title=f"Fluturași {month:02d}.{year}", author=company.name_ro)
    story = []
    for n, slip in enumerate(slips_of(year, month, payment_slip_lines(payment, employee_ids))):
        if n:
            story.append(PageBreak())
        story += _employee_story(year, month, slip, company, st, doc.width)
    if not story:
        story = [Paragraph("Nu sunt angajați cu calcul aprobat în îndreptare.", st["base"])]
    doc.build(story)
    return buf.getvalue()
