"""Tipărirea documentelor din șabloane editabile.

Șabloanele folosesc limbajul de șabloane Django, dar primesc DOAR date simple (dicționare, liste,
text, numere) — niciodată obiecte din baza de date —, ca un șablon modificat să nu poată ajunge la
date pe care nu ar trebui să le vadă. Pagina rezultată are o politică de securitate care interzice
scripturile; tipărirea o pornește interfața, din afara paginii.
"""
from pathlib import Path

from django.template import Context, Engine, TemplateSyntaxError
from django.utils import timezone
from django.utils.html import escape

from apps.core.models import Company

DEFAULTS_DIR = Path(__file__).resolve().parent / "defaults"

ENGINE = Engine(
    dirs=[],
    app_dirs=False,
    libraries={"crm_print": "apps.printing.templatetags.crm_print"},
    builtins=["apps.printing.templatetags.crm_print"],
    autoescape=True,
)

CSP = "default-src 'none'; img-src * data: blob:; style-src 'unsafe-inline'; font-src data:; script-src 'none'"


class PrintError(Exception):
    pass


def default_body(doc_type: str) -> str:
    path = DEFAULTS_DIR / f"{doc_type}.html"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def base_css() -> str:
    return (DEFAULTS_DIR / "base.css").read_text(encoding="utf-8")


def company_context(request, lang: str) -> dict:
    """Datele întreprinderii pentru forme (antetul, semnăturile), în limba formei. Imaginile (logo-ul, ștampila,
    semnătura) se pun direct în pagină: tiparul nu cere fișiere de pe server (adresa lor poate fi altă în spatele
    proxy-ului, iar pagina tipărită e deschisă dintr-un cadru fără sesiune)."""
    company = Company.get()
    accounts = list(company.bank_accounts.all())
    main_account = next((b for b in accounts if b.is_default), accounts[0] if accounts else None)
    lang = lang if lang in ("ro", "ru", "en") else "ro"
    return {
        "name": (lang == "ru" and company.name_ru) or (lang == "en" and company.name_en) or company.name_ro,
        "full_name": company.display_name(lang),
        "name_ro": company.name_ro,
        "legal_form": company.legal_form, "idno": company.idno, "caem": company.caem,
        "address": company.legal_address, "postal_address": company.postal_address,
        "phone": company.phone, "email": company.email, "website": company.website,
        "director": company.director, "director_position": company.position("director", lang),
        "chief_accountant": company.chief_accountant,
        "chief_accountant_position": company.position("chief_accountant", lang),
        "hr_head": company.hr_head, "hr_head_position": company.position("hr_head", lang),
        "logo": embedded(company.logo), "stamp": embedded(company.stamp), "signature": embedded(company.signature),
        "bank_accounts": [{"iban": b.iban, "bank": b.bank_name, "bic": b.bic, "currency": b.currency,
                           "default": b.is_default} for b in accounts],
        "bank": ({"iban": main_account.iban, "bank": main_account.bank_name, "bic": main_account.bic}
                 if main_account else None),
        "accent": company.primary_color or {"blue": "#1E6FD9", "turquoise": "#07BCCB"}.get(company.default_theme, "#1FA463"),
    }


IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml",
               ".webp": "image/webp"}


def embedded(field) -> str:
    """Imaginea încărcată în Constante ca `data:` URI; lipsă, alt tip sau fișier pierdut — gol (forma iese fără ea)."""
    import base64

    if not field:
        return ""
    mime = IMAGE_TYPES.get(Path(field.name).suffix.lower())
    if not mime:
        return ""
    try:
        with field.open("rb") as fh:
            raw = fh.read()
    except (OSError, ValueError):
        return ""
    finally:
        try:
            field.close()
        except (OSError, ValueError):
            pass
    return f"data:{mime};base64," + base64.b64encode(raw).decode()


def render(body: str, css: str, context: dict, *, orientation="portrait", title="", lang="ro") -> str:
    if (context.get("options") or {}).get("show_stamp") is False and context.get("company"):
        context = {**context, "company": {**context["company"], "stamp": "", "signature": ""}}  # tipărit fără ștampilă
    try:
        template = ENGINE.from_string(body)
        content = template.render(Context(context, autoescape=True))
    except TemplateSyntaxError as exc:
        raise PrintError(f"Eroare în șablon: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 – o greșeală în șablon nu trebuie să dea eroare 500
        raise PrintError(f"Șablonul nu a putut fi afișat: {exc}") from exc
    from .texts import style_css

    page = "@page { size: A4 landscape; }" if orientation == "landscape" else ""
    page += " " + style_css(context.get("style"))
    accent = escape(context.get("company", {}).get("accent", "#1FA463"))
    return (
        f'<!doctype html><html lang="{lang}" translate="no"><head><meta charset="utf-8"><meta name="google" content="notranslate"><title>{escape(title)}</title>'
        f"<style>:root{{--accent:{accent};}}\n{base_css()}\n{page}\n{css}</style></head>"
        f"<body>{content}</body></html>"
    )


def today_str():
    return timezone.localdate().strftime("%d.%m.%Y")
