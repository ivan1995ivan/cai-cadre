"""Orele pe tipuri (instruire, examinare, zbor…) în pontaj și plata lor după tariful raportului de muncă, cu orele garantate.

Datele:
- orele se scriu pe linia pontajului (`TimesheetLine.typed_hours`): pe zile (dacă tipul permite) sau ca total pe lună; un
  raport de muncă cu două linii în lună (transfer) are orele adunate;
- tariful și garanția sunt pe raport (`JobHourRate`), cu perioada lor; în aceeași lună pot fi două rânduri (tariful schimbat).

Orele garantate sunt un **minim plătit**: plătite = max(efective, garantate). Garanția lunii se reduce proporțional cu zilele
lucrătoare (calendarul de producție) în care nu e „disponibil”: raportul nu există încă / a încetat, rândul tarifului nu e în
vigoare, contractul e suspendat, angajatul e într-o absență din lista setării `guarantee_absences` (implicit toate concediile și
boala; deplasarea și formarea profesională nu reduc — sunt muncă):

    garantat 50 × 18 / 22 zile disponibile = 40,91; efectiv 34 → plătit 40,91

Cu două rânduri de tarif în lună: orele scrise pe zile merg la rândul în vigoare în ziua lor; totalul pe lună se împarte între
rânduri proporțional cu zilele lor lucrătoare; garanția fiecărui rând se socotește pe zilele lui.

Legătura cu orele lucrate (`HourType.work_time`): „within” — orele sunt o parte din orele standard (nu se adună a doua oară);
„added” — se adaugă la orele lucrate ale liniei și la partea lucrată din normă; „none” — nu sunt timp de muncă.
"""
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from rest_framework.exceptions import ValidationError

ZERO, CENT = Decimal("0"), Decimal("0.01")
SETTINGS_KEY = "guarantee_absences"
# felurile de absență care reduc garanția (apps.leave.models.ABSENCE_KINDS): tot ce nu e muncă — concediile (cel de odihnă se
# plătește din medie, care cuprinde deja orele), boala, îngrijirea copilului, staționarea și șomajul tehnic (plătite după
# regula lor); fără deplasare și formare profesională
DEFAULT_REDUCING = ["annual", "extra", "unpaid", "maternity", "paternity", "childcare", "childcare_unpaid", "study", "days_off",
                    "sick", "idle", "tech_unemployment"]
NOT_REDUCING = ("travel", "training")


def q(value) -> Decimal:
    return Decimal(value or 0).quantize(CENT, rounding=ROUND_HALF_UP)


def fmt(value, money=False) -> str:
    """„40,91”, „50”, „1 234,5” — pentru explicații; `money` — sumele în lei: întregi fără zecimale, altfel cu două
    („9 166,50”)."""
    v = Decimal(value or 0).quantize(CENT, rounding=ROUND_HALF_UP)
    text = format(v.normalize(), "f") if not money or v == v.to_integral_value() else format(v, "f")
    if "E" in text:
        text = format(v.to_integral_value(), "f")
    whole, _, frac = text.partition(".")
    sign = "−" if whole.startswith("-") else ""
    whole = whole.lstrip("-")
    groups = []
    while len(whole) > 3:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    groups.insert(0, whole)
    return sign + " ".join(groups) + ("," + frac if frac else "")


def settings() -> dict:
    """{"kinds": [felurile de absență care reduc garanția], "suspension": bool} — din setările timpului de muncă."""
    from .services import get_settings

    raw = get_settings().get(SETTINGS_KEY)
    if not isinstance(raw, dict):
        raw = {}
    kinds = raw.get("kinds")
    if not isinstance(kinds, list):
        kinds = list(DEFAULT_REDUCING)
    return {"kinds": [k for k in kinds if k not in NOT_REDUCING], "suspension": raw.get("suspension", True) is not False}


def check_settings(value) -> dict:
    from apps.leave.models import ABSENCE_KINDS

    if not isinstance(value, dict):
        raise ValidationError({SETTINGS_KEY: "Setarea are felurile de absență („kinds”) și suspendarea („suspension”)."})
    known = {k for k, _ in ABSENCE_KINDS}
    kinds = value.get("kinds") or []
    if not isinstance(kinds, list) or any(k not in known for k in kinds):
        raise ValidationError({SETTINGS_KEY: "Felurile de absență nu există."})
    bad = [k for k in kinds if k in NOT_REDUCING]
    if bad:
        raise ValidationError({SETTINGS_KEY: "Deplasarea și formarea profesională sunt muncă: nu reduc orele garantate."})
    return {"kinds": kinds, "suspension": bool(value.get("suspension", True))}


# --- orele scrise -------------------------------------------------------------------------------------------------------
def entry_hours(entry) -> Decimal:
    """Orele efective ale unui tip pe linie: totalul pe lună, dacă e scris, altfel suma zilelor."""
    if not isinstance(entry, dict):
        return ZERO
    if entry.get("month") not in (None, ""):
        return Decimal(str(entry["month"]))
    return sum((Decimal(str(v)) for v in (entry.get("days") or {}).values()), ZERO)


def merge(typed_list) -> dict:
    """Orele pe tipuri ale mai multor linii (același raport, două tabele în lună) → una: zilele se adună, totalurile la fel."""
    out = {}
    for typed in typed_list:
        for code, entry in (typed or {}).items():
            if not isinstance(entry, dict):
                continue
            cur = out.setdefault(code, {"days": {}, "month": None})
            if entry.get("month") not in (None, ""):
                cur["month"] = float(Decimal(str(cur["month"] or 0)) + entry_hours(entry))
            else:
                for d, h in (entry.get("days") or {}).items():
                    cur["days"][str(d)] = float(Decimal(str(cur["days"].get(str(d), 0))) + Decimal(str(h)))
    for cur in out.values():  # un total pe lună într-una din linii: zilele celeilalte intră în el
        if cur["month"] is not None and cur["days"]:
            cur["month"] = float(Decimal(str(cur["month"])) + sum((Decimal(str(v)) for v in cur["days"].values()), ZERO))
            cur["days"] = {}
    return out


def set_hours(line, hour_type, *, days=None, month=None):
    """Orele unui tip pe linia pontajului: `days` = {zi: ore} (înlocuiește zilele) sau `month` = totalul pe lună; amândouă
    goale — tipul se scoate de pe linie."""
    from .services import month_days

    ts = line.timesheet
    if ts.status == "closed":
        raise ValidationError({"detail": "Tabela este închisă."})
    n_days = len(month_days(ts.year, ts.month))
    typed = dict(line.typed_hours or {})
    clean_days = {}
    for key, value in (days or {}).items():
        if value in (None, ""):
            continue
        try:
            d, h = int(key), Decimal(str(value).replace(",", "."))
        except (ValueError, ArithmeticError):
            raise ValidationError({"days": f"Ziua „{key}”: „{value}” nu este un număr de ore."}) from None
        if not 1 <= d <= n_days:
            raise ValidationError({"days": f"Ziua {d} nu este în lună."})
        if h < 0 or h > 24:
            raise ValidationError({"days": f"Ziua {d}: orele sunt între 0 și 24."})
        if h:
            clean_days[str(d)] = float(h)
    total = None
    if month not in (None, ""):
        try:
            total = Decimal(str(month).replace(",", "."))
        except ArithmeticError:
            raise ValidationError({"month": "Totalul pe lună nu este un număr."}) from None
        if total < 0 or total > 744:
            raise ValidationError({"month": "Totalul pe lună este între 0 și 744 de ore."})
    if clean_days and total is not None:
        raise ValidationError({"detail": "Orele se scriu pe zile sau ca total pe lună, nu amândouă."})
    if clean_days and hour_type.entry == "month":
        raise ValidationError({"days": f"Tipul {hour_type.code} se scrie doar ca total pe lună."})
    if not clean_days and total is None:
        typed.pop(hour_type.code, None)
    else:
        typed[hour_type.code] = {"days": dict(sorted(clean_days.items(), key=lambda kv: int(kv[0]))),
                                 "month": float(total) if total is not None else None}
    line.typed_hours = typed
    line.save(update_fields=["typed_hours"])
    return line


# --- garanția și plata ------------------------------------------------------------------------------------------------
class Availability:
    """Zilele lucrătoare ale lunii (calendarul de producție) și motivele pentru care raportul nu e „disponibil” într-o zi."""

    def __init__(self, ctx, jd, conf=None):
        conf = conf or settings()
        self.ctx, self.jd = ctx, jd
        self.working = [d for d in ctx.days if ctx.cal.is_working(d)]
        self.kinds, self.suspension = set(conf["kinds"]), conf["suspension"]

    def reason(self, day) -> str | None:
        """None — disponibil; altfel motivul: „inactive”, „suspended” sau codul absenței din pontaj."""
        from .services import ABSENCE_CODES

        if not self.jd.active(day):
            return "inactive"
        for a in self.jd.absences:
            if a.date_from <= day <= a.date_to and a.kind in self.kinds:
                if a.employment_id and a.employment_id != self.jd.job.pk:
                    continue
                return ABSENCE_CODES.get(a.kind, a.kind)
        if self.suspension and self.jd.is_suspended(day):
            return "Sp"
        return None


def _reasons_text(counts: dict) -> str:
    parts = []
    for key, n in counts.items():
        if key == "inactive":
            parts.append(f"{n} zile fără raport / fără tarif")
        elif key == "Sp":
            parts.append(f"{n} zile suspendat")
        else:
            parts.append(f"{n} zile {key}")
    return f" ({', '.join(parts)})" if parts else ""


def summarize(ctx, jd, typed: dict, rates: list, hour_types: dict, conf=None) -> dict:
    """Orele pe tipuri ale raportului în lună: {cod: rezumat}. Rezumatul: orele efective, rândurile de tarif (garantat,
    disponibil, plătit, suma), totalurile și explicația. `rates` — rândurile `JobHourRate` ale raportului (oricare);
    `hour_types` — {cod: HourType}."""
    av = Availability(ctx, jd, conf)
    first, last = ctx.days[0], ctx.days[-1]
    total_days = len(av.working)
    reasons = {d: av.reason(d) for d in av.working}
    by_code = defaultdict(list)
    for r in rates:
        if r.in_force(first, last):
            by_code[r.hour_type.code].append(r)
    out = {}
    for code in sorted(set(typed) | set(by_code), key=lambda c: (getattr(hour_types.get(c), "sort", 0), c)):
        ht = hour_types.get(code)
        entry = typed.get(code) or {}
        hours = entry_hours(entry)
        rows = sorted(by_code.get(code, []), key=lambda r: (r.date_from, r.pk or 0))
        per_day = {int(k): Decimal(str(v)) for k, v in (entry.get("days") or {}).items()} if entry.get("month") in (None, "") else {}
        res = {"code": code, "name": ht.name_ro if ht else code, "work_time": ht.work_time if ht else "within",
               "hours": float(q(hours)), "by_day": bool(per_day), "rows": [], "paid": float(q(hours)), "amount": 0.0,
               "guaranteed": None, "guaranteed_full": None, "available_days": None, "total_days": total_days, "rate": None,
               "unrated_hours": 0.0, "note": "", "pay_type": ht.pay_type_id if ht else None}
        if not rows:
            res["note"] = f"efectiv {fmt(hours)} ore" + ("" if ht is None or not hours else "; fără tarif pe raport")
            out[code] = res
            continue
        row_days = []
        for r in rows:
            mine = [d for d in av.working if r.date_from <= d and (r.date_to is None or d <= r.date_to)]
            row_days.append(mine)
        # orele pe rânduri
        alloc = [ZERO] * len(rows)
        unrated = ZERO
        if per_day:
            for day_no, h in per_day.items():
                day = ctx.days[day_no - 1] if 1 <= day_no <= len(ctx.days) else None
                idx = next((i for i, r in enumerate(rows) if day and r.date_from <= day and (r.date_to is None or day <= r.date_to)), None)
                if idx is None:
                    unrated += h
                else:
                    alloc[idx] += h
        else:
            weights = [sum(1 for d in mine if reasons[d] != "inactive") for mine in row_days]
            if sum(weights) == 0 or len(rows) == 1:
                alloc[-1] = hours
            else:
                left = hours
                for i, w in enumerate(weights):
                    part = q(hours * w / sum(weights)) if i < len(rows) - 1 else left
                    alloc[i], left = part, left - part
        paid_total = amount_total = ZERO
        notes, g_total, g_full, avail_total = [], ZERO, ZERO, 0
        has_guarantee = False
        for r, mine, h in zip(rows, row_days, alloc):
            row = {"id": r.pk, "rate": float(r.rate), "from": r.date_from.isoformat(),
                   "to": r.date_to.isoformat() if r.date_to else None, "hours": float(q(h)), "guaranteed_full": None,
                   "guaranteed": None, "available_days": None, "paid": float(q(h))}
            paid = h
            text = f"efectiv {fmt(h)}"
            if r.guaranteed_hours is not None:
                has_guarantee = True
                counts = defaultdict(int)
                for d in av.working:
                    if d not in mine:
                        counts["inactive"] += 1
                    elif reasons[d]:
                        counts[reasons[d]] += 1
                avail = total_days - sum(counts.values())
                reduced = q(r.guaranteed_hours * avail / total_days) if total_days else ZERO
                paid = max(h, reduced)
                g_total += reduced
                g_full += r.guaranteed_hours
                avail_total += avail
                row.update({"guaranteed_full": float(r.guaranteed_hours), "guaranteed": float(reduced), "available_days": avail})
                if avail == total_days:
                    text = f"garantat {fmt(r.guaranteed_hours)}; efectiv {fmt(h)} → plătit {fmt(paid)}"
                else:
                    text = (f"garantat {fmt(r.guaranteed_hours)} × {avail} / {total_days} zile disponibile"
                            f"{_reasons_text(counts)} = {fmt(reduced)}; efectiv {fmt(h)} → plătit {fmt(paid)}")
            amount = q(paid * r.rate)
            row.update({"paid": float(q(paid)), "amount": float(amount)})
            text += f" × {fmt(r.rate, True)} lei = {fmt(amount, True)} lei"
            if len(rows) > 1:
                text = f"{max(r.date_from, first):%d.%m}–{min(r.date_to or last, last):%d.%m}: {text}"
            paid_total += paid
            amount_total += amount
            notes.append(text)
            res["rows"].append(row)
        if unrated:
            notes.append(f"{fmt(unrated)} ore în zile fără tarif în vigoare (neplătite)")
        res.update({"paid": float(q(paid_total + unrated)), "amount": float(q(amount_total)), "rate": float(rows[-1].rate),
                    "unrated_hours": float(q(unrated)), "note": "; ".join(notes)})
        if has_guarantee:
            res.update({"guaranteed": float(q(g_total)), "guaranteed_full": float(g_full), "available_days": avail_total
                        if len(rows) == 1 else None})
        out[code] = res
    return out


def warnings(summary: dict, totals: dict) -> list:
    """Orele „în cadrul orelor lucrate” mai multe decât orele lucrate ale liniei."""
    within = sum((Decimal(str(s["hours"])) for s in summary.values() if s["work_time"] == "within"), ZERO)
    worked = Decimal(str((totals or {}).get("hours") or 0))
    if within > worked:
        return [f"Orele pe tipuri care fac parte din program ({fmt(within)}) sunt mai multe decât orele lucrate ({fmt(worked)})."]
    return []


def added_hours(summary: dict) -> Decimal:
    """Orele care se adaugă la orele lucrate (tipurile „se adaugă la orele lucrate”)."""
    return sum((Decimal(str(s["hours"])) for s in summary.values() if s["work_time"] == "added"), ZERO)


def job_summary(ctx, jd, typed: dict, conf=None) -> dict:
    """Rezumatul unui raport (cu rândurile de tarif și tipurile din bază)."""
    from .models import HourType, JobHourRate

    rates = list(JobHourRate.objects.filter(employment=jd.job).select_related("hour_type"))
    types = {t.code: t for t in HourType.objects.all()}
    return summarize(ctx, jd, typed, rates, types, conf)
