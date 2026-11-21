"""API-ul regimului IT Park: regimul fiscal cu istoric (Setări → Constantele salarizării), luna impozitului unic (venitul din
vânzări, angajații, IU17), ISAPTI17 și nota anuală pentru angajat — previzualizare, Excel și tipar."""
from decimal import Decimal

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.printing.renderer import company_context
from apps.printing.views import print_document
from apps.staff.models import Employee

from . import it_park, reports
from .models import FiscalRegime, ItParkMonth
from .payments import MONTHS
from .printing import _money
from .serializers import FiscalRegimeSerializer, ItParkMonthSerializer

SETTINGS_ACTIONS = {"create": "edit", "update": "edit", "partial_update": "edit", "destroy": "edit"}


def _d(value):
    return value.strftime("%d.%m.%Y") if value else ""


def _lang(request):
    return request.query_params.get("lang") if request.query_params.get("lang") in ("ro", "ru", "en") else "ro"


def _int(value, field, low, high):
    try:
        v = int(value)
    except (TypeError, ValueError):
        raise ValidationError({field: "Nu este un număr."}) from None
    if not low <= v <= high:
        raise ValidationError({field: f"Între {low} și {high}."})
    return v


def _num(value) -> float:
    return float(Decimal(value or 0))


class FiscalRegimeViewSet(viewsets.ModelViewSet):
    """Regimul fiscal al întreprinderii pe luni (general / IT Park), cu istoric."""

    perm_module = "payroll_settings"
    perm_actions = SETTINGS_ACTIONS
    serializer_class = FiscalRegimeSerializer
    pagination_class = None
    queryset = FiscalRegime.objects.all()


def _month_json(data: dict) -> dict:
    out = {**data}
    for k in ("sales_income", "per_employee", "tax_pct", "min_pct", "avg_salary", "by_sales", "minimum", "due"):
        out[k] = None if data.get(k) is None else _num(data[k])
    out["rows"] = [{**r, "base": None if r["base"] is None else _num(r["base"]), "amount": _num(r["amount"])} for r in data["rows"]]
    return out


class ItParkYearView(APIView):
    """Lunile anului în regim (și cele cu venitul scris): venitul din vânzări, angajații, impozitul datorat."""

    perm_module = ("tax_reports", "payroll")

    def get(self, request):
        year = _int(request.query_params.get("year") or timezone.localdate().year, "year", 2000, 2100)
        today = timezone.localdate()
        regimes = FiscalRegimeSerializer(FiscalRegime.objects.all(), many=True).data
        return Response({"year": year, "regime": it_park.regime_on(today), "regimes": regimes,
                         "months": [_month_json(m) for m in it_park.year_overview(year)]})


class ItParkMonthView(APIView):
    """Luna impozitului unic: GET — calculul (cu lista angajaților); PUT — venitul din vânzări, data depunerii IU17;
    ?export=xlsx — Excel; ?print=1 — tiparul calculului."""

    perm_module = ("tax_reports", "payroll")

    def get(self, request, year, month):
        year, month = _int(year, "year", 2000, 2100), _int(month, "month", 1, 12)
        p = request.query_params
        if p.get("export") == "xlsx":
            if not request.user.has_crm_perm("tax_reports.export"):
                raise PermissionDenied("Nu aveți drept de export.")
            return iu17_xlsx(it_park.month_tax(year, month))
        if p.get("print"):
            return print_month(request, year, month)
        return Response(_month_json(it_park.month_tax(year, month)))

    def put(self, request, year, month):
        if not (request.user.has_crm_perm("tax_reports.create") or request.user.has_crm_perm("payroll.edit")):
            raise PermissionDenied("Venitul din vânzări îl scrie cine întocmește raportările fiscale sau salariul (contabilul).")
        year, month = _int(year, "year", 2000, 2100), _int(month, "month", 1, 12)
        doc = ItParkMonth.objects.filter(year=year, month=month).first() or ItParkMonth(year=year, month=month)
        ser = ItParkMonthSerializer(doc, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save(updated_by=request.user, updated_at=timezone.now())
        return Response(_month_json(it_park.month_tax(year, month)))


# --- Excel -----------------------------------------------------------------------------------------------------------------
def iu17_xlsx(data: dict):
    head = ["Indicatorii", "Codul", "Baza impozabilă / numărul", "Cota", "Suma impozitului unic (lei)", "Temeiul"]
    rows = [[r["label"], r["code"], "" if r["base"] is None else _num(r["base"]), r["rate"], _num(r["amount"]), r["basis"]]
            for r in data["rows"]]
    people = [[n, p["tab_number"], p["name"], p["idnp"], "; ".join(p["jobs"]), p["worked_days"], "da" if p["counted"] else "nu",
               p["reason"]] for n, p in enumerate(data["people"], start=1)]
    return reports.xlsx(f"IU17-{data['year']}-{data['month']:02d}.xlsx", [
        ("IU17 (calculul)", head, rows),
        ("Angajații (rd. 020)", ["Nr.", "Nr. tabel", "Numele, prenumele", "IDNP", "Raporturile de muncă (CIM)", "Zile lucrate",
                                  "Se numără", "Motivul"], people)])


def isapti17_xlsx(data: dict):
    head = ["Nr.", "Codul fiscal al angajatului", "Numele și prenumele", "Venitul salarial îndreptat spre achitare în regim (lei)",
            "Numărul de luni în regim"]
    rows = [[r["no"], r["idnp"], r["name"], r["income"], r["months"]] for r in data["rows"]]
    rows.append(["", "", "Total", data["total"]["income"], ""])
    return reports.xlsx(f"ISAPTI17-{data['year']}.xlsx", [("ISAPTI17", head, rows)])


# --- tiparul ---------------------------------------------------------------------------------------------------------------
def month_context(request, year: int, month: int, lang="ro") -> dict:
    data = it_park.month_tax(year, month)
    rows = [{**r, "base": "" if r["base"] is None else (str(int(r["base"])) if r["code"] == "020" else _money(r["base"])),
             "amount": _money(r["amount"]) or "0,00"} for r in data["rows"]]
    people = [{**p, "no": n} for n, p in enumerate([x for x in data["people"]], start=1)]
    return {"company": company_context(request, lang), "lang": lang, "options": {},
            "doc": {"year": year, "month": MONTHS[month], "month_no": f"{month:02d}", "rows": rows, "people": people,
                    "employees": data["employees"], "due": _money(data["due"]) or "0,00", "deadline": _d(data["deadline"]),
                    "sales_entered": data["sales_entered"], "it_park": data["it_park"],
                    "rule": "7 % din venitul din vânzări" if data["rule"] == "sales" else "minimul pe angajați"},
            "today": _d(timezone.localdate()), "placeholders": {"luna": MONTHS[month], "an": year}}


def print_month(request, year: int, month: int):
    lang = _lang(request)
    return print_document(request, "it_park_tax", month_context(request, year, month, lang),
                          template_id=request.query_params.get("template"), title=f"Impozitul unic IT Park {month:02d}.{year}", lang=lang)


def annual_context(request, year: int, lang="ro") -> dict:
    data = it_park.isapti17(year)
    rows = [{**r, "income": _money(r["income"]) or "0,00"} for r in data["rows"]]
    return {"company": company_context(request, lang), "lang": lang, "options": {},
            "doc": {"year": year, "rows": rows, "total": _money(data["total"]["income"]) or "0,00", "persons": data["total"]["persons"]},
            "today": _d(timezone.localdate()), "placeholders": {"an": year}}


def notes_context(request, year: int, employee_ids=None, lang="ro") -> dict:
    rows = it_park.annual_rows(year, employee_ids=employee_ids)
    notes = [{**r, "income": _money(r["income"]) or "0,00", "months_text": ", ".join(MONTHS[m] for m in r["month_list"])} for r in rows]
    return {"company": company_context(request, lang), "lang": lang, "options": {}, "doc": {"year": year, "notes": notes},
            "today": _d(timezone.localdate()), "placeholders": {"an": year}}


def print_annual(request, year: int):
    lang = _lang(request)
    return print_document(request, "isapti17", annual_context(request, year, lang), template_id=request.query_params.get("template"),
                          title=f"ISAPTI17 {year}", lang=lang)


def print_notes(request, year: int, employee_ids=None):
    lang = _lang(request)
    return print_document(request, "it_park_note", notes_context(request, year, employee_ids, lang),
                          template_id=request.query_params.get("template"), title=f"Nota anuală IT Park {year}", lang=lang)


def annual_report(request, year: int):
    """ISAPTI17 (?export=xlsx, ?print=1) și notele anuale (?print=notes, &employee=… pentru unul singur)."""
    p = request.query_params
    if p.get("export") == "xml":
        raise ValidationError({"detail": "Pentru ISAPTI17 nu avem schema XML oficială: se depune după Excel / tipar."})
    if p.get("export") == "xlsx":
        return isapti17_xlsx(it_park.isapti17(year))
    if p.get("print") == "notes":
        emp = p.get("employee")
        if emp:
            e = Employee.objects.filter(pk=emp).first()
            if e is None:
                raise NotFound()
            from apps.staff import services as staff

            if not staff.can_see(e, request.user, "payroll"):
                raise NotFound()
        return print_notes(request, year, [int(emp)] if emp else None)
    if p.get("print"):
        return print_annual(request, year)
    return Response(it_park.isapti17(year))


def iu17_report(request, year: int, month: int):
    p = request.query_params
    if p.get("export") == "xml":
        raise ValidationError({"detail": "Pentru IU17 nu avem schema XML oficială: se depune după calculul din Excel / tipar."})
    if p.get("export") == "xlsx":
        return iu17_xlsx(it_park.month_tax(year, month))
    if p.get("print"):
        return print_month(request, year, month)
    return Response(_month_json(it_park.month_tax(year, month)))


# --- previzualizarea formelor în editor -------------------------------------------------------------------------------------
def _sample_month():
    doc = ItParkMonth.objects.order_by("-year", "-month").first()
    if doc:
        return doc.year, doc.month
    today = timezone.localdate()
    return today.year, today.month


def sample_month(request, lang, options):
    y, m = _sample_month()
    return month_context(request, y, m, lang)


def sample_annual(request, lang, options):
    return annual_context(request, _sample_month()[0], lang)


def sample_notes(request, lang, options):
    year = _sample_month()[0]
    ctx = notes_context(request, year, None, lang)
    if not ctx["doc"]["notes"]:
        raise ValueError(f"Nu există încă salarii plătite în regimul IT Park în {year}.")
    ctx["doc"]["notes"] = ctx["doc"]["notes"][:2]
    return ctx

