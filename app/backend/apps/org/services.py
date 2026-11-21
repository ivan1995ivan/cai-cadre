"""Statele de personal: aprobarea, versiunea nouă, diferențele, totalurile și ocuparea posturilor."""
from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.deletion import ensure_not_marked

from .models import STAFF_CATEGORY, DictItem, StaffList, StaffListLine

ZERO = Decimal("0")

# Cine ocupă posturile: modulul de angajați (Etapa 2) adaugă aici o funcție
#   provider(staff_list, on_date) -> {(subdivision_id, occupation_id): {"occupied": Decimal, "temporary": Decimal,
#                                                                         "holders": [{"name", "units", "kind"}]}}
# Până atunci posturile apar toate vacante.
OCCUPANCY_PROVIDERS: list = []


def current(on_date=None) -> StaffList | None:
    """Statele aprobate în vigoare la data dată (implicit azi)."""
    on_date = on_date or timezone.localdate()
    return (StaffList.objects.filter(status="approved", effective_from__lte=on_date)
            .order_by("-effective_from", "-id").first())


def check_editable(staff_list: StaffList):
    ensure_not_marked(staff_list)
    if staff_list.status != "draft":
        raise ValidationError({"detail": "Statele aprobate nu se mai modifică. Faceți o versiune nouă."})


@transaction.atomic
def approve(staff_list: StaffList, user=None) -> StaffList:
    check_editable(staff_list)
    if not staff_list.lines.exists():
        raise ValidationError({"detail": "Statele de personal nu au niciun rând."})
    bad = staff_list.lines.filter(units__lte=0).count()
    if bad:
        raise ValidationError({"detail": f"{bad} rânduri au unități zero sau negative."})
    clash = StaffList.objects.filter(status="approved", effective_from=staff_list.effective_from).exclude(pk=staff_list.pk)
    if clash.exists():
        raise ValidationError({"detail": "Există deja state aprobate în vigoare de la aceeași dată. Anulați-le sau "
                                         "alegeți altă dată."})
    staff_list.status = "approved"
    staff_list.approved_at = timezone.now()
    staff_list.save(update_fields=["status", "approved_at"])
    return staff_list


@transaction.atomic
def cancel(staff_list: StaffList) -> StaffList:
    if staff_list.status == "cancelled":
        return staff_list
    staff_list.status = "cancelled"
    staff_list.save(update_fields=["status"])
    return staff_list


@transaction.atomic
def new_version(source: StaffList, effective_from, user=None) -> StaffList:
    """Versiune nouă (ciornă) cu toate rândurile versiunii de bază, legată de ea pentru comparație."""
    if source.status == "draft":
        raise ValidationError({"detail": "Versiunea nouă se face dintr-un stat aprobat; ciorna se modifică direct."})
    copy = StaffList.objects.create(
        effective_from=effective_from, basis=source.basis, previous=source, created_by=user,
        notes="", status="draft",
    )
    StaffListLine.objects.bulk_create([
        StaffListLine(staff_list=copy, subdivision_id=line.subdivision_id, occupation_id=line.occupation_id,
                      category_id=line.category_id, units=line.units, base_salary=line.base_salary,
                      allowance_pct=line.allowance_pct, note=line.note, sort=line.sort)
        for line in source.lines.all()
    ])
    return copy


def _key(line):
    return (line.subdivision_id, line.occupation_id)


def diff(staff_list: StaffList, base: StaffList | None = None, lang: str = "ro") -> list:
    """Ce s-a schimbat față de versiunea anterioară: posturi introduse, lichidate, cu unități / salariu modificat."""
    base = base or staff_list.previous
    if base is None:
        return []
    old = defaultdict(lambda: {"units": ZERO, "salary": None})
    new = defaultdict(lambda: {"units": ZERO, "salary": None})
    names = {}
    for target, sl in ((old, base), (new, staff_list)):
        for line in sl.lines.select_related("subdivision", "occupation"):
            k = _key(line)
            target[k]["units"] += line.units
            target[k]["salary"] = line.base_salary
            names[k] = (line.subdivision.local_name(lang), line.occupation.code, line.occupation.local_name(lang))
    out = []
    for k in sorted(set(old) | set(new), key=lambda k: names[k]):
        o, n = old.get(k), new.get(k)
        if o is None:
            change = "added"
        elif n is None:
            change = "removed"
        elif o["units"] != n["units"] or o["salary"] != n["salary"]:
            change = "changed"
        else:
            continue
        sub, code, occ = names[k]
        out.append({
            "subdivision": sub, "occupation_code": code, "occupation": occ, "change": change,
            "units_before": str(o["units"]) if o else "0", "units_after": str(n["units"]) if n else "0",
            "salary_before": str(o["salary"]) if o and o["salary"] is not None else "",
            "salary_after": str(n["salary"]) if n and n["salary"] is not None else "",
        })
    return out


def category_label(category, lang: str = "ro") -> str:
    """Denumirea categoriei de personal (fără categorie — „Fără categorie”)."""
    if category is None:
        return {"ru": "Без категории", "en": "No category"}.get(lang, "Fără categorie")
    return category.local_name(lang)


def totals(staff_list: StaffList, lang: str = "ro") -> dict:
    """Totalurile pe subdiviziuni și pe categorii de personal (efectivul-limită), în ordinea clasificatorului."""
    by_cat = {c.pk: {"id": c.pk, "code": c.code, "name": c.local_name(lang), "units": ZERO, "fund": ZERO}
              for c in DictItem.objects.filter(kind=STAFF_CATEGORY)}
    none = {"id": None, "code": "", "name": category_label(None, lang), "units": ZERO, "fund": ZERO}
    by_sub = {}
    total_units, total_fund = ZERO, ZERO
    for line in staff_list.lines.select_related("subdivision", "occupation", "category", "occupation__category"):
        fund = line.monthly_fund()
        category = line.effective_category()
        cat = by_cat.get(category.pk, none) if category is not None else none
        cat["units"] += line.units
        cat["fund"] += fund
        sub = by_sub.setdefault(line.subdivision_id, {"id": line.subdivision_id, "name": line.subdivision.name_ro,
                                                      "sort": line.subdivision.sort, "units": ZERO, "fund": ZERO})
        sub["units"] += line.units
        sub["fund"] += fund
        total_units += line.units
        total_fund += fund

    def fmt(d):
        return {**d, "units": str(d["units"]), "fund": str(d["fund"])}

    return {
        "categories": [fmt(c) for c in [*by_cat.values(), none] if c["units"]],
        "subdivisions": [fmt(s) for s in sorted(by_sub.values(), key=lambda s: (s["sort"], s["name"]))],
        "units": str(total_units), "fund": str(total_fund),
    }


def occupancy(staff_list: StaffList | None = None, on_date=None, lang: str = "ro") -> dict:
    """Ocuparea posturilor: unități aprobate / ocupate / temporar vacante / vacante, pe fiecare rând."""
    on_date = on_date or timezone.localdate()
    staff_list = staff_list or current(on_date)
    if staff_list is None:
        return {"staff_list": None, "rows": [], "totals": None}
    taken = {}
    for provider in OCCUPANCY_PROVIDERS:
        for k, v in (provider(staff_list, on_date) or {}).items():
            cur = taken.setdefault(k, {"occupied": ZERO, "temporary": ZERO, "holders": []})
            cur["occupied"] += Decimal(v.get("occupied", 0))
            cur["temporary"] += Decimal(v.get("temporary", 0))
            cur["holders"] += v.get("holders", [])
    grouped = {}
    for line in staff_list.lines.select_related("subdivision", "occupation", "category", "occupation__category"):
        k = _key(line)
        category = line.effective_category()
        row = grouped.setdefault(k, {
            "subdivision_id": line.subdivision_id, "subdivision": line.subdivision.local_name(lang),
            "subdivision_sort": line.subdivision.sort, "occupation_id": line.occupation_id,
            "occupation_code": line.occupation.code, "occupation": line.occupation.local_name(lang),
            "category": category.pk if category else None, "category_name": category_label(category, lang), "approved": ZERO,
        })
        row["approved"] += line.units
    rows, t_app, t_occ, t_tmp = [], ZERO, ZERO, ZERO
    for k, row in grouped.items():
        got = taken.get(k, {"occupied": ZERO, "temporary": ZERO, "holders": []})
        vacant = row["approved"] - got["occupied"]
        rows.append({**row, "approved": str(row["approved"]), "occupied": str(got["occupied"]),
                     "temporary": str(got["temporary"]), "vacant": str(vacant), "over": vacant < 0,
                     "holders": got["holders"]})
        t_app += row["approved"]
        t_occ += got["occupied"]
        t_tmp += got["temporary"]
    rows.sort(key=lambda r: (r["subdivision_sort"], r["subdivision"], r["occupation_code"], r["occupation"]))
    return {
        "staff_list": {"id": staff_list.id, "number": staff_list.number, "effective_from": staff_list.effective_from},
        "on_date": on_date, "rows": rows, "employees_module": bool(OCCUPANCY_PROVIDERS),
        "totals": {"approved": str(t_app), "occupied": str(t_occ), "temporary": str(t_tmp), "vacant": str(t_app - t_occ)},
    }
