"""Catalogul de rapoarte (PLAN.md §5.9): fiecare raport primește filtrele și întoarce același format pentru ecran, Excel și tipar.

Formatul: {"title", "subtitle", "columns": [{"key", "title", "type"}], "rows": [{...} sau {"_section": "text"}],
"totals": {...} | None, "summary": [{"label", "value"}], "conclusion": "concluzia în cuvinte" (opțional)}. Tipurile coloanelor:
text, int, num, date, pct. Rândul cu `_link` (adresa din program) deschide documentul lui (dublu clic); `_subtotal` — îngroșat.
"""
from dataclasses import dataclass, field
from datetime import date

from django.utils import timezone
from rest_framework.exceptions import ValidationError

MONTHS = {
    "ro": ["", "ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie", "august", "septembrie", "octombrie",
           "noiembrie", "decembrie"],
    "ru": ["", "январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"],
    "en": ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
           "December"],
}

GROUPS = {
    "personnel": ("Personalul", "Персонал", "Personnel"),
    "time": ("Concedii și timp de muncă", "Отпуска и рабочее время", "Leave and working time"),
    "orders": ("Ordine", "Приказы", "Orders"),
    "external": ("Raportări externe", "Внешняя отчётность", "External reporting"),
}


def tr(text, lang: str) -> str:
    """Textele rapoartelor sunt tuple (ro, ru, en)."""
    if isinstance(text, str):
        return text
    i = {"ro": 0, "ru": 1, "en": 2}.get(lang, 0)
    return (text[i] if i < len(text) else "") or text[0]


def col(key, title, type_="text"):
    return {"key": key, "title": title, "type": type_}


@dataclass
class Report:
    key: str
    group: str
    title: tuple
    hint: tuple
    filters: list
    build: object  # (Params) -> dict
    perm: str = "reports.view"


@dataclass
class Link:
    """Rapoartele care au deja pagina lor în modul apar în catalog ca legătură."""

    key: str
    group: str
    title: tuple
    hint: tuple
    link: str
    perm: str


REPORTS: dict = {}
LINKS: list = []


def report(key, group, title, hint, filters, perm="reports.view"):
    def wrap(fn):
        REPORTS[key] = Report(key, group, title, hint, filters, fn, perm)
        return fn
    return wrap


@dataclass
class Params:
    user: object
    lang: str = "ro"
    today: date = field(default_factory=timezone.localdate)
    on_date: date | None = None
    date_from: date | None = None
    date_to: date | None = None
    year: int | None = None
    month: int | None = None
    subdivision: int | None = None
    category: str = ""
    kinds: str = "main"  # main = doar raporturile de bază; all = și cumulul
    absence_kind: str = ""
    employee: int | None = None  # rapoartele despre un singur angajat (fișa decontărilor)
    sub_ids: set | None = None  # subdiviziunile pe care le vede utilizatorul (None = toate)

    def t(self, text):
        return tr(text, self.lang)

    def month_name(self):
        return f"{MONTHS[self.lang if self.lang in MONTHS else 'ro'][self.month]} {self.year}"

    def period_text(self):
        return f"{self.date_from:%d.%m.%Y} – {self.date_to:%d.%m.%Y}"

    def allowed(self, sub_id) -> bool:
        return (self.sub_ids is None or sub_id in self.sub_ids)


def _date(value, name):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError({name: "Data nu este corectă (AAAA-LL-ZZ)."}) from exc


def parse(request) -> Params:
    """Filtrele comune din query string, cu valorile implicite: azi, luna curentă, anul curent."""
    from apps.org.models import Subdivision
    from apps.staff import services as staff

    q = request.query_params
    lang = q.get("lang") if q.get("lang") in ("ro", "ru", "en") else "ro"
    today = timezone.localdate()
    p = Params(user=request.user, lang=lang, today=today)
    p.on_date = _date(q["on_date"], "on_date") if q.get("on_date") else today
    p.date_from = _date(q["date_from"], "date_from") if q.get("date_from") else today.replace(day=1)
    p.date_to = _date(q["date_to"], "date_to") if q.get("date_to") else today
    if p.date_to < p.date_from:
        raise ValidationError({"date_to": "Sfârșitul perioadei este înaintea începutului."})
    try:
        p.year = int(q.get("year") or today.year)
        p.month = int(q.get("month") or today.month)
    except ValueError as exc:
        raise ValidationError({"detail": "Anul sau luna nu sunt corecte."}) from exc
    if not 1 <= p.month <= 12:
        raise ValidationError({"month": "Luna nu este corectă."})
    p.category = q.get("category", "")
    p.kinds = "all" if q.get("kinds") == "all" else "main"
    p.absence_kind = q.get("absence_kind", "")
    if q.get("employee"):
        from apps.staff.models import Employee

        emp = Employee.objects.filter(pk=q["employee"]).first() if str(q["employee"]).isdigit() else None
        if emp is None or not staff.can_see(emp, request.user):
            raise ValidationError({"employee": "Angajatul nu există sau nu este în subdiviziunile dvs."})
        p.employee = emp.pk
    visible = staff.visible_subdivision_ids(request.user, "employees")
    if q.get("subdivision"):
        sub = Subdivision.objects.filter(pk=q["subdivision"]).first()
        if sub is None:
            raise ValidationError({"subdivision": "Subdiviziunea nu există."})
        p.subdivision = sub.pk
        chosen = sub.descendant_ids()
        p.sub_ids = chosen if visible is None else chosen & visible
    else:
        p.sub_ids = visible
    return p


def subtitle_parts(p: Params, *parts) -> str:
    from apps.org.models import Subdivision

    out = [x for x in parts if x]
    if p.subdivision:
        sub = Subdivision.objects.filter(pk=p.subdivision).first()
        if sub:
            out.append(sub.local_name(p.lang))
    return " · ".join(out)


def catalog(user, lang: str) -> list:
    rows = []
    for r in REPORTS.values():
        if user.has_crm_perm(r.perm):
            rows.append({"key": r.key, "group": r.group, "group_title": tr(GROUPS[r.group], lang), "title": tr(r.title, lang),
                         "hint": tr(r.hint, lang), "filters": r.filters, "link": ""})
    for ln in LINKS:
        if user.has_crm_perm(ln.perm):
            rows.append({"key": ln.key, "group": ln.group, "group_title": tr(GROUPS[ln.group], lang), "title": tr(ln.title, lang),
                         "hint": tr(ln.hint, lang), "filters": [], "link": ln.link})
    order = list(GROUPS)
    rows.sort(key=lambda r: order.index(r["group"]))
    return rows


def run(key: str, p: Params) -> dict:
    rep = REPORTS.get(key)
    if rep is None:
        raise ValidationError({"detail": "Raportul nu există."})
    data = rep.build(p)
    data.setdefault("title", tr(rep.title, p.lang))
    data.setdefault("subtitle", "")
    data.setdefault("totals", None)
    data.setdefault("summary", [])
    data.setdefault("conclusion", "")
    data["key"] = key
    return data
