"""Tarifele pe tipuri de ore ale raportului de muncă din documente: tabelul „Tarife pe tipuri de ore” al ordinului (angajare,
modificarea salariului / condițiilor, cumul) — același mecanism ca la „Acumulări și rețineri” (apps.payroll.planned):

- **adaugă** — rând nou (`JobHourRate`) de la data rândului (implicit data efectului ordinului), până la data dată sau fără termen;
  tipul nu poate avea două rânduri în vigoare în aceeași zi;
- **modifică** — rândul în vigoare se închide în ajunul datei, de la ea se deschide unul nou (ce nu se dă se ia din cel vechi);
- **oprește** — rândul în vigoare primește „până la” (data dată sau ajunul datei „de la”).

Tarifele se plătesc la modalitățile „pe tipuri de ore” și „mixt” (`staff.models.RATE_MODES`): la celelalte nu se pun. Anularea
ordinului revine exact, în ordine inversă; dacă rândul a fost schimbat între timp, se oprește cu eroare.
"""
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from rest_framework.exceptions import ValidationError

from apps.staff.models import PAY_MODES, RATE_MODES

from .models import HourType, JobHourRate, OccupationHourRate

ACTIONS = ("add", "modify", "stop")
DAY = timedelta(days=1)
MODE_LABELS = dict(PAY_MODES)


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
    try:
        out = Decimal(str(value).replace(",", "."))
    except InvalidOperation:
        raise ValidationError({"detail": f"{who}: „{value}” ({field}) nu este un număr."}) from None
    if out < 0:
        raise ValidationError({"detail": f"{who}: {field} nu poate fi negativ."})
    return out


def mode_on(job, day) -> str:
    """Modalitatea de remunerare a raportului la data dată (din istoric)."""
    from apps.staff import services as staff

    return staff.values_on(job, day)["pay_mode"]


def check_mode(job, day, who):
    mode = mode_on(job, day)
    if mode not in RATE_MODES:
        raise ValidationError({"detail": f"{who}: tarifele pe tipuri de ore se plătesc la modalitatea „Pe tipuri de ore” sau „Mixt”; "
                                         f"raportul are „{MODE_LABELS.get(mode, mode)}” la {day:%d.%m.%Y}."})


def check_overlap(job, hour_type, start, end, who, exclude=None):
    qs = JobHourRate.objects.filter(employment=job, hour_type=hour_type).exclude(pk=exclude)
    for r in qs:
        if r.date_from <= (end or date.max) and (r.date_to is None or r.date_to >= start):
            raise ValidationError({"detail": f"{who}: {hour_type.code} are deja tarif în vigoare "
                                             f"({r.date_from:%d.%m.%Y} – {r.date_to.strftime('%d.%m.%Y') if r.date_to else '…'}); "
                                             f"folosiți „modifică” sau „oprește”."})


def normalize(row: dict, who: str) -> dict:
    action = row.get("action") or "add"
    if action not in ACTIONS:
        raise ValidationError({"detail": f"{who}: acțiunea „{action}” nu există (adaugă / modifică / oprește)."})
    raw = row.get("hour_type")
    ht = raw if isinstance(raw, HourType) else HourType.objects.filter(pk=raw).first() if raw else None
    if ht is None:
        raise ValidationError({"detail": f"{who}: alegeți tipul de ore."})
    out = {"hour_type": ht, "action": action, "rate": _dec(row.get("rate"), "tariful", who),
           "guaranteed_hours": _dec(row.get("guaranteed_hours"), "orele garantate", who),
           "date_from": _date(row.get("date_from"), "de la", who), "date_to": _date(row.get("date_to"), "până la", who),
           "document": str(row.get("document") or "")[:200], "target": row.get("target")}
    if action == "add":
        if not ht.is_active or ht.deletion_mark:
            raise ValidationError({"detail": f"{who}: tipul de ore {ht.code} nu este activ."})
        if out["rate"] is None:
            raise ValidationError({"detail": f"{who}, {ht.code}: dați tariful pe oră."})
    if out["guaranteed_hours"] is not None and out["guaranteed_hours"] > 744:
        raise ValidationError({"detail": f"{who}, {ht.code}: orele garantate pe lună sunt cel mult 744."})
    if out["date_from"] and out["date_to"] and out["date_to"] < out["date_from"] and action != "stop":
        raise ValidationError({"detail": f"{who}, {ht.code}: „până la” este înaintea lui „de la”."})
    return out


def _target(row, job, day, who) -> JobHourRate:
    ht = row["hour_type"]
    qs = JobHourRate.objects.filter(employment=job, hour_type=ht)
    if row.get("target"):
        found = qs.filter(pk=row["target"]).first()
        if found is None:
            raise ValidationError({"detail": f"{who}: rândul ales ({ht.code}) nu este al raportului."})
        return found
    found = list(qs.filter(date_from__lte=day).exclude(date_to__lt=day))
    if not found:
        raise ValidationError({"detail": f"{who}: nu are tarif {ht.code} ({ht.name_ro}) în vigoare la {day:%d.%m.%Y}."})
    return found[0]


def apply(row: dict, *, job, default_from: date, reference: str, who: str, order_item=None) -> dict:
    row = normalize(row, who)
    ht, action = row["hour_type"], row["action"]
    start = row["date_from"] or default_from
    document = row["document"] or reference
    result = {"action": action, "hour_type": ht.code}
    if action in ("modify", "stop"):
        new_to = row["date_to"] if action == "stop" and row["date_to"] else start - DAY
        old = _target(row, job, new_to + DAY, who)
        if new_to < old.date_from:
            raise ValidationError({"detail": f"{who}: tariful {ht.code} începe la {old.date_from:%d.%m.%Y}; se poate opri / modifica "
                                             f"cel mai devreme de a doua zi (ca să-l scoateți de tot, anulați documentul lui)."})
        if old.date_to is not None and old.date_to <= new_to:
            raise ValidationError({"detail": f"{who}: tariful {ht.code} se termină deja la {old.date_to:%d.%m.%Y}."})
        result.update({"closed": old.pk, "closed_before": _iso(old.date_to), "closed_to": _iso(new_to)})
        previous_to = old.date_to
        old.date_to = new_to
        old.save(update_fields=["date_to"])
        if action == "modify":
            check_mode(job, start, who)
            new = JobHourRate.objects.create(
                employment=job, hour_type=ht, rate=row["rate"] if row["rate"] is not None else old.rate,
                guaranteed_hours=row["guaranteed_hours"] if row["guaranteed_hours"] is not None else old.guaranteed_hours,
                date_from=start, date_to=row["date_to"] if row["date_to"] is not None else previous_to, document=document,
                order_item=order_item)
            result.update({"created": new.pk, "created_to": _iso(new.date_to)})
    else:
        check_mode(job, start, who)
        if start < job.date_from:
            raise ValidationError({"detail": f"{who}, {ht.code}: tariful începe înaintea raportului de muncă ({job.date_from:%d.%m.%Y})."})
        check_overlap(job, ht, start, row["date_to"], who)
        new = JobHourRate.objects.create(employment=job, hour_type=ht, rate=row["rate"], guaranteed_hours=row["guaranteed_hours"],
                                         date_from=start, date_to=row["date_to"], document=document, order_item=order_item)
        result.update({"created": new.pk, "created_to": _iso(new.date_to)})
    return result


def undo(results, who: str):
    for res in reversed(list(results or [])):
        if res.get("created"):
            new = JobHourRate.objects.filter(pk=res["created"]).first()
            if new is not None:
                if _iso(new.date_to) != res.get("created_to"):
                    raise ValidationError({"detail": f"{who}: tariful {res.get('hour_type')} a fost schimbat după aceea (oprit / "
                                                     f"modificat la {new.date_to:%d.%m.%Y}); anulați întâi documentul care l-a schimbat."})
                new.delete()
        if res.get("closed"):
            old = JobHourRate.objects.filter(pk=res["closed"]).first()
            if old is not None:
                if _iso(old.date_to) != res.get("closed_to"):
                    raise ValidationError({"detail": f"{who}: tariful {res.get('hour_type')} a fost schimbat după aceea; anulați "
                                                     f"întâi documentul care l-a schimbat."})
                old.date_to = date.fromisoformat(res["closed_before"]) if res.get("closed_before") else None
                old.save(update_fields=["date_to"])


def check_mode_change(job, day, new_mode, who="Raportul de muncă"):
    """Modalitatea fără tarife (salariu lunar, tarif orar) cere ca tarifele pe ore să fie oprite până la data schimbării."""
    if new_mode in RATE_MODES:
        return
    left = JobHourRate.objects.filter(employment=job).exclude(date_to__lt=day).select_related("hour_type")
    if left.exists():
        codes = ", ".join(sorted({r.hour_type.code for r in left}))
        raise ValidationError({"detail": f"{who}: are tarife pe tipuri de ore în vigoare după {day:%d.%m.%Y} ({codes}); opriți-le "
                                         f"(în același ordin, tabelul „Tarife pe tipuri de ore”) sau alegeți modalitatea „Mixt”."})


def occupation_defaults(occupation) -> list:
    """Tarifele-tip ale funcției ca rânduri „adaugă” ale tabelului din ordin (doar tipurile active)."""
    if occupation is None:
        return []
    return [{"hour_type": x.hour_type_id, "action": "add", "rate": _str(x.rate), "guaranteed_hours": _str(x.guaranteed_hours),
             "date_from": None, "date_to": None, "document": ""}
            for x in OccupationHourRate.objects.filter(occupation=occupation, hour_type__is_active=True,
                                                       hour_type__deletion_mark=False)]


def _str(value):
    return None if value is None else format(value.normalize() if value == value.to_integral_value() else value, "f")
