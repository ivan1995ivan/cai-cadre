"""Antetul întreprinderii pe toate formele de tipar (fără Stema de Stat / fondator), datele firmei din Constante și din
asistentul de instalare."""
import base64
import importlib

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.models import BankAccount, Company

FORBIDDEN = ("REPUBLICA MOLDOVA", "РЕСПУБЛИКА МОЛДОВА", "REPUBLIC OF MOLDOVA", "Stema", "stema", "fondator", "Fondator",
             "MINISTERUL", "gov-header", "data:image/svg+xml")
# PNG de 1×1 pixel
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")


def render_form(doc_type, lang="ro", texts=None, style=None, extra=None):
    """Forma livrată, randată cu datele întreprinderii și un document gol (fără date de cadre): antetul și semnăturile."""
    from django.test import RequestFactory

    from apps.printing import texts as print_texts
    from apps.printing.models import PrintTemplate
    from apps.printing.renderer import company_context, render

    tpl = PrintTemplate.objects.get(doc_type=doc_type, code="standard")
    context = {"company": company_context(RequestFactory().get("/"), lang), "lang": lang,
               "options": dict(tpl.default_options or {}), **(extra or {})}
    context = print_texts.apply(context, doc_type, texts if texts is not None else tpl.texts, style or tpl.style, lang)
    return render(tpl.body, tpl.css, context, orientation=tpl.orientation, lang=lang, title=tpl.name)


@pytest.fixture
def firm(db, seeded, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    c = Company.get()
    c.name_ro, c.name_ru, c.legal_form = "„Exemplu Prim”", "«Пример Прим»", "SRL"
    c.idno, c.caem, c.legal_address = "1012600012345", "6201", "mun. Chișinău, str. Exemplu 1"
    c.phone, c.email, c.website = "022 000 001", "office@exemplu.md", "exemplu.md"
    c.director, c.director_position_ro, c.director_position_ru = "Ion Popescu", "Administrator", "Администратор"
    c.chief_accountant, c.hr_head = "Ana Rusu", "Maria Lungu"
    c.logo.save("logo.png", SimpleUploadedFile("logo.png", PNG, content_type="image/png"), save=False)
    c.save()
    BankAccount.objects.create(company=c, iban="MD24AG000225100013104168", bank_name="Banca Exemplu SA", bic="EXMDMD2X",
                               is_default=True)
    return c


def test_company_display_name_and_positions(db):
    c = Company(name_ro="„Exemplu”", legal_form="SRL")
    assert c.display_name() == "„Exemplu” SRL"
    c.name_ro = "Exemplu S.R.L."
    assert c.display_name() == "Exemplu S.R.L."  # forma juridică e deja în denumire
    c.legal_form = ""
    assert c.display_name() == "Exemplu S.R.L."
    c.name_ru, c.name_en = "Пример", ""
    assert c.display_name("ru") == "Пример" and c.display_name("en") == "Exemplu S.R.L."
    # funcțiile: goale — cele obișnuite; scrise doar în română — aceleași și pe forma rusă
    assert (c.position("director"), c.position("director", "ru")) == ("Director", "Директор")
    assert c.position("chief_accountant", "ru") == "Главный бухгалтер" and c.position("hr_head") == "Șef resurse umane"
    c.director_position_ro = " Administrator "
    assert c.position("director") == c.position("director", "ru") == c.position("director", "en") == "Administrator"
    c.director_position_ru = "Администратор"
    assert c.position("director", "ru") == "Администратор"


def test_every_print_form_renders_with_company_header(admin_client, firm):
    from apps.printing.models import PrintTemplate
    from apps.printing.seed import SYSTEM_TEMPLATES

    assert len(SYSTEM_TEMPLATES) == 24  # cu „Modificarea acumulărilor planificate” (S3), formele IT Park (S4), raportul de producție (S5a)
    for doc_type, code, *_ in SYSTEM_TEMPLATES:
        tpl = PrintTemplate.objects.get(doc_type=doc_type, code=code)
        assert "gov_header" not in tpl.body and "company_header" in tpl.body or doc_type == "payslip"
        for lang in ("ro", "ru", "en"):
            html = render_form(doc_type, lang)
            for word in FORBIDDEN:
                assert word not in html, (doc_type, lang, word)
            name = "«Пример Прим» SRL" if lang == "ru" else "„Exemplu Prim” SRL"
            if doc_type != "payslip":  # fluturașul are antetul lui scurt, pe fiecare fișă (fără fișe — fără antet)
                assert name in html, (doc_type, lang)
                assert 'class="company-header with-logo"' in html and "data:image/png;base64," in html, doc_type
                assert "IDNO 1012600012345" in html and "6201" in html and "mun. Chișinău, str. Exemplu 1" in html
                assert "IBAN MD24AG000225100013104168" in html and "office@exemplu.md" in html, doc_type
            # previzualizarea din editor (cu datele reale ale modulului, unde există) — tot fără antetul de stat
            r = admin_client.post("/api/print/preview/", {"doc_type": doc_type, "body": tpl.body, "css": tpl.css,
                                                         "orientation": tpl.orientation, "lang": lang}, format="json")
            if r.status_code == 200:
                assert not [w for w in FORBIDDEN if w in r.content.decode()], doc_type
            else:
                assert r.status_code == 400, (doc_type, r.status_code)  # „nu există încă date” — nu eroare de șablon
                assert "șablon" not in str(r.data), (doc_type, r.data)


def test_header_shows_only_filled_requisites_and_respects_no_logo(db, seeded):
    c = Company.get()
    c.name_ro, c.legal_form = "Firma Goală", ""
    c.save()
    html = render_form("employee_list")
    assert '<div class="company-name">Firma Goală</div>' in html and 'class="company-header"' in html
    assert "IDNO" not in html and "IBAN" not in html and 'class="requisites"' not in html


def test_logo_can_be_turned_off_in_form_style(firm):
    html = render_form("certificate_work", style={"show_logo": False})
    assert "data:image/png" not in html and 'class="company-header"' in html and "„Exemplu Prim” SRL" in html


def test_payslip_shows_company_name(firm):
    html = render_form("payslip", extra={"slips": [{"name": "Popescu Ion", "jobs": []}], "doc": {"month": "martie"}})
    assert "<b>„Exemplu Prim” SRL</b>" in html


def test_signatures_take_positions_and_names_from_constants(firm):
    html = render_form("certificate_work")
    assert "<div>Administrator<div" in html and "Ion Popescu" in html
    assert "<div>Șef resurse umane<div" in html and "Maria Lungu" in html
    assert "<div>Администратор<div" in render_form("certificate_work", "ru")
    assert "<div>Начальник отдела кадров<div" in render_form("certificate_work", "ru")
    payroll = render_form("payroll_sheet")
    assert "<div>Contabil-șef<div" in payroll and "Ana Rusu" in payroll and "{funcția" not in payroll
    staff = render_form("staff_list")
    assert "<div>Administrator<div" in staff and "<div>Contabil-șef<div" in staff
    leave = render_form("leave_schedule")
    assert "Administrator ______________ Ion Popescu" in leave and "{conducătorul}" not in leave
    # textul scris în formă are prioritate; în el merg și datele din Constante
    custom = render_form("employee_list", texts={"ro": {"hr_label": "Inspector personal, {întreprinderea}"}})
    assert "Inspector personal, „Exemplu Prim” SRL" in custom


def test_template_editor_lists_company_placeholders(admin_client, seeded):
    rows = admin_client.get("/api/print-templates/", {"doc_type": "staff_list"}).data
    assert {"număr", "întreprinderea", "funcția_conducătorului", "conducătorul"} <= set(rows[0]["placeholders"])
    fields = {f["key"]: f for f in rows[0]["text_fields"]}
    assert "Ministerul" not in str(fields)


def test_saved_templates_with_state_header_are_migrated(db, seeded):
    from django.apps import apps

    from apps.printing.models import PrintTemplate

    migration = importlib.import_module("apps.printing.migrations.0005_company_header")
    tpl = PrintTemplate.objects.create(doc_type="order", code="vechi", name="Ordin vechi",
                                       body="{% gov_header %}<p>Text propriu</p>", original_body="{% gov_header %}")
    migration.forwards(apps, None)
    tpl.refresh_from_db()
    assert tpl.body == "{% company_header %}<p>Text propriu</p>" and tpl.original_body == "{% company_header %}"
    assert not PrintTemplate.objects.filter(body__contains="gov_header").exists()


def test_caem_moves_from_tax_settings_to_constants(db):
    from django.apps import apps

    from apps.core.models import SystemSetting

    migration = importlib.import_module("apps.core.migrations.0007_company_private_enterprise")
    Company.get()
    SystemSetting.write("tax_report_settings", {"cnas_code": "1234567", "caem": "86.10"})
    migration.caem_to_company(apps, None)
    assert Company.objects.get(pk=1).caem == "8610"
    assert SystemSetting.read("tax_report_settings") == {"cnas_code": "1234567"}


def test_constants_api_has_firm_fields_without_state_or_crm_leftovers(admin_client, seeded):
    data = admin_client.get("/api/company/").data
    for gone in ("founder_ro", "founder_ru", "show_stema", "vat_code", "default_vat_rate", "offer_validity_days",
                 "margin_visible_to_all", "min_margin_pct", "cost_method", "discount_mode", "price_rounding",
                 "base_currency"):
        assert gone not in data
    for field in ("caem", "director_position_ro", "director_position_ru", "chief_accountant_position_ro",
                  "hr_head_position_ro", "logo", "bank_accounts", "legal_form", "idno"):
        assert field in data
    r = admin_client.patch("/api/company/", {"caem": "62.01", "director_position_ro": "Administrator"}, format="json")
    assert r.status_code == 200 and r.data["caem"] == "6201" and r.data["director_position_ro"] == "Administrator"
    assert admin_client.patch("/api/company/", {"caem": "62A"}, format="json").status_code == 400
    assert admin_client.patch("/api/company/", {"caem": ""}, format="json").data["caem"] == ""


def test_setup_wizard_company_data(db, seeded):
    from apps.setup.management.commands.crm_install import Command
    from apps.setup.views import CompanySetupSerializer

    bad = CompanySetupSerializer(data={"name_ro": "", "idno": "123", "caem": "x", "bank": {"iban": "nu"}})
    assert not bad.is_valid() and {"name_ro", "idno", "caem", "bank"} <= set(bad.errors)
    ok = CompanySetupSerializer(data={"name_ro": "„Exemplu”", "legal_form": "SRL", "idno": "1012600012345",
                                      "caem": "62.01", "legal_address": "mun. Chișinău", "phone": "022 000 001",
                                      "director": "Ion Popescu", "director_position_ro": "Administrator",
                                      "iban": "ignorat", "bank": {"iban": "md24 ag00 0225 1000 1310 4168",
                                                                  "bank_name": "Banca Exemplu SA"}})
    assert ok.is_valid(), ok.errors
    assert ok.validated_data["caem"] == "6201" and ok.validated_data["bank"]["iban"] == "MD24AG000225100013104168"
    Command()._configure({"company": ok.validated_data})
    c = Company.objects.get(pk=1)
    assert (c.name_ro, c.legal_form, c.idno, c.caem, c.legal_address) == ("„Exemplu”", "SRL", "1012600012345", "6201",
                                                                          "mun. Chișinău")
    assert c.director_position_ro == "Administrator" and c.display_name() == "„Exemplu” SRL"
    assert c.bank_accounts.get().iban == "MD24AG000225100013104168"
