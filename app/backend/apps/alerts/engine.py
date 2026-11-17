"""Termenele și alertele (PLAN.md §5.8): se calculează din date, la cerere (lista „Termene și alerte”, panoul de start)
și noaptea (notificările în sistem și pe e-mail, o singură dată pentru fiecare alertă și utilizator).

Fiecare alertă are: tipul, nivelul, data-termen, angajatul și subdiviziunile lui, textul, legătura și **cui i se adresează**:
„hr” (cadrele: drept de editare a angajaților), „accounting” (contabilitatea: drept de salarizare), „head” (utilizatorii
subdiviziunii — șeful de secție, asistentul superior).
"""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

from django.db.models import Q
from django.utils import timezone

from apps.core.models import SystemSetting

SETTINGS_KEY = "alert_settings"
# tipul: (activ, zile înainte, cui) — zilele se schimbă din Setări
KINDS = {
    "probation_end": (True, 10, ("hr", "head")),
    "contract_end": (True, 30, ("hr", "head")),
    "document_expiry": (True, 30, ("hr",)),
    "qualification_expiry": (True, 180, ("hr", "head")),
    "childcare_end": (True, 30, ("hr", "accounting")),
    "maternity_end": (True, 14, ("hr", "accounting")),
    "leave_unused": (True, 0, ("hr", "head")),
    "sanction_expiry": (True, 7, ("hr",)),
    "retirement": (True, 180, ("hr",)),
    "birthday": (True, 7, ("hr", "head")),
    "seniority_step": (True, 30, ("hr", "accounting")),
    "order_unacknowledged": (True, 3, ("hr",)),
    "payroll_orders": (True, 7, ("accounting",)),
    "leave_requests": (True, 0, ("head", "hr")),
    "next_month_leave": (True, 30, ("head",)),
    "roster_missing": (True, 20, ("head", "hr")),
    "irm19_due": (True, 5, ("accounting", "hr")),
}
DEFAULTS = {"retirement_men": 63, "retirement_women": 63, "email_digest": True,
            **{k: {"enabled": v[0], "days": v[1]} for k, v in KINDS.items()}}
EXTRA: dict = {}  # tipurile adăugate de alte module (formarea, sănătatea): tip → funcția (today, days, cfg)


def register(kind: str, enabled: bool, days: int, audiences: tuple, fn):
    """Un modul își adaugă tipul de alertă: apare în listă, în setări și în notificările de noapte."""
    KINDS[kind] = (enabled, days, audiences)
    DEFAULTS[kind] = {"enabled": enabled, "days": days}
    EXTRA[kind] = fn


def get_settings() -> dict:
    saved = SystemSetting.read(SETTINGS_KEY, {}) or {}
    out = {**DEFAULTS, **saved}
    for k in KINDS:
        out[k] = {**DEFAULTS[k], **(saved.get(k) or {})}
    return out


def save_settings(data: dict) -> dict:
    cfg = get_settings()
    for k in KINDS:
        if isinstance(data.get(k), dict):
            cfg[k] = {"enabled": bool(data[k].get("enabled", cfg[k]["enabled"])),
                      "days": max(0, min(int(data[k].get("days", cfg[k]["days"]) or 0), 730))}
    for k in ("retirement_men", "retirement_women"):
        if k in data:
            cfg[k] = max(50, min(int(data[k] or 63), 75))
    if "email_digest" in data:
        cfg["email_digest"] = bool(data["email_digest"])
    SystemSetting.write(SETTINGS_KEY, cfg)
    return cfg


@dataclass
class Alert:
    kind: str
    key: str
    title: str
    text: str
    due: date
    level: str = "info"
    employee: int | None = None
    employee_name: str = ""
    subdivisions: set = field(default_factory=set)
    link: str = ""

    def as_dict(self, today: date) -> dict:
        return {"kind": self.kind, "key": self.key, "title": self.title, "text": self.text, "due": self.due,
                "days": (self.due - today).days, "level": self.level, "employee": self.employee,
                "employee_name": self.employee_name, "link": self.link}


def _subs(employee) -> set:
    return {j.subdivision_id for j in employee.employments.all() if j.status != "ended"}


def _d(day) -> str:
    return day.strftime("%d.%m.%Y") if day else ""


def _years_after(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year + years)
    except ValueError:
        return day.replace(year=day.year + years, day=28)


def collect(today: date | None = None, kinds=None) -> list:
    """Toate alertele active la data dată (fiecare tip cu orizontul lui din setări)."""
    today = today or timezone.localdate()
    cfg = get_settings()
    wanted = [k for k in KINDS if cfg[k]["enabled"] and (kinds is None or k in kinds)]
    out = []
    for kind in wanted:
        out += (EXTRA.get(kind) or globals()[f"_{kind}"])(today, cfg[kind]["days"], cfg)
    return sorted(out, key=lambda a: (a.due, a.kind, a.employee_name))


# --- raporturile de muncă ----------------------------------------------------------------------------------------
def _jobs():
    from apps.staff.models import Employment

    return Employment.objects.exclude(status="ended").select_related("employee", "occupation", "subdivision")


def _probation_end(today, days, cfg):
    out = []
    for j in _jobs().filter(probation_until__gte=today, probation_until__lte=today + timedelta(days=days)):
        out.append(Alert("probation_end", f"probation:{j.pk}:{j.probation_until}", "Se încheie perioada de probă",
                         f"{j.employee.full_name()} ({j.occupation.name_ro}) — perioada de probă până la {_d(j.probation_until)}",
                         j.probation_until, "warning", j.employee_id, j.employee.full_name(), {j.subdivision_id},
                         f"/employees/{j.employee_id}?tab=jobs"))
    return out


def _contract_end(today, days, cfg):
    out = []
    for j in _jobs().filter(date_to__gte=today, date_to__lte=today + timedelta(days=days)):
        out.append(Alert("contract_end", f"contract:{j.pk}:{j.date_to}", "Expiră contractul pe durată determinată",
                         f"{j.employee.full_name()} ({j.occupation.name_ro}, {j.get_kind_display().lower()}) — CIM până la "
                         f"{_d(j.date_to)}: prelungire sau încetare", j.date_to, "warning", j.employee_id,
                         j.employee.full_name(), {j.subdivision_id}, f"/employees/{j.employee_id}?tab=jobs"))
    return out


def _document_expiry(today, days, cfg):
    from apps.staff.models import EmployeeDocument

    out = []
    qs = (EmployeeDocument.objects.filter(expiry_date__lte=today + timedelta(days=days), expiry_date__gte=today - timedelta(days=30),
                                          employee__status__in=("active", "suspended"))
          .select_related("employee", "doc_type").prefetch_related("employee__employments"))
    for doc in qs:
        name = doc.doc_type.name_ro if doc.doc_type_id else (doc.title or "Actul")
        expired = doc.expiry_date < today
        out.append(Alert("document_expiry", f"doc:{doc.pk}:{doc.expiry_date}", "A expirat actul" if expired else "Expiră actul",
                         f"{doc.employee.full_name()} — {name} {doc.series} {doc.number}".strip() + f", valabil până la {_d(doc.expiry_date)}",
                         doc.expiry_date, "warning" if expired else "info", doc.employee_id, doc.employee.full_name(),
                         _subs(doc.employee), f"/employees/{doc.employee_id}?tab=documents"))
    return out


def _qualification_expiry(today, days, cfg):
    from apps.staff.models import Qualification

    out, seen = [], set()
    qs = (Qualification.objects.filter(valid_until__lte=today + timedelta(days=days), valid_until__gte=today - timedelta(days=30),
                                       employee__status__in=("active", "suspended"))
          .select_related("employee", "category", "specialty").prefetch_related("employee__employments").order_by("-valid_until"))
    for q in qs:
        if (q.employee_id, q.specialty_id) in seen:
            continue
        seen.add((q.employee_id, q.specialty_id))
        newer = Qualification.objects.filter(employee_id=q.employee_id, specialty_id=q.specialty_id, awarded_on__gt=q.awarded_on or date.min)
        if newer.exists():
            continue  # categoria a fost deja confirmată
        cat = q.category.name_ro.lower() if q.category_id else "categoria"
        spec = f" ({q.specialty.name_ro})" if q.specialty_id else ""
        out.append(Alert("qualification_expiry", f"qual:{q.pk}:{q.valid_until}", "Atestarea: expiră categoria de calificare",
                         f"{q.employee.full_name()} — {cat}{spec} valabilă până la {_d(q.valid_until)}", q.valid_until,
                         "warning" if q.valid_until < today + timedelta(days=60) else "info", q.employee_id,
                         q.employee.full_name(), _subs(q.employee), f"/employees/{q.employee_id}?tab=education"))
    return out


# --- concedii ------------------------------------------------------------------------------------------------------
def _absence_end(today, days, kinds, kind, title):
    from apps.leave.models import Absence

    out = []
    qs = (Absence.objects.filter(kind__in=kinds, date_to__gte=today, date_to__lte=today + timedelta(days=days))
          .select_related("employee").prefetch_related("employee__employments"))
    for a in qs:
        out.append(Alert(kind, f"{kind}:{a.pk}:{a.date_to}", title,
                         f"{a.employee.full_name()} — {a.get_kind_display().lower()} până la {_d(a.date_to)}; revine la "
                         f"{_d(a.date_to + timedelta(days=1))}", a.date_to, "info", a.employee_id, a.employee.full_name(),
                         _subs(a.employee), f"/employees/{a.employee_id}?tab=leave"))
    return out


def _childcare_end(today, days, cfg):
    return _absence_end(today, days, ("childcare", "childcare_unpaid"), "childcare_end",
                        "Se încheie concediul de îngrijire a copilului")


def _maternity_end(today, days, cfg):
    return _absence_end(today, days, ("maternity",), "maternity_end", "Se încheie concediul de maternitate")


def _leave_unused(today, days, cfg):
    """Codul muncii, art. 118: concediul nu se poate neacorda doi ani la rând — anii de muncă încheiați de peste un an
    cu zile rămase."""
    from apps.leave import balance
    from apps.staff.models import Employee

    calc = balance.Calculator(today)
    out = []
    for emp in balance.prefetch(Employee.objects.filter(status="active").prefetch_related("employments")):
        data = calc.balance(emp)
        old = [y for y in data["years"] if y["closed"] and y["remaining"] > 0 and balance.add_year(y["to"]) < today]
        if not old:
            continue
        days_left = sum(y["remaining"] for y in old)
        first = old[0]
        out.append(Alert("leave_unused", f"unused:{emp.pk}:{first['from']}", "Concediu nefolosit mai mult de un an",
                         f"{emp.full_name()} — {days_left:g} zile din anii de muncă încheiați (cel mai vechi: "
                         f"{_d(first['from'])} – {_d(first['to'])}); art. 118 Codul muncii", balance.add_year(first["to"]),
                         "warning", emp.pk, emp.full_name(), _subs(emp), f"/employees/{emp.pk}?tab=leave"))
    return out


def _leave_requests(today, days, cfg):
    from apps.leave.models import LeaveRequest

    out = []
    for r in LeaveRequest.objects.filter(status="new", deletion_mark=False).select_related("employee").prefetch_related("employee__employments"):
        out.append(Alert("leave_requests", f"request:{r.pk}", "Cerere de concediu de aprobat",
                         f"{r.employee.full_name()} — {r.get_kind_display().lower()} {_d(r.date_from)} – {_d(r.date_to)} ({r.days} zile)",
                         r.date_from, "task", r.employee_id, r.employee.full_name(), _subs(r.employee), "/leave?tab=requests"))
    return out


def _next_month_leave(today, days, cfg):
    from apps.leave.models import Absence

    out = []
    qs = (Absence.objects.filter(kind__in=("annual", "extra"), date_from__gt=today, date_from__lte=today + timedelta(days=days))
          .select_related("employee").prefetch_related("employee__employments"))
    for a in qs:
        out.append(Alert("next_month_leave", f"nextleave:{a.pk}:{a.date_from}", "Pleacă în concediu",
                         f"{a.employee.full_name()} — {a.get_kind_display().lower()} {_d(a.date_from)} – {_d(a.date_to)}",
                         a.date_from, "info", a.employee_id, a.employee.full_name(), _subs(a.employee),
                         f"/employees/{a.employee_id}?tab=leave"))
    return out


# --- disciplină, vârstă, vechime ----------------------------------------------------------------------------------------
def _sanction_expiry(today, days, cfg):
    from apps.orders.models import Sanction

    out = []
    qs = (Sanction.objects.filter(lifted_on__isnull=True, valid_until__gte=today, valid_until__lte=today + timedelta(days=days))
          .select_related("employee", "kind").prefetch_related("employee__employments"))
    for s in qs:
        out.append(Alert("sanction_expiry", f"sanction:{s.pk}", "Se stinge sancțiunea disciplinară",
                         f"{s.employee.full_name()} — {s.kind.name_ro.lower()} din {_d(s.date)} se stinge la {_d(s.valid_until)}",
                         s.valid_until, "info", s.employee_id, s.employee.full_name(), _subs(s.employee),
                         f"/employees/{s.employee_id}?tab=orders"))
    return out


def _active_people():
    from apps.staff.models import Employee

    return Employee.objects.filter(status__in=("active", "suspended"), birth_date__isnull=False).prefetch_related("employments")


def _retirement(today, days, cfg):
    out = []
    for e in _active_people():
        age = cfg["retirement_women"] if e.sex == "F" else cfg["retirement_men"]
        day = _years_after(e.birth_date, int(age))
        if today <= day <= today + timedelta(days=days):
            out.append(Alert("retirement", f"retire:{e.pk}:{day}", "Atinge vârsta standard de pensionare",
                             f"{e.full_name()} — împlinește {age} de ani la {_d(day)}", day, "info", e.pk, e.full_name(),
                             _subs(e), f"/employees/{e.pk}"))
    return out


def _birthday(today, days, cfg):
    out = []
    for e in _active_people():
        day = _years_after(e.birth_date, today.year - e.birth_date.year)
        if day < today:
            day = _years_after(e.birth_date, today.year + 1 - e.birth_date.year)
        if day <= today + timedelta(days=days):
            age = day.year - e.birth_date.year
            jubilee = age % 10 == 0 or (age >= 50 and age % 5 == 0)
            out.append(Alert("birthday", f"birthday:{e.pk}:{day.year}", "Jubileu" if jubilee else "Zi de naștere",
                             f"{e.full_name()} — {age} de ani la {_d(day)}", day, "success" if jubilee else "info", e.pk,
                             e.full_name(), _subs(e), f"/employees/{e.pk}"))
    return out


def _seniority_step(today, days, cfg):
    """Vechimea în sistemul sănătății atinge o treaptă nouă a sporului de vechime (tipul de calcul cu trepte pe ani)."""
    from apps.payroll.models import PayType
    from apps.staff import services as staff
    from apps.staff.models import Employee

    steps = set()
    for t in PayType.objects.filter(formula="scale", is_active=True):
        steps |= {int(s["from"]) for s in t.scale or [] if "from" in s}
    if not steps:
        return []
    out = []
    horizon = today + timedelta(days=days)
    for e in Employee.objects.filter(status="active").prefetch_related("employments__occupation", "experience"):
        now = staff.seniority(e, today)["healthcare"]["years"]
        later = staff.seniority(e, horizon)["healthcare"]["years"]
        reached = sorted(s for s in steps if now < s <= later)
        if reached:
            out.append(Alert("seniority_step", f"senior:{e.pk}:{reached[-1]}", "Vechime: treaptă nouă a sporului",
                             f"{e.full_name()} — împlinește {reached[-1]} ani de vechime în sistemul sănătății până la "
                             f"{_d(horizon)}", horizon, "info", e.pk, e.full_name(), _subs(e), f"/employees/{e.pk}?tab=seniority"))
    return out


# --- ordine, grafice, raportări ------------------------------------------------------------------------------------------
def _order_unacknowledged(today, days, cfg):
    from apps.orders.models import OrderItem

    out = []
    qs = (OrderItem.objects.filter(order__status="signed", acknowledged_on__isnull=True, employee__isnull=False,
                                   order__signed_at__date__lte=today - timedelta(days=days),
                                   order__signed_at__date__gte=today - timedelta(days=90))
          .select_related("order", "employee").prefetch_related("employee__employments"))
    for it in qs:
        out.append(Alert("order_unacknowledged", f"ack:{it.pk}", "Ordin neadus la cunoștință",
                         f"{it.employee.full_name()} — ordinul nr. {it.order.reference()}", it.order.date, "task",
                         it.employee_id, it.employee.full_name(), _subs(it.employee), f"/orders/{it.order_id}"))
    return out


def _payroll_orders(today, days, cfg):
    from apps.orders.models import Order

    out = []
    qs = (Order.objects.filter(status="signed", order_type__payroll_effect=True, signed_at__date__gte=today - timedelta(days=days))
          .select_related("order_type").prefetch_related("items__employee__employments"))
    for o in qs:
        names = ", ".join(i.employee.short_name() for i in o.items.all() if i.employee_id)[:200]
        subs = {s for i in o.items.all() if i.employee_id for s in _subs(i.employee)}
        out.append(Alert("payroll_orders", f"payorder:{o.pk}", "Ordin cu efect salarial",
                         f"Nr. {o.reference()} — {o.order_type.name_ro}: {names}", o.date, "info", None, "", subs, f"/orders/{o.pk}"))
    return out


def _roster_missing(today, days, cfg):
    """De la ziua din setări a lunii: secțiile cu angajați care n-au graficul lunar pentru luna următoare."""
    if today.day < days:
        return []
    from apps.org.models import Subdivision
    from apps.staff.models import Employment
    from apps.worktime.models import Roster

    nxt = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
    have = set(Roster.objects.filter(year=nxt.year, month=nxt.month).values_list("subdivision_id", flat=True))
    staffed = set(Employment.objects.exclude(status="ended").values_list("subdivision_id", flat=True))
    out = []
    for sub in Subdivision.objects.filter(pk__in=staffed - have, is_active=True):
        out.append(Alert("roster_missing", f"roster:{sub.pk}:{nxt:%Y-%m}", "Graficul lunar de completat",
                         f"{sub.name_ro} — graficul pe {nxt:%m.%Y} nu este făcut", nxt, "task", None, "", {sub.pk},
                         "/worktime/rosters"))
    return out


def _irm19_due(today, days, cfg):
    from apps.payroll import reports

    out = []
    for r in reports.irm19(today - timedelta(days=20), today)["rows"]:
        deadline = date.fromisoformat(r["deadline"])
        if deadline <= today + timedelta(days=days):
            what = r["event"] or r["type"]
            out.append(Alert("irm19_due", f"irm19:{r['order_id']}:{r['employee']}:{r['code'] or r['category']}",
                             "IRM19 de depus la CNAS", f"{r['name']} — {what.lower()}, ordinul nr. {r['order']}; termenul {_d(deadline)}",
                             deadline, "warning" if deadline <= today else "task", r["employee"], r["name"], set(),
                             "/tax-reports?tab=irm19"))
    return out


# --- destinatarii --------------------------------------------------------------------------------------------------------
def audiences_of(user) -> set:
    out = set()
    if user.has_crm_perm("employees.edit") or user.has_crm_perm("orders.create"):
        out.add("hr")
    if user.has_crm_perm("payroll.view"):
        out.add("accounting")
    if user.subdivisions.exists():
        out.add("head")
    return out


def for_user(user, alerts: list) -> list:
    """Alertele care privesc utilizatorul: după rolul lui (cadre / contabilitate) și, la șeful de secție, după secțiile lui."""
    from apps.staff import services as staff

    aud = audiences_of(user)
    if not aud:
        return []
    ids = staff.visible_subdivision_ids(user, "employees")
    own = set()
    for sub in user.subdivisions.all():
        own |= sub.descendant_ids()
    out = []
    for a in alerts:
        who = set(KINDS[a.kind][2])
        if who & (aud - {"head"}) and (ids is None or not a.subdivisions or a.subdivisions & ids):
            out.append(a)
        elif "head" in who and "head" in aud and a.subdivisions & own:
            out.append(a)
    return out


def recipients():
    from apps.users.models import User

    return User.objects.filter(is_active=True).prefetch_related("subdivisions")


def run(today=None) -> dict:
    """Sarcina de noapte: alertele noi → notificare în sistem + rezumatul pe e-mail (o dată pentru fiecare utilizator)."""
    from apps.core.models import Notification

    from . import mail
    from .models import AlertLog

    today = today or timezone.localdate()
    alerts = collect(today)
    cfg = get_settings()
    sent = emailed = 0
    for user in recipients():
        mine = for_user(user, alerts)
        if not mine:
            continue
        known = set(AlertLog.objects.filter(user=user, key__in=[a.key for a in mine]).values_list("key", flat=True))
        fresh = [a for a in mine if a.key not in known]
        if not fresh:
            continue
        for a in fresh:
            Notification.send(user, a.title, a.text, level="warning" if a.level == "warning" else ("task" if a.level == "task" else "info"),
                              kind=f"alert_{a.kind}", link=a.link)
        mailed = bool(cfg.get("email_digest")) and mail.send_digest(user, fresh, today)
        AlertLog.objects.bulk_create([AlertLog(user=user, key=a.key, emailed=mailed) for a in fresh], ignore_conflicts=True)
        sent += len(fresh)
        emailed += 1 if mailed else 0
    return {"alerts": len(alerts), "notified": sent, "emails": emailed}


def counts_by_kind(alerts: list) -> dict:
    out = defaultdict(int)
    for a in alerts:
        out[a.kind] += 1
    return dict(out)


def employment_filter_for(user):
    """Filtrul pe angajați pentru indicatorii panoului (șeful de secție — doar secțiile lui)."""
    from apps.staff import services as staff

    ids = staff.visible_subdivision_ids(user, "employees")
    return None if ids is None else Q(subdivision_id__in=ids)
