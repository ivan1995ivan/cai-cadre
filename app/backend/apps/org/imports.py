"""Importurile din Excel ale Etapei 1: funcțiile (CORM), specialitățile, subdiviziunile și rândurile statelor."""
from decimal import Decimal

from apps.core.excel_import import Column, RowError, Spec

from .models import STAFF_CATEGORY, DictItem, Occupation, Specialty, StaffListLine, Subdivision

CATEGORY_HINT = ("Categoria de personal: codul (cifra grupei CORM, de ex. 2) sau denumirea din clasificatorul „Categoriile "
                 "de personal”; goală — după prima cifră a codului CORM al funcției.")


def _category(value):
    """Categoria de personal după cod sau denumire (RO / RU / EN, întreagă sau începutul ei)."""
    if value in (None, ""):
        return None
    v = str(value).strip().lower()
    if v.endswith(".0"):  # Excel dă cifra ca număr: 2 → „2.0”
        v = v[:-2]
    items = list(DictItem.objects.filter(kind=STAFF_CATEGORY, deletion_mark=False))
    for item in items:
        if item.code.lower() == v:
            return item
    names = [(n.lower(), item) for item in items for n in (item.name_ro, item.name_ru, item.name_en) if n]
    for name, item in names:
        if name == v:
            return item
    for name, item in names:
        if name.startswith(v):
            return item
    raise RowError(f"Categoria „{value}” nu există. {CATEGORY_HINT}")


def _names(values, obj):
    for f in ("name_ru", "name_en"):
        if values.get(f):
            setattr(obj, f, values[f])


# --- funcțiile (CORM 006-2021) -----------------------------------------------
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
    code="occupations", title="Funcțiile (Clasificatorul ocupațiilor CORM 006-2021)", sheet_title="Functii",
    columns=[
        Column("code", "Cod CORM", example="241106", aliases=("cod", "код", "cod ocupatie")),
        Column("name_ro", "Denumirea (RO)", required=True, example="Contabil",
               aliases=("denumirea", "denumire", "ocupatia", "functia")),
        Column("name_ru", "Denumirea (RU)", example="Бухгалтер", aliases=("наименование",)),
        Column("name_en", "Denumirea (EN)", example="Accountant"),
        Column("category", "Categoria de personal", example="2"),
        Column("isco_code", "Cod ISCO-08", example="2411"),
        Column("weekly_hours", "Ore pe săptămână", kind="decimal", example=40),
        Column("base_leave_days", "Concediu de bază (zile)", kind="int", example=28),
        Column("extra_leave_days", "Concediu suplimentar (zile)", kind="int", example=0),
        Column("harmful", "Condiții vătămătoare (da/nu)", kind="bool", example="nu"),
        Column("notes", "Observații"),
    ],
    save_row=_save_occupation,
    notes=["Rândul cu același cod CORM se actualizează; fără cod — după denumire.", CATEGORY_HINT,
           "Clasificatorul complet CORM 006-2021 (Ordinul MMPS nr. 11/2021, cu modificările ulterioare) se poate lipi aici "
           "(codul și denumirea sunt suficiente; categoria se pune după prima cifră a codului)."],
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
        Column("code", "Cod", example="0411"),
        Column("name_ro", "Denumirea (RO)", required=True, example="Contabilitate"),
        Column("name_ru", "Denumirea (RU)", example="Бухгалтерский учёт"),
        Column("name_en", "Denumirea (EN)", example="Accounting"),
        Column("kind", "Nivelul (higher / postsecondary / secondary / other)", example="higher", aliases=("nivelul", "tipul")),
        Column("isced", "Cod ISCED-F", example="0411"),
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
    if values.get("extra_leave_days") is not None:
        obj.extra_leave_days = values["extra_leave_days"]
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
    code="subdivisions", title="Subdiviziunile întreprinderii", sheet_title="Subdiviziuni",
    columns=[
        Column("code", "Cod", example="PROD"),
        Column("name_ro", "Denumirea (RO)", required=True, example="Secția de producție"),
        Column("name_ru", "Denumirea (RU)", example="Производственный цех"),
        Column("name_en", "Denumirea (EN)"),
        Column("parent", "Subdiviziunea-părinte (cod sau denumire)"),
        Column("kind", "Tipul (department / section / workshop / branch / warehouse / other)", example="workshop",
               aliases=("tipul", "felul", "тип")),
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
        category=_category(values.get("category")), note=values.get("note", ""),
        sort=ctx.setdefault("_sort", 0) + 10,
    )
    ctx["_sort"] = line.sort
    line.save()
    return f"{sub.name_ro} — {occ.code} {occ.name_ro}: {line.units}", "created"


STAFF_LINES = Spec(
    code="staff_lines", title="Rândurile statelor de personal", sheet_title="State",
    columns=[
        Column("subdivision", "Subdiviziunea (cod sau denumire)", required=True, example="Secția de producție",
               aliases=("subdiviziunea", "sectia", "secția")),
        Column("occupation_code", "Cod CORM", example="753117", aliases=("codul functiei", "cod")),
        Column("occupation", "Funcția", example="Cusător în confecții", aliases=("denumirea functiei",)),
        Column("units", "Unități", required=True, kind="decimal", example=2.5,
               aliases=("numarul de unitati", "unitati aprobate")),
        Column("base_salary", "Salariul de funcție", kind="decimal", example=9500),
        Column("allowance_pct", "Sporuri fixe (%)", kind="decimal", example=0),
        Column("category", "Categoria de personal (goală — a funcției)", aliases=("categoria de personal", "categoria")),
        Column("note", "Observații", aliases=("mentiune", "mențiune")),
    ],
    save_row=_save_line,
    notes=["Se adaugă rânduri în statul de personal deschis (ciornă). Funcția se caută după cod CORM, apoi după denumire.",
           "Bifa „Creează funcțiile lipsă” adaugă în clasificator funcțiile negăsite (după denumire).", CATEGORY_HINT],
)

SPECS = {s.code: s for s in (OCCUPATIONS, SPECIALTIES, SUBDIVISIONS, STAFF_LINES)}
