"""Trimiterea fluturașilor pe e-mail: fiecărui angajat — o arhivă ZIP cu PDF-ul lui, parola = ultimele 5 cifre ale codului
fiscal (IDNP). Fără e-mail sau fără IDNP angajatul se sare (se vede motivul). Se trimite pe bucăți (interfața trimite
câte 20 de angajați pe rând și arată progresul), prin serverul SMTP din Administrare → Setări → Poșta (e-mail)."""
from django.core.mail import EmailMessage
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.alerts import mail

from . import payslip_pdf, zipcrypto
from .models import Payment, PayslipDispatch
from .printing import MONTHS

CHUNK = 25


def password_of(employee) -> str:
    digits = "".join(ch for ch in (employee.idnp or "") if ch.isdigit())
    return digits[-5:] if len(digits) >= 5 else ""


def summary(payment: Payment) -> dict:
    """Cine din îndreptare poate primi fluturașul: cu e-mail și IDNP, fără e-mail, fără IDNP; ultima trimitere a fiecăruia."""
    people = {}
    for ln in payment.lines.select_related("employee"):
        people.setdefault(ln.employee_id, ln.employee)
    last = {}
    for d in PayslipDispatch.objects.filter(payment=payment).order_by("sent_at", "id"):
        last[d.employee_id] = {"status": d.status, "message": d.message, "email": d.email, "sent_at": d.sent_at}
    rows = []
    for e in sorted(people.values(), key=lambda x: (x.last_name, x.first_name)):
        problem = "" if (e.email or "").strip() else "fără e-mail"
        if not problem and not password_of(e):
            problem = "fără IDNP (parola arhivei)"
        rows.append({"employee": e.pk, "name": e.full_name(), "email": e.email or "", "problem": problem, "last": last.get(e.pk)})
    conn, _cfg = mail.connection()
    return {"rows": rows, "ready": sum(1 for r in rows if not r["problem"]), "smtp": conn is not None}


def send(payment: Payment, employee_ids: list, user=None) -> list:
    """Trimite fluturașii angajaților dați din îndreptare (cel mult CHUNK o dată); întoarce rezultatul pe fiecare."""
    if payment.kind != "salary" or payment.status not in ("approved", "paid") or payment.deletion_mark:
        raise ValidationError({"detail": "Fluturașii se trimit din îndreptarea pe salariu aprobată sau achitată."})
    if len(employee_ids) > CHUNK:
        raise ValidationError({"detail": f"Cel mult {CHUNK} angajați o dată."})
    conn, cfg = mail.connection()
    if conn is None:
        raise ValidationError({"detail": "E-mailul nu e configurat: Administrare → Setări → Poșta (e-mail) pentru notificări și fluturași (serverul SMTP)."})
    month = f"{MONTHS[payment.month]} {payment.year}"
    lines = payment.lines.select_related("employee").filter(employee_id__in=employee_ids)
    people = {ln.employee_id: ln.employee for ln in lines}
    out = []
    conn.open()
    try:
        for emp_id in employee_ids:
            e = people.get(int(emp_id))
            if e is None:
                continue
            email, pwd = (e.email or "").strip(), password_of(e)
            status, message = "sent", ""
            if not email:
                status, message = "skipped", "fără e-mail"
            elif not pwd:
                status, message = "skipped", "fără IDNP (parola arhivei)"
            else:
                try:
                    pdf = payslip_pdf.build(payment, [e.pk])
                    name = f"fluturas-{payment.year}-{payment.month:02d}-{e.tab_number or e.pk}"
                    archive = zipcrypto.make_zip([(f"{name}.pdf", pdf)], pwd)
                    msg = EmailMessage(
                        subject=f"Fluturașul de salariu — {month}",
                        body=(f"Bună ziua, {e.first_name}!\n\nÎn atașament găsiți fluturașul de salariu pentru {month}.\n"
                              "Arhiva are parolă: ultimele 5 cifre ale codului dvs. personal (IDNP).\n\n"
                              "Mesaj trimis automat din programul de evidență a cadrelor."),
                        from_email=cfg["from_email"] or cfg["username"], to=[email], connection=conn)
                    msg.attach(f"{name}.zip", archive, "application/zip")
                    msg.send(fail_silently=False)
                except Exception as exc:  # o adresă greșită nu oprește restul
                    status, message = "error", str(exc)[:300]
            PayslipDispatch.objects.create(payment=payment, employee=e, email=email, status=status, message=message,
                                           sent_at=timezone.now(), sent_by=user)
            out.append({"employee": e.pk, "name": e.full_name(), "email": email, "status": status, "message": message})
    finally:
        conn.close()
    return out
