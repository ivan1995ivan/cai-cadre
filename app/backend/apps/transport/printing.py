"""Tiparul cursei: foaia de parcurs cu segmentele pe țări, plata pe km și calculul diurnei pe zile."""
from decimal import Decimal

from django.utils import timezone

from apps.printing.renderer import company_context
from apps.printing.views import print_document

from .services import fmt, totals


def _dt(value):
    return timezone.localtime(value).strftime("%d.%m.%Y %H:%M") if value else ""


def _money(value):
    from apps.payroll.printing import _money as money

    return money(value)


def trip_context(request, trip, lang="ro") -> dict:
    legs = [{"no": n, "country": f"{leg.country.code} — {leg.country.name_ro}", "entered": _dt(leg.entered), "left": _dt(leg.left),
             "ops": ", ".join(x for x, on in (("încărcare", leg.loading), ("descărcare", leg.unloading), ("masa asigurată", leg.meals))
                              if on), "km": fmt(leg.km) if leg.km is not None else ""}
            for n, leg in enumerate(trip.legs.select_related("country").order_by("entered", "id"), start=1)]
    diems = [{"name": d.employment.employee.full_name(), "day": d.day.strftime("%d.%m.%Y"),
              "country": d.country.code if d.country_id else "MD", "hours": fmt(d.hours, 2), "pct": fmt(d.pct, 2),
              "norm": f"{fmt(d.norm, 2)} {d.currency}", "fx": fmt(d.fx_rate, 4) if d.currency != "MDL" else "",
              "amount": _money(d.amount), "taxable": _money(d.taxable) if d.taxable else "", "how": d.how}
             for d in trip.diems.select_related("employment__employee", "country").order_by("employment", "day", "sort")]
    t = totals(trip)
    return {"company": company_context(request, lang), "lang": lang, "options": {}, "legs": legs, "diems": diems,
            "doc": {"number": trip.number, "status": trip.get_status_display(), "approved": trip.status == "approved",
                    "driver": trip.driver.employee.full_name(), "driver_tab": trip.driver.employee.tab_number,
                    "co_driver": trip.co_driver.employee.full_name() if trip.co_driver_id else "",
                    "vehicle": str(trip.vehicle), "trailer": str(trip.trailer) if trip.trailer_id else "",
                    "kind": trip.get_kind_display(), "scope": trip.get_scope_display(), "route": trip.route,
                    "departure": _dt(trip.departure), "arrival": _dt(trip.arrival),
                    "odometer_out": trip.odometer_out or "", "odometer_in": trip.odometer_in or "", "km": fmt(trip.km),
                    "km_rate": fmt(trip.km_rate) if trip.km_rate is not None else "", "km_amount": _money(trip.km_amount),
                    "adr": trip.adr, "note": trip.note},
            "totals": {"per_diem": _money(t["per_diem"]), "per_diem_taxable": _money(t["per_diem_taxable"]) if t["per_diem_taxable"] else ""},
            "today": timezone.localdate().strftime("%d.%m.%Y"),
            "placeholders": {"număr": trip.number, "data": _dt(trip.departure)[:10]}}


def print_trip(request, trip):
    from apps.payroll.payment_printing import _lang

    lang = _lang(request)
    return print_document(request, "trip_sheet", trip_context(request, trip, lang), template_id=request.query_params.get("template"),
                          title=f"Foaia de parcurs nr. {trip.number}", lang=lang)


def sample_trip(request, lang, options):
    from .models import Trip

    trip = Trip.objects.first()
    if trip is None:
        raise ValueError("Nu există încă curse (foi de parcurs).")
    return trip_context(request, trip, lang)


# --- fișa KPI ------------------------------------------------------------------------------------------------------------
def kpi_context(request, sheet, lang="ro") -> dict:
    from . import kpi

    def num(v, unit=""):
        return "—" if v is None else fmt(v, 2) + (f" {unit}" if unit else "")

    rows = []
    for n, ln in enumerate(sheet.lines.select_related("employee", "employment__occupation", "scheme").order_by("sort", "id"), start=1):
        items = [{"name": d["name"], "value": num(d["value"]), "unit": d.get("unit") or "",
                  "score": num(d["score"], "%"), "weight": fmt(d["weight"]), "manual": d.get("manual")} for d in ln.details]
        rows.append({"no": n, "tab_number": ln.employee.tab_number, "name": ln.employee.full_name(),
                     "occupation": ln.employment.occupation.name_ro, "scheme": ln.scheme.code, "items": items,
                     "base": _money(ln.base), "score": num(ln.score, "%"), "amount": _money(ln.amount)})
    t = kpi.totals(sheet)
    day = sheet.date.strftime("%d.%m.%Y")
    return {"company": company_context(request, lang), "lang": lang, "options": {}, "rows": rows,
            "doc": {"number": sheet.number, "date": day, "period": f"{sheet.month:02d}.{sheet.year}",
                    "status": sheet.get_status_display(), "approved": sheet.status == "approved", "note": sheet.note,
                    "subdivision": sheet.subdivision.name_ro if sheet.subdivision_id else ""},
            "totals": {"amount": _money(Decimal(str(t["amount"])))}, "today": timezone.localdate().strftime("%d.%m.%Y"),
            "placeholders": {"număr": sheet.number, "data": day}}


def print_kpi(request, sheet):
    from apps.payroll.payment_printing import _lang

    lang = _lang(request)
    return print_document(request, "kpi_sheet", kpi_context(request, sheet, lang), template_id=request.query_params.get("template"),
                          title=f"Fișa KPI nr. {sheet.number}", lang=lang)


def sample_kpi(request, lang, options):
    from .models import KpiSheet

    sheet = KpiSheet.objects.filter(lines__isnull=False).first()
    if sheet is None:
        raise ValueError("Nu există încă fișe KPI cu rânduri.")
    return kpi_context(request, sheet, lang)
