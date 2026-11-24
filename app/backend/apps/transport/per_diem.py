"""Diurna șoferilor pe zile (Regulamentul aprobat prin HG nr. 10/2012, cu modificările HG 1058/2023 și HG 783/2024).

Cursa internațională: timpul peste hotare din segmentele cursei (intrarea / ieșirea — ora trecerii frontierei, pct. 7). Segmentele
lipite (ieșirea dintr-o țară = intrarea în următoarea) fac o **aflare neîntreruptă peste hotare**; o întoarcere în Moldova o
întrerupe. Pentru fiecare aflare (pct. 31, normele categoriei I):
- până la 8 ore — C.per_diem_short_pct (20 %) din norma țării, o dată;
- peste 8 ore, cel mult 24 — C.per_diem_day_pct (40 %) din normă, o dată;
- peste 24 de ore — „modul general”: fiecare zi calendaristică a aflării (și ziua plecării, și cea a sosirii — pct. 24) cu 100 %
  din norma țării zilei.
Țara zilei: cea în care se ajunge în ziua respectivă — la trecerea dintr-o țară în alta, norma țării de destinație (pct. 26); o țară
de tranzit (fără încărcare / descărcare) unde șoferul stă mai puțin de 24 de ore ia norma țării de destinație a cursei (pct. 23),
iar încărcarea într-o țară și descărcarea în alta — tot norma țării de destinație (pct. 31). Ziua cu masa asigurată de beneficiar
(peste 8 ore peste hotare) — C.per_diem_meals_pct (20 %) din normă (pct. 33).

Procentul întreprinderii: C.per_diem_pct (sau cel scris pe cursă) se aplică peste regula de mai sus; firmele private pot plăti cel
puțin C.per_diem_private_min_pct (70 %) din normă (pct. 22¹) — sub el cursa nu se aprobă. Peste 100 % — partea în plus e venit
impozabil (DIURNAEX).

Suma în lei: cursul oficial BNM din ziua dinaintea plecării (pct. 41, fără avans) — fixat la aprobare.

Cursa în țară: munca șoferului pe drum nu e deplasare (pct. 3); diurna în țară (norma „Republica Moldova”, 250 lei) se plătește doar
cu C.per_diem_domestic_pay = 1, pentru cursele de mai multe zile (pct. 24: o singură zi — fără diurnă).
"""
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Country, PerDiemNorm, Trip

ZERO, HUNDRED = Decimal("0"), Decimal("100")


def _fmt(value, places=2):
    from .services import fmt

    return fmt(value, places)


def _q(value) -> Decimal:
    from .services import q

    return q(value)


def norm_on(country: Country, day):
    n = PerDiemNorm.objects.filter(country=country, date_from__lte=day).order_by("-date_from").first()
    if n is None:
        raise ValidationError({"detail": f"Țara {country.code} — {country.name_ro} n-are norma diurnei la {day:%d.%m.%Y} "
                                         f"(Setări → Țările și diurnele)."})
    return n


def fx_on(currency: str, day) -> Decimal:
    from apps.core import bnm

    if currency == "MDL":
        return Decimal("1")
    rate = bnm.rate_on(currency, day)
    if rate is None:
        raise ValidationError({"detail": f"Lipsește cursul BNM pentru {currency} la {day:%d.%m.%Y} (Setări → Valutele → cursul BNM)."})
    return Decimal(rate)


def _stays(legs: list) -> list:
    """Aflările neîntrerupte peste hotare: segmentele lipite (ieșirea = intrarea următorului) puse împreună."""
    stays = []
    for leg in legs:
        if stays and leg.entered <= stays[-1][-1].left:
            stays[-1].append(leg)
        else:
            stays.append([leg])
    return stays


def _day_bounds(day):
    start = timezone.make_aware(datetime.combine(day, time.min))
    return start, start + timedelta(days=1)


def _destination(stay: list, idx: int):
    """Țara de destinație pentru segmentul de tranzit `idx`: următoarea țară cu încărcare / descărcare, altfel ultima de dinainte,
    altfel segmentul însuși."""
    after = [leg for leg in stay[idx + 1:] if leg.loading or leg.unloading]
    if after:
        return after[0]
    before = [leg for leg in stay[:idx] if leg.loading or leg.unloading]
    return before[-1] if before else stay[idx]


def calculate(trip: Trip) -> list:
    """Rândurile diurnei (fără salvare): [{employment, day, country, hours, pct, norm, currency, fx_rate, amount, taxable, how}]
    pentru șofer și al doilea șofer. Ridică ValidationError dacă lipsește o normă sau un curs."""
    from apps.payroll.engine import Constants

    if trip.arrival <= trip.departure:
        return []
    start_day = timezone.localtime(trip.departure).date()
    c = Constants(start_day)
    company_pct = trip.per_diem_pct if trip.per_diem_pct is not None else c("per_diem_pct", "100")
    min_pct = c("per_diem_private_min_pct", "70")
    if company_pct < min_pct:
        raise ValidationError({"detail": f"Diurna de {_fmt(company_pct)} % e sub minimul de {_fmt(min_pct)} % din normă "
                                         f"(HG 10/2012 pct. 22¹)."})
    fx_day = start_day - timedelta(days=1)  # pct. 41: cursul din ziua dinaintea delegării
    days = []  # (ziua, țara, ore, % din normă după regulă, explicația)
    legs = list(trip.legs.select_related("country").order_by("entered", "id"))
    if trip.scope == "domestic":
        if c("per_diem_domestic_pay", "0") != 1:
            return []
        md = Country.objects.filter(code="MD").first()
        last_day = timezone.localtime(trip.arrival).date()
        if md is None or last_day == start_day:  # o singură zi în țară — fără diurnă (pct. 24)
            return []
        d = start_day
        while d <= last_day:
            days.append((d, md, Decimal("24"), HUNDRED, "cursă în țară de mai multe zile, 100 % (pct. 24)"))
            d += timedelta(days=1)
    else:
        short_pct, day_pct = c("per_diem_short_pct", "20"), c("per_diem_day_pct", "40")
        meals_pct = c("per_diem_meals_pct", "20")
        stays = _stays(legs)
        longest = max(((st[-1].left - st[0].entered).total_seconds() / 3600 for st in stays), default=0)
        if stays and longest <= 24:
            # aflări scurte (pct. 31 lit. a, b): o sumă pe aflare, după orele ei
            for stay in stays:
                begin, end = stay[0].entered, stay[-1].left
                hours = Decimal(str((end - begin).total_seconds())) / 3600
                meals = trip.meals_provided or any(leg.meals for leg in stay)
                # țara aflării: cea cu încărcare / descărcare, altfel cea în care a stat mai mult
                dest = (next((leg for leg in stay if leg.loading or leg.unloading), None)
                        or max(stay, key=lambda x: x.left - x.entered))
                band = short_pct if hours <= 8 else day_pct
                rule = "până la 8 ore peste hotare (pct. 31 lit. a)" if hours <= 8 else "8–24 de ore peste hotare (pct. 31 lit. b)"
                if meals and hours > 8 and meals_pct < band:
                    band, rule = meals_pct, rule + ", masa asigurată (pct. 33)"
                days.append((timezone.localtime(begin).date(), dest.country, hours, band, rule))
        elif stays:
            # peste 24 de ore (pct. 31 lit. c): „modul general” — fiecare zi a deplasării, de la ziua plecării până la ziua
            # sosirii (pct. 24), 100 % din norma țării zilei
            flat = [leg for st in stays for leg in st]
            d, last = start_day, timezone.localtime(trip.arrival).date()
            while d <= last:
                lo, hi = _day_bounds(d)
                present = [leg for leg in flat if leg.entered < hi and leg.left > lo]
                if present:
                    leg = present[-1]  # unde ajunge în ziua aceasta: la trecerea frontierei — țara de destinație (pct. 26)
                    why = "100 % (pct. 31 lit. c, pct. 26)"
                elif lo < flat[0].entered:
                    leg, why = flat[0], "ziua plecării, 100 % (pct. 24)"
                elif hi > flat[-1].left:
                    leg, why = flat[-1], "ziua sosirii, 100 % (pct. 24)"
                else:  # zi întreagă în Moldova la mijlocul cursei — nu e deplasare peste hotare
                    d += timedelta(days=1)
                    continue
                stay = next(st for st in stays if leg in st)
                idx = stay.index(leg)
                passage = (leg.left - leg.entered).total_seconds() / 3600  # trecerea prin țara aceasta
                if not (leg.loading or leg.unloading) and passage < 24:
                    target = _destination(stay, idx)
                    if target is not leg:
                        why += f"; tranzit prin {leg.country.code} sub 24 de ore — norma țării de destinație (pct. 23)"
                        leg = target
                hours_day = sum(((min(x.left, hi) - max(x.entered, lo)).total_seconds() for x in present), 0) / 3600
                pct = HUNDRED
                day_meals = trip.meals_provided or any(x.meals for x in present)
                if day_meals and hours_day > 8:
                    pct, why = meals_pct, why + "; masa asigurată — " + _fmt(meals_pct) + " % (pct. 33)"
                days.append((d, leg.country, Decimal(str(round(hours_day, 2))), pct, why))
                d += timedelta(days=1)
    rows = []
    people = [j for j in (trip.driver, trip.co_driver) if j is not None]
    for day, country, hours, legal_pct, why in days:
        norm = norm_on(country, day)
        fx = fx_on(norm.currency, fx_day)
        legal = _q(norm.amount * legal_pct / HUNDRED * fx)  # suma în limita normei (neimpozabilă)
        paid = _q(norm.amount * legal_pct / HUNDRED * company_pct / HUNDRED * fx)
        taxable = max(paid - legal, ZERO)
        how = (f"{country.code}: {_fmt(norm.amount)} {norm.currency} × {_fmt(legal_pct)} %"
               + (f" × {_fmt(company_pct)} % (întreprinderea)" if company_pct != HUNDRED else "")
               + (f" × {_fmt(fx, 4)} (BNM {fx_day:%d.%m.%Y})" if norm.currency != "MDL" else "")
               + f" = {_fmt(paid)} lei; {why}")
        for job in people:
            rows.append({"employment": job, "day": day, "country": country if country.code != "MD" else None, "hours": _q(hours),
                         "pct": _q(legal_pct * company_pct / HUNDRED), "norm": norm.amount, "currency": norm.currency, "fx_rate": fx,
                         "amount": paid, "taxable": taxable, "how": how[:300]})
    return rows
