"""Dreptul la concediul de odihnă anual și soldul, pe anii de muncă (de la data angajării).

Anul de muncă începe la data angajării; perioadele care nu dau dreptul la concediu (implicit concediile pentru
îngrijirea copilului) îl prelungesc cu numărul lor de zile. Dreptul pe an = zilele de bază ale funcției + cele
suplimentare pentru condiții (funcția sau subdiviziunea, se ia cel mai mare număr — HG 1223/2004) + drepturile
personale (`LeaveRight`). Anul în curs se acumulează proporțional; anul încheiat prin eliberare — la fel.

Folositul vine din absențele de tip „anual” și „suplimentar”: cu anul de muncă scris în ordin — pe acel an; fără el —
pe cel mai vechi an cu zile rămase (împărțit pe ani, dacă e nevoie). Corectările (`LeaveAdjustment`) se adaugă pe anul
lor. Cu „data pornirii evidenței” din setări, anii încheiați înainte nu se mai calculează: soldul lor vine din
corectările „sold inițial”.
"""
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.utils import timezone

from apps.core.models import SystemSetting
from apps.staff.models import CIVIL_KINDS

KEY = "leave_settings"
DEFAULTS = {"start_date": None, "not_counted": ["childcare", "childcare_unpaid"]}
USED_KINDS = {"annual", "extra"}
MAIN_KINDS = ("main", "main_student", "resident")
ZERO = Decimal("0")
CENT = Decimal("0.01")


def get_settings() -> dict:
    return {**DEFAULTS, **(SystemSetting.read(KEY, {}) or {})}


def save_settings(data: dict) -> dict:
    cfg = get_settings()
    if "start_date" in data:
        raw = data.get("start_date")
        cfg["start_date"] = date.fromisoformat(str(raw)[:10]).isoformat() if raw else None
    if "not_counted" in data:
        from .models import ABSENCE_KINDS

        known = {k for k, _ in ABSENCE_KINDS}
        cfg["not_counted"] = [k for k in (data.get("not_counted") or []) if k in known]
    SystemSetting.write(KEY, cfg)
    return cfg


def add_year(day: date) -> date:
    try:
        return day.replace(year=day.year + 1)
    except ValueError:  # 29 februarie
        return day.replace(year=day.year + 1, day=28)


def overlap(a_from, a_to, b_from, b_to) -> int:
    start, end = max(a_from, b_from), min(a_to, b_to)
    return (end - start).days + 1 if end >= start else 0


def _num(value) -> float:
    return float(Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP))


class Calculator:
    """Calculul pentru unul sau mai mulți angajați (funcțiile și subdiviziunile se citesc o singură dată)."""

    def __init__(self, on_date=None):
        from apps.org.models import Occupation, Subdivision

        self.on_date = on_date or timezone.localdate()
        cfg = get_settings()
        self.start_date = date.fromisoformat(cfg["start_date"]) if cfg.get("start_date") else None
        self.not_counted = set(cfg.get("not_counted") or [])
        self.occupations = {o.pk: o for o in Occupation.objects.all()}
        self.subdivisions = {s.pk: s for s in Subdivision.objects.all()}

    # --- raportul de muncă care dă vechimea pentru concediu ----------------------------------
    @staticmethod
    def job_of(employee):
        jobs = sorted((j for j in employee.employments.all() if j.kind not in CIVIL_KINDS), key=lambda j: (j.date_from, j.pk))
        main = [j for j in jobs if j.kind in MAIN_KINDS]
        pool = main or jobs
        return pool[-1] if pool else None

    @staticmethod
    def values_on(job, day):
        recs = [h for h in job.history.all() if h.date <= day]
        if not recs:
            return job.occupation_id, job.subdivision_id
        rec = max(recs, key=lambda h: (h.date, h.pk))
        return rec.occupation_id, rec.subdivision_id

    # --- anii de muncă ---------------------------------------------------------------------
    def work_years(self, start: date, limit: date, excluded: list) -> list:
        years, current = [], start
        while current <= limit and len(years) < 80:
            end = add_year(current) - timedelta(days=1)
            for _ in range(60):  # prelungirea cu zilele care nu dau dreptul (poate atinge alte perioade)
                skipped = sum(overlap(current, end, a, b) for a, b in excluded)
                new_end = add_year(current) - timedelta(days=1) + timedelta(days=skipped)
                if new_end == end:
                    break
                end = new_end
            skipped = sum(overlap(current, end, a, b) for a, b in excluded)
            years.append({"from": current, "to": end, "skipped": skipped})
            current = end + timedelta(days=1)
        return years

    def entitlement(self, employee, job, y_from, y_to) -> dict:
        occ_id, sub_id = self.values_on(job, min(y_to, self.on_date))
        occ, sub = self.occupations.get(occ_id), self.subdivisions.get(sub_id)
        base = occ.base_leave_days if occ else 28
        extra = max(occ.extra_leave_days if occ else 0, sub.extra_leave_days if sub else 0)
        personal = sum(r.days for r in employee.leave_rights.all()
                       if (r.date_from is None or r.date_from <= y_to) and (r.date_to is None or r.date_to >= y_from))
        return {"base": base, "extra": extra, "personal": personal, "entitled": base + extra + personal}

    # --- soldul ------------------------------------------------------------------------------
    def balance(self, employee) -> dict:
        job = self.job_of(employee)
        out = {"employee": employee.pk, "on_date": self.on_date, "start": None, "years": [], "opening": 0.0,
               "remaining": 0.0, "available": 0.0, "current": None}
        if job is None or job.date_from > self.on_date:
            return out
        limit = min(job.end_date, self.on_date) if job.end_date else self.on_date
        absences = list(employee.absences.all())
        excluded = sorted((a.date_from, a.date_to) for a in absences
                          if a.kind in self.not_counted and a.date_from >= job.date_from)
        rows = []
        for y in self.work_years(job.date_from, limit, excluded):
            if self.start_date and y["to"] < self.start_date:
                continue  # an încheiat înainte de pornirea evidenței: soldul lui vine din „sold inițial”
            ent = self.entitlement(employee, job, y["from"], y["to"])
            nominal = (y["to"] - y["from"]).days + 1 - y["skipped"]
            cut = min(limit, y["to"])
            worked = (cut - y["from"]).days + 1 - sum(overlap(y["from"], cut, a, b) for a, b in excluded)
            full = cut >= y["to"]
            accrued = Decimal(ent["entitled"]) if full else (Decimal(ent["entitled"]) * max(worked, 0) / max(nominal, 1))
            rows.append({**y, **ent, "accrued": accrued, "used": ZERO, "adjusted": ZERO, "absences": [],
                         "closed": full, "ended": bool(job.end_date and job.end_date < y["to"])})

        def year_for(day):
            return next((r for r in rows if r["from"] <= day <= r["to"]), None)

        opening = ZERO
        for adj in employee.leave_adjustments.all():
            row = year_for(adj.work_year_from or adj.date)
            if row is None:
                opening += adj.days
            else:
                row["adjusted"] += adj.days
        used = sorted((a for a in absences if a.kind in USED_KINDS and a.date_from >= job.date_from),
                      key=lambda a: (a.date_from, a.pk))
        floating = []
        for a in used:
            row = year_for(a.work_year_from) if a.work_year_from else None
            if a.work_year_from and row is None:
                continue  # pe un an dinaintea pornirii evidenței: e cuprins în soldul inițial
            if row is None:
                floating.append(a)
            else:
                row["used"] += a.days
                row["absences"].append(a.pk)
        for a in floating:  # fără anul de muncă: pe cel mai vechi an cu zile rămase
            left = Decimal(a.days)
            for row in rows:
                if left <= 0 or row["from"] > a.date_from:
                    break
                free = Decimal(row["entitled"]) + row["adjusted"] - row["used"]
                if free <= 0:
                    continue
                take = min(free, left)
                row["used"] += take
                row["absences"].append(a.pk)
                left -= take
            if left > 0:
                row = year_for(a.date_from) or (rows[-1] if rows else None)
                if row is not None:
                    row["used"] += left
                    row["absences"].append(a.pk)
        total = opening
        available = opening
        for row in rows:
            row["remaining"] = row["accrued"] + row["adjusted"] - row["used"]
            row["available"] = Decimal(row["entitled"]) + row["adjusted"] - row["used"]
            total += row["remaining"]
            available += row["available"] if not row["ended"] else row["remaining"]
        current = next((r for r in rows if r["from"] <= self.on_date <= r["to"]), rows[-1] if rows else None)
        out.update({
            "start": job.date_from, "opening": _num(opening), "remaining": _num(total), "available": _num(available),
            "years": [{"from": r["from"], "to": r["to"], "base": r["base"], "extra": r["extra"], "personal": r["personal"],
                       "entitled": r["entitled"], "accrued": _num(r["accrued"]), "used": _num(r["used"]),
                       "adjusted": _num(r["adjusted"]), "remaining": _num(r["remaining"]), "available": _num(r["available"]),
                       "skipped": r["skipped"], "closed": r["closed"], "absences": r["absences"]} for r in rows],
            "current": ({"from": current["from"], "to": current["to"], "entitled": current["entitled"]} if current else None),
        })
        return out

    def suggest_work_year(self, employee):
        """Anul de muncă pentru un concediu nou: cel mai vechi cu zile rămase, altfel anul în curs."""
        data = self.balance(employee)
        for y in data["years"]:
            if y["available"] > 0:
                return y["from"], y["to"]
        cur = data["current"]
        return (cur["from"], cur["to"]) if cur else (None, None)

    def entitled_in(self, employee, day: date) -> int:
        """Zilele cuvenite pe anul de muncă în care cade data (pentru graficul anual)."""
        job = self.job_of(employee)
        if job is None:
            return 0
        start = job.date_from
        while add_year(start) <= day:
            start = add_year(start)
        return self.entitlement(employee, job, start, add_year(start) - timedelta(days=1))["entitled"]


def prefetch(qs):
    return qs.prefetch_related("employments__history", "absences", "leave_rights", "leave_adjustments")


def balance(employee, on_date=None) -> dict:
    return Calculator(on_date).balance(employee)
