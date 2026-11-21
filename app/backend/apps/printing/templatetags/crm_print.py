from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def money(value, decimals=2):
    """1234.5 → „1 234,50” (formatul obișnuit în Moldova)."""
    if value is None or value == "":
        return ""
    try:
        number = Decimal(str(value))
        decimals = int(decimals)
    except (InvalidOperation, ValueError, TypeError):
        return value
    text = f"{number:,.{decimals}f}"
    return text.replace(",", " ").replace(".", ",")


@register.filter
def qty(value):
    """Cantitate fără zecimale inutile: 12.500 → 12,5."""
    if value is None or value == "":
        return ""
    try:
        number = Decimal(str(value)).normalize()
    except (InvalidOperation, ValueError):
        return value
    return f"{number:f}".replace(".", ",")


HEADER_WORDS = {"ro": ("IDNO", "Cod CAEM", "tel.", "e-mail", "BIC"), "ru": ("IDNO", "Код CAEM", "тел.", "e-mail", "BIC"),
                "en": ("IDNO", "CAEM code", "tel.", "e-mail", "BIC")}


@register.simple_tag(takes_context=True)
def company_header(context):
    """Antetul formelor: logo-ul (dacă e încărcat și nu e oprit în stilul formei), denumirea întreprinderii cu forma
    juridică și rechizitele — IDNO, CAEM, adresa juridică, telefonul, e-mailul, site-ul, contul bancar principal.
    Se arată doar ce e completat în Constante."""
    from django.utils.html import escape
    from django.utils.safestring import mark_safe

    company = context.get("company") or {}
    lang = context.get("lang") if context.get("lang") in HEADER_WORDS else "ro"
    idno_w, caem_w, phone_w, email_w, bic_w = HEADER_WORDS[lang]

    def line(*items):
        text = " · ".join(escape(x) for x in items if x)
        return f'<div class="requisites">{text}</div>' if text else ""

    bank = company.get("bank") or {}
    bank_text = ""
    if bank.get("iban"):
        bank_text = ", ".join(x for x in (f"IBAN {bank['iban']}", bank.get("bank"),
                                          f"{bic_w} {bank['bic']}" if bank.get("bic") else "") if x)
    logo = company.get("logo")
    parts = [f'<div class="company-header{" with-logo" if logo else ""}">']
    if logo:
        parts.append(f'<div class="company-logo"><img src="{escape(logo)}" alt=""></div>')
    parts.append('<div class="company-id">')
    parts.append(f'<div class="company-name">{escape(company.get("full_name") or company.get("name") or "")}</div>')
    parts.append(line(f"{idno_w} {company['idno']}" if company.get("idno") else "",
                      f"{caem_w} {company['caem']}" if company.get("caem") else "", company.get("address")))
    parts.append(line(f"{phone_w} {company['phone']}" if company.get("phone") else "",
                      f"{email_w} {company['email']}" if company.get("email") else "", company.get("website")))
    parts.append(line(bank_text))
    parts.append("</div></div>")
    return mark_safe("".join(parts))
