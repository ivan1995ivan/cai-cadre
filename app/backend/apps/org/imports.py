"""Importurile din Excel ale Etapei 1: funcțiile (CORM), specialitățile, subdiviziunile și rândurile statelor."""
from decimal import Decimal

from apps.core.excel_import import Column, RowError, Spec

from .models import STAFF_CATEGORIES, Occupation, Specialty, StaffListLine, Subdivision

CATEGORY_CODES = {code for code, _ in STAFF_CATEGORIES}
CATEGORY_NAMES = {name.lower(): code for code, name in STAFF_CATEGORIES}
CATEGORY_HINT = "Categoria: " + ", ".join(f"{code} = {name}" for code, name in STAFF_CATEGORIES)


def _category(value) -> str:
    if not value:
        return ""
    v = str(value).strip().lower()
    if v in CATEGORY_CODES:
        return v
    if v in CATEGORY_NAMES:
        return CATEGORY_NAMES[v]
    for name, code in CATEGORY_NAMES.items():
        if v and v in name:
            return code
    raise RowError(f"Categoria „{value}” nu există. {CATEGORY_HINT}")


def _names(values, obj):
    for f in ("name_ru", "name_en"):
        if values.get(f):
            setattr(obj, f, values[f])


# --- funcțiile (CORM 006-21) -------------------------------------------------
def _save_occupation(values, ctx):
    code, name = values.get("code", ""), values["name_ro"]
    obj = Occupation.objects.filter(code=code).first() if code else Occupation.objects.filter(name_ro__iexact=name).first()
    status = "updated" if obj else "created"
    obj = obj or Occupation(code=code)
    obj.name_ro = name
    _names(values, obj)
    if values.get("category"):
        obj.category = _category(values["category"])
    for f in ("isco_code", "notes"):
        if values.get(f):
            setattr(obj, f, values[f])
    for f in ("weekly_hours",):
        if values.get(f) is not None:
            setattr(obj, f, values[f])
    for f in ("base_leave_days", "extra_leave_days"):
        if values.get(f) is not None:
            setattr(obj, f, values[f])
    if values.get("harmful") is not None and "harmful" in values:
        obj.harmful = bool(values["harmful"])
    obj.save()
    return obj, status


OCCUPATIONS = Spec(
    code="occupations", title="Funcțiile (Clasificatorul ocupațiilor CORM 006-21)", sheet_title="Functii",
    columns=[
        Column("code", "Cod CORM", example="221104", aliases=("cod", "код", "cod ocupatie")),
        Column("name_ro", "Denumirea (RO)", required=True, example="Medic de familie",
               aliases=("denumirea", "denumire", "ocupatia", "functia")),
        Column("name_ru", "Denumirea (RU)", example="Семейный врач", aliases=("наименование",)),
        Column("name_en", "Denumirea (EN)", example="Family physician"),
        Column("category", "Categoria de personal", example="physicians"),
        Column("isco_code", "Cod ISCO-08", example="2211"),
        Column("weekly_hours", "Ore pe săptămână", kind="decimal", example=35),
        Column("base_leave_days", "Concediu de bază (zile)", kind="int", example=28),
        Column("extra_leave_days", "Concediu suplimentar (zile)", kind="int", example=0),
        Column("harmful", "Condiții vătămătoare (da/nu)", kind="bool", example="nu"),
        Column("notes", "Observații"),
    ],
    save_row=_save_occupation,
    notes=["Rândul cu același cod CORM se actualizează; fără cod — după denumire.", CATEGORY_HINT,
           "Clasificatorul complet CORM 006-21 se poate lua de pe site-ul Ministerului Muncii și Protecției Sociale "
           "și lipi aici (codul și denumirea sunt suficiente)."],
)


# --- specialitățile -----------------------------------------------------------
def _save_specialty(values, ctx):
    code, name = values.get("code", ""), values["name_ro"]
    obj = Specialty.objects.filter(code=code).first() if code else Specialty.objects.filter(name_ro__iexact=name).first()
    status = "updated" if obj else "created"
    obj = obj or Specialty(code=code)
    obj.name_ro = name
    _names(values, obj)
    kind = (values.get("kind") or "").strip().lower()
    if kind:
        kinds = dict(Specialty.KINDS)
        match = kind if kind in kinds else next((k for k, n in kinds.items() if n.lower().startswith(kind)), None)
        if not match:
            raise RowError(f"Tipul „{values['kind']}” nu există: {', '.join(kinds)}.")
        obj.kind = match
    if values.get("isced"):
        obj.isced = values["isced"]
    obj.save()
    return obj, status


SPECIALTIES = Spec(
    code="specialties", title="Specialitățile", sheet_title="Specialitati",
    columns=[
        Column("code", "Cod", example="TO"),
        Column("name_ro", "Denumirea (RO)", required=True, example="Ortopedie și traumatologie"),
        Column("name_ru", "Denumirea (RU)", example="Ортопедия и травматология"),
        Column("name_en", "Denumirea (EN)", example="Orthopaedics and traumatology"),
        Column("kind", "Tipul (medical / pharmacy / nursing / other)", example="medical"),
        Column("isced", "Cod ISCED", example="0912"),
    ],
    save_row=_save_specialty,
)


# --- subdiviziunile -----------------------------------------------------------
def _save_subdivision(values, ctx):
    code, name = values.get("code", ""), values["name_ro"]
    obj = Subdivision.objects.filter(code=code).first() if code else Subdivision.objects.filter(name_ro__iexact=name).first()
    status = "updated" if obj else "created"
    obj = obj or Subdivision(code=code)
    obj.name_ro = name
    _names(values, obj)
    parent = values.get("parent")
    if parent:
        found = Subdivision.objects.filter(code=parent).first() or Subdivision.objects.filter(name_ro__iexact=parent).first()
        if not found:
            raise RowError(f"Subdiviziunea-părinte „{parent}” nu există (puneți-o mai sus în fișier).")
        if obj.pk and found.pk == obj.pk:
            raise RowError("O subdiviziune nu poate fi propriul părinte.")
        obj.parent = found
    kind = (values.get("kind") or "").strip().lower()
    if kind:
        kinds = dict(Subdivision.KINDS)
        match = kind if kind in kinds else next((k for k, n in kinds.items() if n.lower().startswith(kind)), None)
        if not match:
            raise RowError(f"Tipul „{values['kind']}” nu există: {', '.join(kinds)}.")
        obj.kind = match
    for f in ("beds", "extra_leave_days"):
        if values.get(f) is not None:
            setattr(obj, f, values[f])
    if values.get("reduced_hours") is not None:
        obj.reduced_hours = values["reduced_hours"]
    if "harmful" in values and values["harmful"] is not None:
        obj.harmful = bool(values["harmful"])
    if values.get("head_name"):
        obj.head_name = values["head_name"]
    if values.get("sort") is not None:
        obj.sort = values["sort"]
    obj.save()
    return obj, status


SUBDIVISIONS = Spec(
    code="subdivisions", title="Subdiviziunile instituției", sheet_title="Subdiviziuni",
    columns=[
        Column("code", "Cod", example="TR1"),
        Column("name_ro", "Denumirea (RO)", required=True, example="Secția traumatologie nr. 1"),
        Column("name_ru", "Denumirea (RU)", example="Отделение травматологии № 1"),
        Column("name_en", "Denumirea (EN)"),
        Column("parent", "Subdiviziunea-părinte (cod sau denumire)"),
        Column("kind", "Tipul (clinical / paraclinical / ambulatory / admin / other)", example="clinical"),
        Column("beds", "Paturi", kind="int", example=40),
        Column("harmful", "Condiții vătămătoare (da/nu)", kind="bool", example="nu"),
        Column("extra_leave_days", "Concediu suplimentar (zile)", kind="int", example=0),
        Column("reduced_hours", "Ore pe săptămână (zi redusă)", kind="decimal"),
        Column("head_name", "Șeful subdiviziunii"),
        Column("sort", "Ordinea", kind="int", example=10),
    ],
    save_row=_save_subdivision,
    notes=["Părintele trebuie să fie mai sus în fișier sau să existe deja în sistem."],
)


# --- rândurile statelor de personal (în statul deschis, ciornă) ------------------
def _find_subdivision(value):
    obj = Subdivision.objects.filter(code=value).first() or Subdivision.objects.filter(name_ro__iexact=value).first()
    if not obj:
        raise RowError(f"Subdiviziunea „{value}” nu există. Importați întâi subdiviziunile.")
    return obj


def _find_occupation(code, name, ctx):
    obj = None
    if code:
        obj = Occupation.objects.filter(code=code).first()
    if not obj and name:
        obj = Occupation.objects.filter(name_ro__iexact=name).first()
    if not obj and name and ctx.get("create_occupations"):
        obj = Occupation.objects.create(code=code or "", name_ro=name)
    if not obj:
        label = f"{code or ''} {name or ''}".strip()
        raise RowError(f"Funcția „{label}” nu există în clasificator (sau bifați „Creează funcțiile lipsă”).")
    return obj


def _save_line(values, ctx):
    staff_list = ctx["staff_list"]
    sub = _find_subdivision(values["subdivision"])
    occ = _find_occupation(values.get("occupation_code"), values.get("occupation"), ctx)
    if not values.get("units") or values["units"] <= 0:
        raise RowError("Unitățile trebuie să fie mai mari decât zero.")
    line = StaffListLine(
        staff_list=staff_list, subdivision=sub, occupation=occ, units=values["units"],
        base_salary=values.get("base_salary") or Decimal("0"), allowance_pct=values.get("allowance_pct") or Decimal("0"),
        category=_category(values.get("category")) if values.get("category") else "",
        effort_note=values.get("effort_note", ""), note=values.get("note", ""),
        sort=ctx.setdefault("_sort", 0) + 10,
    )
    ctx["_sort"] = line.sort
    line.save()
    return f"{sub.name_ro} — {occ.code} {occ.name_ro}: {line.units}", "created"


STAFF_LINES = Spec(
    code="staff_lines", title="Rândurile statelor de personal", sheet_title="State",
    columns=[
        Column("subdivision", "Subdiviziunea (cod sau denumire)", required=True, example="Secția traumatologie nr. 1",
               aliases=("subdiviziunea", "sectia", "secția")),
        Column("occupation_code", "Cod CORM", example="221104", aliases=("codul functiei", "cod")),
        Column("occupation", "Funcția", example="Medic traumatolog-ortoped", aliases=("denumirea functiei",)),
        Column("units", "Unități", required=True, kind="decimal", example=2.5,
               aliases=("numarul de unitati", "unitati aprobate")),
        Column("base_salary", "Salariul de funcție", kind="decimal", example=14660),
        Column("allowance_pct", "Sporuri fixe (%)", kind="decimal", example=0),
        Column("category", "Categoria de personal"),
        Column("effort_note", "Mențiune (efort)"),
        Column("note", "Observații"),
    ],
    save_row=_save_line,
    notes=["Se adaugă rânduri în statul de personal deschis (ciornă). Funcția se caută după cod CORM, apoi după denumire.",
           "Bifa „Creează funcțiile lipsă” adaugă în clasificator funcțiile negăsite (după denumire).", CATEGORY_HINT],
)

SPECS = {s.code: s for s in (OCCUPATIONS, SPECIALTIES, SUBDIVISIONS, STAFF_LINES)}
