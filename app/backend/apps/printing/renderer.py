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

LABELS = {
    "ro": {
        "price_list": "Listă de prețuri", "date": "Data", "currency": "Valuta", "vat_included": "Prețurile includ TVA",
        "vat_excluded": "Prețurile nu includ TVA", "photo": "Foto", "code": "Cod", "name": "Denumire",
        "unit": "U.M.", "price": "Preț", "empty": "Nu sunt produse pentru criteriile alese.",
        "footer": "Prețurile pot fi modificate fără preaviz. Pentru calcul exact contactați managerul.",
        "uncategorized": "Fără categorie",
        "offer": "Ofertă comercială", "valid_until": "Valabilă până la", "manager": "Manager", "client": "Client",
        "contact": "Persoana de contact", "site": "Adresa (magazinul)", "qty": "Cantitate", "discount": "Reducere",
        "final_price": "Preț final", "amount": "Suma", "list_total": "Total după listă", "discount_total": "Reducere",
        "doc_discount": "Reducere la tot documentul", "without_vat": "Total fără TVA", "vat": "TVA", "total": "Total de plată",
        "vat_included_short": "cu TVA", "delivery_terms": "Livrarea", "payment_terms": "Plata",
        "offer_footer": "Oferta este valabilă până la data indicată. Prețurile și disponibilitatea se confirmă la comandă.",
        "invoice": "Factură", "due_date": "Termen de plată", "order": "Comanda", "buyer": "Cumpărător", "address": "Adresa",
        "delivery_address": "Adresa de livrare", "vat_code": "Cod TVA", "vat_rate": "Cota TVA", "issued_by": "A eliberat",
        "received_by": "A primit", "client_slip": "Aviz de livrare", "handed_over": "A predat", "no_claims": "fără pretenții",
        "warehouse_slip": "Bon de eliberare din depozit", "warehouse": "Depozit", "lots": "Lot / rolă — cantitate · celula",
        "picked_by": "A colectat", "checked_by": "A verificat",
        "delivery_note": "Aviz de însoțire a mărfii", "vehicle": "Mijlocul de transport", "invoiced_in": "Facturat în",
        "client_return": "Retur de la client", "base_invoices": "Pe baza facturilor", "return_reason": "Motivul",
        "reconciliation": "Act de verificare a decontărilor", "period": "Perioada", "reconciliation_between": "Între",
        "and": "și", "document": "Documentul", "debit": "Debit", "credit": "Credit", "opening_balance": "Sold la început",
        "turnover": "Rulaj pe perioadă", "closing_balance": "Sold la sfârșit", "director": "Director",
        "chief_accountant": "Contabil-șef",
        "payment_slip": "Bon de plată",
        "supplier_caps": "FURNIZOR", "buyer_caps": "CUMPĂRĂTOR", "prepared_by": "A întocmit", "tel": "Tel",
        "nr": "Nr.", "goods_name": "Denumire marfă", "sum": "Suma", "sum_total": "Sumă totală",
        "discount_sum": "Reducere", "sum_with_discount": "Sumă cu reducere", "total_label": "Total",
        "avg_discount": "Reducere medie acordată", "manager_sign": "Semnătură manager", "client_sign": "Semnătură client",
        "ls_company": "L.Ș. COMPANIE", "vat_of_which": "inclusiv TVA",
        "pf_client": "Client", "pf_client_phone": "Telefon client", "pf_manager": "Manager",
        "pf_manager_phone": "Telefon manager", "pf_route": "Ruta", "pf_order": "Comanda", "pf_goods": "MARFA",
        "pf_production": "Producere", "pf_roll": "ROLA", "pf_material": "MATERIAL", "pf_unrolled": "DESFĂȘURAT",
        "pf_length": "Lungimea foii", "pf_width": "Lățimea foii", "pf_area": "Suprafața", "pf_done": "Executat",
        "pf_comment": "COMENTARIU", "pf_execution": "EXECUTARE", "pf_release": "ELIBERARE",
        "pf_exec_requested": "Termen de executare solicitat", "pf_delivery_requested": "Termen de livrare solicitat",
        "pf_roll_series": "Seria rola", "pf_exec_date": "Data executării", "pf_packing": "Verificat ambalare",
        "pf_loaded": "Încărcat", "pf_received": "Primit marfa", "pf_delivery_date": "Data livrării",
        "payment_account": "Cont de plată", "supplier": "Furnizor", "payer": "Plătitor", "basis": "Temei",
        "from_date": "din", "price_no_vat": "Preț fără TVA", "amount_no_vat": "Suma fără TVA",
        "in_words": "Total de plată în litere", "payment_purpose": "În destinația plății indicați",
        "payment_by_account": "Plata conform contului nr.", "account_valid": "Contul de plată este valabil până la",
        "cutting_list": "Fișă de producere", "length_m": "Lungimea, m", "width_mm": "Lățimea, mm", "pieces": "Buc.",
        "note": "Notă", "cuts_total": "Total", "production_orders": "Comenzi de producție", "cut_by": "A debitat",
        "produced_check": "A verificat calitatea", "totals_by_unit": "Total pe comandă", "no_cuts": "fără debitare",
        "calc_title": "Calcul", "calc_params": "Datele inițiale", "calc_material": "Materialul", "calc_view3d": "Vedere 3D",
        "calc_plan": "Vedere de sus", "calc_slopes": "Pantele și foile", "calc_slope": "Panta", "calc_area": "Suprafața",
        "calc_sheets": "Foi", "calc_sheet_length": "Lungimea foii, mm", "calc_cutting_list": "Fișa de debitare",
        "calc_cutting": "Schema de tăiere din foi standard", "calc_waste": "Pierderi", "calc_material_area": "Material",
        "calc_materials": "Materiale", "calc_basis": "Calculat din", "calc_rest": "Rest", "calc_linear": "Metri liniari",
        "calc_weight": "Greutatea", "calc_roof_area": "Suprafața acoperișului", "calc_drawing": "Desenul acoperișului",
        "calc_stock_used": "Foi standard folosite", "calc_too_long": "Mai lungi decât foile standard",
        "calc_sheet_note": "Pe desen: numărul foii și lungimea ei în mm; partea punctată se taie la montaj. Cotele, în metri.",
    },
    "ru": {
        "price_list": "Прайс-лист", "date": "Дата", "currency": "Валюта", "vat_included": "Цены с НДС",
        "vat_excluded": "Цены без НДС", "photo": "Фото", "code": "Код", "name": "Наименование",
        "unit": "Ед.", "price": "Цена", "empty": "Нет товаров по выбранным условиям.",
        "footer": "Цены могут быть изменены без предварительного уведомления. Для точного расчёта обратитесь к менеджеру.",
        "uncategorized": "Без категории",
        "offer": "Коммерческое предложение", "valid_until": "Действительно до", "manager": "Менеджер", "client": "Клиент",
        "contact": "Контактное лицо", "site": "Адрес (магазин)", "qty": "Количество", "discount": "Скидка",
        "final_price": "Цена со скидкой", "amount": "Сумма", "list_total": "Сумма по прайсу", "discount_total": "Скидка",
        "doc_discount": "Скидка на весь документ", "without_vat": "Итого без НДС", "vat": "НДС", "total": "Итого к оплате",
        "vat_included_short": "с НДС", "delivery_terms": "Доставка", "payment_terms": "Оплата",
        "offer_footer": "Предложение действительно до указанной даты. Цены и наличие подтверждаются при заказе.",
        "invoice": "Счёт-фактура", "due_date": "Срок оплаты", "order": "Заказ", "buyer": "Покупатель", "address": "Адрес",
        "delivery_address": "Адрес доставки", "vat_code": "Код НДС", "vat_rate": "Ставка НДС", "issued_by": "Отпустил",
        "received_by": "Получил", "client_slip": "Накладная на отгрузку", "handed_over": "Сдал", "no_claims": "претензий не имею",
        "warehouse_slip": "Расходный ордер склада", "warehouse": "Склад", "lots": "Партия / рулон — количество · ячейка",
        "picked_by": "Собрал", "checked_by": "Проверил",
        "delivery_note": "Товарная накладная", "vehicle": "Транспорт", "invoiced_in": "Включено в счёт",
        "client_return": "Возврат от клиента", "base_invoices": "На основании счетов", "return_reason": "Причина",
        "reconciliation": "Акт сверки взаиморасчётов", "period": "Период", "reconciliation_between": "Между",
        "and": "и", "document": "Документ", "debit": "Дебет", "credit": "Кредит", "opening_balance": "Сальдо на начало",
        "turnover": "Обороты за период", "closing_balance": "Сальдо на конец", "director": "Директор",
        "chief_accountant": "Главный бухгалтер",
        "payment_slip": "Квитанция на оплату",
        "supplier_caps": "ПОСТАВЩИК", "buyer_caps": "ПОКУПАТЕЛЬ", "prepared_by": "Составил", "tel": "Тел",
        "nr": "№", "goods_name": "Наименование товара", "sum": "Сумма", "sum_total": "Общая сумма",
        "discount_sum": "Скидка", "sum_with_discount": "Сумма со скидкой", "total_label": "Итого",
        "avg_discount": "Средняя предоставленная скидка", "manager_sign": "Подпись менеджера", "client_sign": "Подпись клиента",
        "ls_company": "М.П. КОМПАНИИ", "vat_of_which": "в том числе НДС",
        "pf_client": "Клиент", "pf_client_phone": "Телефон клиента", "pf_manager": "Менеджер",
        "pf_manager_phone": "Телефон менеджера", "pf_route": "Маршрут", "pf_order": "Заказ", "pf_goods": "ТОВАР",
        "pf_production": "Производство", "pf_roll": "РУЛОН", "pf_material": "МАТЕРИАЛ", "pf_unrolled": "РАСКРОЙ",
        "pf_length": "Длина листа", "pf_width": "Ширина листа", "pf_area": "Площадь", "pf_done": "Выполнено",
        "pf_comment": "КОММЕНТАРИЙ", "pf_execution": "ВЫПОЛНЕНИЕ", "pf_release": "ВЫДАЧА",
        "pf_exec_requested": "Запрошенный срок выполнения", "pf_delivery_requested": "Запрошенный срок доставки",
        "pf_roll_series": "Серия рулона", "pf_exec_date": "Дата выполнения", "pf_packing": "Проверена упаковка",
        "pf_loaded": "Погружено", "pf_received": "Товар принял", "pf_delivery_date": "Дата доставки",
        "payment_account": "Счёт на оплату", "supplier": "Поставщик", "payer": "Плательщик", "basis": "Основание",
        "from_date": "от", "price_no_vat": "Цена без НДС", "amount_no_vat": "Сумма без НДС",
        "in_words": "Всего к оплате прописью", "payment_purpose": "В назначении платежа укажите",
        "payment_by_account": "Оплата по счёту №", "account_valid": "Счёт действителен до",
        "cutting_list": "Лист на производство", "length_m": "Длина, м", "width_mm": "Ширина, мм", "pieces": "Шт.",
        "note": "Примечание", "cuts_total": "Итого", "production_orders": "Производственные заказы", "cut_by": "Раскроил",
        "produced_check": "Проверил качество", "totals_by_unit": "Итого по заказу", "no_cuts": "без раскроя",
        "calc_title": "Расчёт", "calc_params": "Исходные данные", "calc_material": "Материал", "calc_view3d": "Вид 3D",
        "calc_plan": "Вид сверху", "calc_slopes": "Скаты и листы", "calc_slope": "Скат", "calc_area": "Площадь",
        "calc_sheets": "Листов", "calc_sheet_length": "Длина листа, мм", "calc_cutting_list": "Лист раскроя",
        "calc_cutting": "Схема раскроя из стандартных листов", "calc_waste": "Отходы", "calc_material_area": "Материал",
        "calc_materials": "Материалы", "calc_basis": "Рассчитано из", "calc_rest": "Остаток", "calc_linear": "Погонные метры",
        "calc_weight": "Вес", "calc_roof_area": "Площадь кровли", "calc_drawing": "Чертёж кровли",
        "calc_stock_used": "Использовано стандартных листов", "calc_too_long": "Длиннее стандартных листов",
        "calc_sheet_note": "На чертеже: номер листа и его длина в мм; пунктир обрезается при монтаже. Размеры в метрах.",
    },
}


class PrintError(Exception):
    pass


def default_body(doc_type: str) -> str:
    path = DEFAULTS_DIR / f"{doc_type}.html"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def base_css() -> str:
    return (DEFAULTS_DIR / "base.css").read_text(encoding="utf-8")


def company_context(request, lang: str) -> dict:
    company = Company.get()

    def url(field):
        return request.build_absolute_uri(field.url) if field else ""

    return {
        "name": (lang == "ru" and company.name_ru) or company.name_ro,
        "legal_form": company.legal_form, "idno": company.idno, "vat_code": company.vat_code,
        "address": company.legal_address, "postal_address": company.postal_address,
        "phone": company.phone, "email": company.email, "website": company.website,
        "director": company.director, "chief_accountant": company.chief_accountant,
        "logo": url(company.logo), "stamp": url(company.stamp), "signature": url(company.signature),
        "bank_accounts": [{"iban": b.iban, "bank": b.bank_name, "bic": b.bic, "currency": b.currency,
                           "default": b.is_default} for b in company.bank_accounts.all()],
        "accent": company.primary_color or {"blue": "#1E6FD9", "turquoise": "#07BCCB"}.get(company.default_theme, "#1FA463"),
        # CAI CADRE: antetul formelor oficiale (Stema de Stat, fondatorul, șeful resurselor umane)
        "stema": stema_uri() if company.show_stema else "",
        "founder": (lang == "ru" and company.founder_ru) or company.founder_ro,
        "hr_head": company.hr_head,
        "name_ro": company.name_ro,
        # rândul de rechizite sub denumire: doar ce e completat, despărțit prin „·”
        "requisites": " · ".join(x for x in (
            f"IDNO {company.idno}" if company.idno else "", company.legal_address,
            f"tel. {company.phone}" if company.phone else "", company.email) if x),
    }


def stema_uri() -> str:
    """Stema de Stat a Republicii Moldova (SVG), pusă direct în pagină: tiparul nu cere fișiere din afară."""
    import base64

    svg = (Path(__file__).resolve().parent / "assets" / "stema.svg").read_bytes()
    return "data:image/svg+xml;base64," + base64.b64encode(svg).decode()


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
