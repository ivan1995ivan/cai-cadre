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


@register.simple_tag(takes_context=True)
def gov_header(context):
    """Antetul formelor oficiale CAI CADRE: Stema de Stat, REPUBLICA MOLDOVA, fondatorul, instituția și rechizitele."""
    from django.utils.html import escape
    from django.utils.safestring import mark_safe

    company = context.get("company") or {}
    lang = context.get("lang") or "ro"
    country = {"ru": "РЕСПУБЛИКА МОЛДОВА", "en": "REPUBLIC OF MOLDOVA"}.get(lang, "REPUBLICA MOLDOVA")
    parts = ['<div class="gov-header">']
    if company.get("stema"):
        parts.append(f'<img class="stema" src="{escape(company["stema"])}" alt="">')
    parts.append(f'<div class="country">{country}</div>')
    if company.get("founder"):
        parts.append(f'<div class="founder">{escape(company["founder"])}</div>')
    parts.append(f'<div class="institution">{escape(company.get("name", ""))}</div>')
    parts.append(f'<div class="requisites">{escape(company.get("requisites", ""))}</div></div>')
    return mark_safe("".join(parts))
