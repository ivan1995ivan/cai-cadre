"""Acumulările și reținerile planificate din documente: tabelul „Acumulări și rețineri” al ordinului de personal și documentul
„Modificarea acumulărilor planificate”. Același mecanism la amândouă:

- **adaugă** — rând nou în fila „Salariu” (`EmployeePayItem`) pe raportul de muncă, de la data rândului (implicit data
  efectului ordinului / data documentului), până la data dată sau fără termen;
- **modifică** — rândul în vigoare se închide în ajunul datei, iar de la ea se deschide unul nou cu valorile noi (ce nu se
  dă se ia din cel vechi);
- **oprește** — rândul în vigoare primește „până la” (data dată sau ajunul datei „de la”).

Fiecare pas întoarce ce a făcut (`result`), iar anularea (ordinul de anulare, anularea aprobării documentului) revine exact,
în ordine inversă. Dacă rândul a fost schimbat între timp de alt document (sau de mână), anularea se oprește cu eroare:
întâi se anulează documentul de după.
"""
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from rest_framework.exceptions import ValidationError

from .models import EmployeePayItem, OccupationPayItem, PayType

ACTIONS = ("add", "modify", "stop")
DAY = timedelta(days=1)


def _iso(d):
    return d.isoformat() if d else None


def _date(value, field, who):
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        raise ValidationError({"detail": f"{who}: data „{value}” ({field}) nu este validă."}) from None


def _dec(value, field, who):
    if value in (None, ""):
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).replace(",", "."))
    except InvalidOperation:
        raise ValidationError({"detail": f"{who}: „{value}” ({field}) nu este un număr."}) from None


def normalize(row: dict, who: str) -> dict:
    """Rândul tabelului (din parametrii ordinului sau din rândul documentului) cu valorile citite și verificate."""
    from .serializers import row_problem

    action = row.get("action") or "add"
    if action not in ACTIONS:
        raise ValidationError({"detail": f"{who}: acțiunea „{action}” nu există (adaugă / modifică / oprește)."})
    raw_type = row.get("pay_type")
    t = raw_type if isinstance(raw_type, PayType) else PayType.objects.filter(pk=raw_type).first() if raw_type else None
    if t is None:
        raise ValidationError({"detail": f"{who}: alegeți tipul de calcul."})
    out = {"pay_type": t, "action": action, "amount": _dec(row.get("amount"), "suma", who),
           "percent": _dec(row.get("percent"), "procentul", who), "quantity": _dec(row.get("quantity"), "cantitatea", who),
           "date_from": _date(row.get("date_from"), "de la", who), "date_to": _date(row.get("date_to"), "până la", who),
           "document": str(row.get("document") or "")[:200], "target": row.get("target")}
    if action == "add":
        if not t.is_active or t.deletion_mark:
            raise ValidationError({"detail": f"{who}: tipul {t.code} nu este activ."})
        problem = row_problem(t, out["amount"], out["percent"])
        if problem:
            raise ValidationError({"detail": f"{who}, {t.code}: {next(iter(problem.values()))}"})
    elif action == "modify" and t.formula == "auto":
        raise ValidationError({"detail": f"{who}: tipul {t.code} se calculează singur; nu se pune pe angajat."})
    for key in ("amount", "percent", "quantity"):
        if out[key] is not None and out[key] < 0:
            raise ValidationError({"detail": f"{who}, {t.code}: valorile nu pot fi negative."})
    if out["date_from"] and out["date_to"] and out["date_to"] < out["date_from"] and action != "stop":
        raise ValidationError({"detail": f"{who}, {t.code}: „până la” este înaintea lui „de la”."})
    return out


def _target(row: dict, employee, employment, start: date, who: str) -> EmployeePayItem:
    """Rândul care se modifică / se oprește: cel ales sau singurul de acest tip în vigoare la data `start` pe raport."""
    t = row["pay_type"]
    qs = EmployeePayItem.objects.filter(employee=employee, pay_type=t)
    if row.get("target"):
        found = qs.filter(pk=row["target"]).first()
        if found is None:
            raise ValidationError({"detail": f"{who}: rândul ales ({t.code}) nu este al angajatului."})
        return found
    qs = qs.filter(date_from__lte=start).exclude(date_to__lt=start)
    qs = qs.filter(employment=employment) if employment is not None else qs.filter(employment__isnull=True)
    found = list(qs.order_by("date_from", "id"))
    if not found and employment is not None and employment.kind in ("main", "main_student"):
        found = list(EmployeePayItem.objects.filter(employee=employee, pay_type=t, employment__isnull=True, date_from__lte=start)
                     .exclude(date_to__lt=start).order_by("date_from", "id"))
    if not found:
        raise ValidationError({"detail": f"{who}: nu are {t.code} ({t.name_ro}) în vigoare la {start:%d.%m.%Y}."})
    if len(found) > 1:
        raise ValidationError({"detail": f"{who}: are mai multe rânduri {t.code} în vigoare la {start:%d.%m.%Y}; alegeți rândul."})
    return found[0]


def apply(row: dict, *, employee, employment, default_from: date, reference: str, who: str, source: dict) -> dict:
    """Aplică un rând (adaugă / modifică / oprește); `source` = {"order_item": …} sau {"change_line": …}. Întoarce ce s-a făcut."""
    row = normalize(row, who)
    t, action = row["pay_type"], row["action"]
    start = row["date_from"] or default_from
    document = row["document"] or reference
    result = {"action": action, "pay_type": t.code}
    if action in ("modify", "stop"):
        new_to = row["date_to"] if action == "stop" and row["date_to"] else start - DAY
        old = _target(row, employee, employment, new_to + DAY, who)
        if new_to < old.date_from:
            raise ValidationError({"detail": f"{who}: rândul {t.code} începe la {old.date_from:%d.%m.%Y}; se poate opri / modifica "
                                             f"cel mai devreme de a doua zi (ca să-l scoateți de tot, anulați documentul lui)."})
        if old.date_to is not None and old.date_to <= new_to:
            raise ValidationError({"detail": f"{who}: rândul {t.code} se termină deja la {old.date_to:%d.%m.%Y}."})
        result.update({"closed": old.pk, "closed_before": _iso(old.date_to), "closed_to": _iso(new_to)})
        previous_to = old.date_to
        old.date_to = new_to
        old.save(update_fields=["date_to"])
        if action == "modify":
            new = EmployeePayItem.objects.create(
                employee=employee, employment=old.employment, pay_type=t,
                amount=row["amount"] if row["amount"] is not None else old.amount,
                percent=row["percent"] if row["percent"] is not None else old.percent,
                quantity=row["quantity"] if row["quantity"] is not None else old.quantity,
                date_from=start, date_to=row["date_to"] if row["date_to"] is not None else previous_to,
                document=document, **source)
            result.update({"created": new.pk, "created_to": _iso(new.date_to)})
    else:
        new = EmployeePayItem.objects.create(employee=employee, employment=employment, pay_type=t, amount=row["amount"],
                                             percent=row["percent"], quantity=row["quantity"], date_from=start,
                                             date_to=row["date_to"], document=document, **source)
        result.update({"created": new.pk, "created_to": _iso(new.date_to)})
    return result


def undo(results, who: str):
    """Întoarce rândurile aplicate (lista `apply`, în ordine inversă)."""
    for res in reversed(list(results or [])):
        if res.get("created"):
            new = EmployeePayItem.objects.filter(pk=res["created"]).first()
            if new is not None:
                if _iso(new.date_to) != res.get("created_to"):
                    raise ValidationError({"detail": f"{who}: rândul {res.get('pay_type')} din fila „Salariu” a fost schimbat după "
                                                     f"aceea (oprit / modificat la {new.date_to:%d.%m.%Y}); anulați întâi documentul "
                                                     f"care l-a schimbat."})
                if EmployeePayItem.objects.filter(pk=new.pk).exists():
                    new.delete()
        if res.get("closed"):
            old = EmployeePayItem.objects.filter(pk=res["closed"]).first()
            if old is not None:
                if _iso(old.date_to) != res.get("closed_to"):
                    raise ValidationError({"detail": f"{who}: rândul {res.get('pay_type')} din fila „Salariu” a fost schimbat după "
                                                     f"aceea; anulați întâi documentul care l-a schimbat."})
                old.date_to = date.fromisoformat(res["closed_before"]) if res.get("closed_before") else None
                old.save(update_fields=["date_to"])


def occupation_defaults(occupation) -> list:
    """Acumulările-tip ale funcției ca rânduri „adaugă” ale tabelului din ordin (doar tipurile active)."""
    if occupation is None:
        return []
    out = []
    for x in OccupationPayItem.objects.filter(occupation=occupation, pay_type__is_active=True).select_related("pay_type"):
        out.append({"pay_type": x.pay_type_id, "action": "add", "amount": _str(x.amount), "percent": _str(x.percent),
                    "quantity": _str(x.quantity), "date_from": None, "date_to": None, "document": ""})
    return out


def _str(value):
    return None if value is None else format(value.normalize() if value == value.to_integral_value() else value, "f")
