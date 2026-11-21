"""Datele demo pe un an întreg, peste baza făcută de `crm_demo`: evidența lunară completă din noiembrie anul trecut până în
luna curentă — graficele de gărzi, tabelele de pontaj (închise), avansul și salariul (calculate, aprobate, achitate),
ordinele anului (concedii din graficul anual, delegări, perfecționare, premii trimestriale, ajutor material, sporuri,
majorări de salariu, categorii, angajări, o eliberare), foile de boală, cererile de scutire, cotizațiile și reținerile
personale, graficul concediilor, planul de formare și atestările. Totul trece prin serviciile modulelor, ca în lucru.

Se rulează o singură dată, după `crm_demo`:  manage.py crm_demo_year
"""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .demo import MEN, SURNAMES, WOMEN, DemoError, _idnp, kind_of

ONE = Decimal("1")
SHIFT_SUBDIVISIONS = ("TR1", "TR2", "ATI", "BLO")  # secțiile cu ture de 12 ore și gărzi (graficul lunar)
LEAVE_WEIGHTS = [3, 3, 4, 5, 6, 9, 10, 9, 6, 4, 3, 3]  # în ce luni pleacă oamenii în concediu (vara cel mai mult)
BANKS = ["BC „Moldova-Agroindbank” S.A.", "BC „Victoriabank” S.A.", "BC „Moldindconbank” S.A."]
TRAVEL = [("Chișinău, Ministerul Sănătății", "participării la ședința de lucru"),
          ("Bălți, Spitalul Clinic Municipal", "consultării pacienților"),
          ("Iași, România — Spitalul „Sf. Spiridon”", "schimbului de experiență"),
          ("Cahul, Spitalul Raional", "acordării asistenței metodice")]
COURSES = [("Actualități în traumatologie și ortopedie", "USMF „Nicolae Testemițanu”", 72),
           ("Urgențe medico-chirurgicale", "USMF „Nicolae Testemițanu”", 36),
           ("Controlul infecțiilor asociate asistenței medicale", "Agenția Națională pentru Sănătate Publică", 16),
           ("Anestezia regională — curs practic", "Societatea de Anesteziologie", 36),
           ("Nursing în ortopedie", "Centrul de Educație Medicală Continuă", 72),
           ("Îngrijirea pacientului imobilizat", "Centrul de Educație Medicală Continuă", 36)]
BONUS_NOTES = {3: "pentru rezultatele activității în trimestrul I", 6: "pentru rezultatele activității în trimestrul II",
               9: "pentru rezultatele activității în trimestrul III", 12: "pentru rezultatele activității în anul curent"}


def _months(year: int, until_month: int) -> list:
    """(an, lună) de la noiembrie anul trecut până la luna curentă inclusiv."""
    out = [(year - 1, 11), (year - 1, 12)]
    out += [(year, m) for m in range(1, until_month + 1)]
    return out


def _last_day(y: int, m: int) -> date:
    return (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1))


def _weekday(day: date) -> date:
    """Prima zi lucrătoare (luni–vineri) de la data dată încolo."""
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day


class Year:
    def __init__(self, year: int, log=print):
        from apps.users.models import User

        self.year = year
        self.today = timezone.localdate()
        self.log = log
        self.rnd = random.Random(year)
        self.users = {u.username: u for u in User.objects.filter(username__in=("cadre", "director", "contabil", "sef.trauma"))}
        self.director = self.users.get("director")
        self.cadre = self.users.get("cadre")
        self.contabil = self.users.get("contabil")
        self.plan = {}  # employee_id -> (data de început, zile) a concediului anual planificat în anul curent
        self.stats = {}

    def count(self, key, n=1):
        self.stats[key] = self.stats.get(key, 0) + n

    # --- angajații --------------------------------------------------------------------------------------------
    def main_jobs(self, on: date):
        """Raporturile de bază active la data dată (angajați înainte de ea)."""
        from apps.staff.models import Employment

        return list(Employment.objects.filter(kind__in=("main", "main_student"), date_from__lt=on)
                    .exclude(status="ended").select_related("employee", "occupation", "subdivision")
                    .order_by("employee__last_name", "employee__first_name"))

    def people(self):
        """Angajații cu datele de bancă și cererile de scutire; cotizațiile și reținerile personale."""
        from apps.payroll.models import EmployeePayItem, ExemptionRequest, PayType
        from apps.staff.models import Employee, Employment, FamilyMember

        rnd = self.rnd
        types = {t.code: t for t in PayType.objects.all()}
        for i, emp in enumerate(Employee.objects.order_by("id")):
            if not emp.iban and i % 7 != 6:
                emp.iban = f"MD{rnd.randint(10, 99)}{rnd.choice(['AG', 'VI', 'ML'])}{rnd.randint(10**17, 10**18 - 1)}"
                emp.bank_name = BANKS[i % 3]
                emp.save(update_fields=["iban", "bank_name"])
            if i % 5 == 4:
                continue  # fără cerere de scutire (impozitul se reține întreg)
            dependents = [{"name": f.full_name, "idnp": f.idnp, "disabled": f.disabled}
                          for f in FamilyMember.objects.filter(employee=emp, dependent=True)]
            married = emp.marital_status is not None and getattr(emp.marital_status, "code", "") == "married"
            for y in (self.year - 1, self.year):
                if not ExemptionRequest.objects.filter(employee=emp, year=y).exists():
                    ExemptionRequest.objects.create(
                        employee=emp, year=y, date=date(y, 1, rnd.randint(8, 25)), kind="personal",
                        spouse=bool(married and i % 3 == 0), spouse_name=f"{emp.last_name} {rnd.choice(MEN + WOMEN)}" if married and i % 3 == 0 else "",
                        dependents=dependents, documents="copia buletinului" + (", certificatele de naștere" if dependents else ""),
                        date_from=date(y, 1, 1))
                    self.count("scutiri")
        start = date(self.year - 1, 1, 1)
        jobs = self.main_jobs(date(self.year - 1, 11, 1))
        if "SINDICAT" in types:
            for i, job in enumerate(jobs):
                if i % 5 in (0, 1, 2) and not EmployeePayItem.objects.filter(employee=job.employee, pay_type=types["SINDICAT"]).exists():
                    EmployeePayItem.objects.create(employee=job.employee, pay_type=types["SINDICAT"], percent=Decimal("1"),
                                                   date_from=max(start, job.date_from), document="Cererea de aderare la sindicat")
                    self.count("sindicat")
        if "PENSIE" in types and jobs:
            job = jobs[len(jobs) // 3]
            if not EmployeePayItem.objects.filter(pay_type=types["PENSIE"]).exists():
                EmployeePayItem.objects.create(employee=job.employee, pay_type=types["PENSIE"], percent=Decimal("25"),
                                               date_from=start, document=f"Titlul executoriu nr. 2-{rnd.randint(1000, 9999)}/{self.year - 1}")
        if "IMPRUMUT" in types and jobs:
            job = jobs[len(jobs) // 2]
            if not EmployeePayItem.objects.filter(pay_type=types["IMPRUMUT"]).exists():
                EmployeePayItem.objects.create(employee=job.employee, pay_type=types["IMPRUMUT"], amount=Decimal("500"),
                                               date_from=date(self.year, 2, 1), date_to=date(self.year, 7, 31),
                                               document="Contractul de împrumut nr. 1 (ajutor rambursabil)")
        if "CONTRACT" in types:
            for job in Employment.objects.filter(kind="contractor").exclude(status="ended"):
                if not EmployeePayItem.objects.filter(employment=job, pay_type=types["CONTRACT"]).exists():
                    EmployeePayItem.objects.create(employee=job.employee, employment=job, pay_type=types["CONTRACT"],
                                                   amount=Decimal("4000"), date_from=job.date_from,
                                                   document=f"Contractul de prestări servicii nr. {job.pk}/{job.date_from.year}")

    def constants(self):
        """Constantele salariului și pentru anul trecut (noiembrie–decembrie se calculează cu ele)."""
        from apps.payroll.models import PayConstant

        first = date(self.year - 1, 1, 1)
        for code in PayConstant.objects.values_list("code", flat=True).distinct():
            if not PayConstant.objects.filter(code=code, date_from__lte=first).exists():
                c = PayConstant.objects.filter(code=code).order_by("date_from").first()
                PayConstant.objects.create(code=code, name=c.name, value=c.value, unit=c.unit, date_from=first,
                                           source=f"{c.source} (valoarea {self.year - 1})".strip())

    def schedules(self):
        """Graficele de lucru: asistentele și infirmierele din secții — ture de 12 ore; medicii ATI — gărzi de 24 de ore."""
        from apps.worktime import seed as worktime_seed
        from apps.worktime.models import JobSchedule, WorkSchedule

        worktime_seed.run()
        zn = WorkSchedule.objects.filter(code="ZN").first()
        g24 = WorkSchedule.objects.filter(code="G24", deletion_mark=False).first()  # gărzile nu se mai livrează (S1)
        if zn is None:
            return
        for i, job in enumerate(self.main_jobs(self.today)):
            if job.subdivision.code not in SHIFT_SUBDIVISIONS or JobSchedule.objects.filter(employment=job).exists():
                continue
            cat = kind_of(job.occupation)
            if cat in ("nurses", "junior") and i % 3:  # o parte rămân pe program de zi
                JobSchedule.objects.create(employment=job, schedule=zn, date_from=job.date_from, cycle_offset=i % 4)
                self.count("grafice ZN")
            elif g24 and cat == "physicians" and job.subdivision.code == "ATI" and "Șef" not in job.occupation.name_ro:
                JobSchedule.objects.create(employment=job, schedule=g24, date_from=job.date_from, cycle_offset=i % 4)
                self.count("grafice G24")

    # --- concediile anului ----------------------------------------------------------------------------------------
    def leave_plan(self):
        """Fiecare angajat de bază pleacă o dată în concediu în anul curent (28 sau 14 zile), după un plan anual."""
        from apps.leave import services as leave_services

        rnd = self.rnd
        for i, job in enumerate(self.main_jobs(date(self.year, 1, 1))):
            for _attempt in range(6):
                month = rnd.choices(range(1, 13), weights=LEAVE_WEIGHTS)[0]
                days = 28 if i % 10 < 7 else 14
                start = date(self.year, month, rnd.randint(1, 12))
                _s, end, _n = leave_services.period("annual", start, days)
                if not leave_services.overlapping(job.employee, start - timedelta(days=3), end + timedelta(days=3)).exists():
                    self.plan[job.employee_id] = (start, days)
                    break

    def leave_schedules(self):
        """Graficul anual al concediilor pe fiecare subdiviziune, cu datele din plan, aprobat prin ordin."""
        from apps.leave import services as leave_services
        from apps.leave.models import LeaveSchedule
        from apps.org.models import OrderType, Subdivision
        from apps.orders import services as order_services
        from apps.orders.models import OrderItem

        order_date = date(self.year - 1, 12, 15)
        schedules = []
        for sub in Subdivision.objects.filter(parent__isnull=True).order_by("sort"):
            sch, created = LeaveSchedule.objects.get_or_create(year=self.year, subdivision=sub, defaults={"created_by": self.cadre})
            leave_services.fill_schedule(sch)
            for ln in sch.lines.all():
                planned = self.plan.get(ln.employee_id)
                if planned and not ln.date_from:
                    ln.date_from, ln.days = planned
                    ln.date_to = leave_services.line_end(ln)
                    ln.save(update_fields=["date_from", "days", "date_to"])
            if sch.status != "approved":
                sch.status = "submitted"
                sch.save(update_fields=["status"])
                schedules.append(sch)
        ot = OrderType.objects.filter(code="leave_schedule").first()
        if schedules and ot is not None:
            order = order_services.new_order(ot, user=self.cadre, date=order_date)
            order.basis = f"Graficele concediilor pe anul {self.year}, transmise de subdiviziuni"
            order.save(update_fields=["basis"])
            item = OrderItem.objects.create(order=order, params={"schedules": [s.pk for s in schedules], "year": self.year}, sort=10)
            order_services.refresh_text(item)
            item.save(update_fields=["text"])
            self._sign(order, "graficul concediilor")

    def _sign(self, order, what: str):
        from apps.orders import services as order_services

        try:
            order_services.sign(order, user=self.director)
            self.count("ordine")
            return True
        except ValidationError as exc:
            self.log(f"  ordinul ({what}) nu s-a semnat: {exc.detail}")
            order.delete()
            return False

    def _order(self, code: str, day: date, basis: str = ""):
        from apps.org.models import OrderType
        from apps.orders import services as order_services

        ot = OrderType.objects.filter(code=code, is_active=True).first()
        if ot is None:
            return None
        order = order_services.new_order(ot, user=self.cadre, date=day)
        if basis:
            order.basis = basis
            order.save(update_fields=["basis"])
        return order

    def _item(self, order, employee, params: dict, sort: int):
        from apps.orders import services as order_services
        from apps.orders.models import OrderItem

        item = OrderItem.objects.create(order=order, employee=employee, params=params, sort=sort * 10)
        order_services.refresh_text(item)
        item.save(update_fields=["text"])
        return item

    def leave_orders(self, y: int, m: int):
        """Ordinul colectiv de concediu pentru cei planificați în luna dată (datat în luna dinainte)."""
        from apps.leave import services as leave_services
        from apps.staff.models import Employee

        if y != self.year:
            return
        who = [(emp_id, start, days) for emp_id, (start, days) in self.plan.items() if start.month == m]
        if not who:
            return
        order_day = _weekday(date(y, m, 1) - timedelta(days=10))
        order = self._order("leave_annual", order_day, basis=f"Graficul concediilor pe anul {y}, cererile salariaților")
        if order is None:
            return
        n = 0
        for emp_id, start, days in sorted(who, key=lambda w: w[1]):
            emp = Employee.objects.get(pk=emp_id)
            _s, end, _n = leave_services.period("annual", start, days)
            if leave_services.overlapping(emp, start, end).exists():
                continue
            n += 1
            self._item(order, emp, {"date_from": start.isoformat(), "days": days}, n)
        if n:
            if self._sign(order, f"concedii {m:02d}.{y}"):
                self.count("concedii", n)
        else:
            order.delete()

    def sick_leaves(self, y: int, m: int):
        from apps.leave import services as leave_services
        from apps.leave.models import SickLeave

        rnd = self.rnd
        jobs = self.main_jobs(date(y, m, 1))
        for k in range(rnd.randint(2, 4)):
            job = rnd.choice(jobs)
            start = date(y, m, rnd.randint(1, 20))
            days = rnd.randint(4, 11)
            end = start + timedelta(days=days - 1)
            if leave_services.overlapping(job.employee, start, end).exists():
                continue
            sick = SickLeave(employee=job.employee, series="CM", number=f"{y}{m:02d}{rnd.randint(1000, 9999)}",
                             issued_on=start, issued_by=rnd.choice(["IMSP AMT Centru", "IMSP AMT Botanica", "IMSP SCM „Sfânta Treime”"]),
                             kind=rnd.choice(["illness", "illness", "illness", "household_injury", "child_care"]),
                             date_from=start, date_to=end, return_date=_weekday(end + timedelta(days=1)), created_by=self.cadre)
            try:
                leave_services.save_sick_leave(sick)
                self.count("foi de boală")
            except ValidationError as exc:
                self.log(f"  foaia de boală nu s-a înregistrat: {exc.detail}")

    def travel_orders(self, y: int, m: int):
        rnd = self.rnd
        doctors = [j for j in self.main_jobs(date(y, m, 1)) if kind_of(j.occupation) == "physicians"]
        if not doctors:
            return
        day = _weekday(date(y, m, rnd.randint(3, 18)))
        order = self._order("travel", day - timedelta(days=2) if day.day > 2 else day, basis="Demersul șefului de secție")
        if order is None:
            return
        for n, job in enumerate(rnd.sample(doctors, min(len(doctors), rnd.randint(1, 2))), start=1):
            where, purpose = rnd.choice(TRAVEL)
            self._item(order, job.employee, {"date_from": day.isoformat(), "date_to": (day + timedelta(days=rnd.randint(1, 2))).isoformat(),
                                             "destination": where, "purpose": purpose}, n)
        if self._sign(order, f"delegare {m:02d}.{y}"):
            self.count("delegări")

    def training_orders(self, y: int, m: int):
        from apps.leave import services as leave_services
        from apps.training.models import TrainingRecord

        rnd = self.rnd
        staff = [j for j in self.main_jobs(date(y, m, 1)) if kind_of(j.occupation) in ("physicians", "nurses")]
        if not staff:
            return
        start = _weekday(date(y, m, rnd.randint(2, 14)))
        end = start + timedelta(days=4)
        order = self._order("training", start - timedelta(days=3), basis="Planul de formare profesională continuă")
        if order is None:
            return
        n = 0
        chosen = []
        for job in rnd.sample(staff, min(len(staff), 2)):
            if leave_services.overlapping(job.employee, start, end).exists():
                continue
            n += 1
            title, provider, hours = rnd.choice(COURSES[:4] if kind_of(job.occupation) == "physicians" else COURSES[4:])
            self._item(order, job.employee, {"date_from": start.isoformat(), "date_to": end.isoformat(), "destination": provider,
                                             "purpose": f"participării la cursul „{title}”"}, n)
            chosen.append((job, title, provider, hours))
        if not n:
            order.delete()
            return
        if self._sign(order, f"perfecționare {m:02d}.{y}"):
            for item in order.items.select_related("employee"):
                job, title, provider, hours = next(c for c in chosen if c[0].employee_id == item.employee_id)
                TrainingRecord.objects.create(employee=item.employee, kind="course", title=title, provider=provider,
                                              date_from=start, date_to=end, hours=Decimal(hours),
                                              certificate_number=f"C-{y}-{self.rnd.randint(100, 999)}", certificate_date=end,
                                              order_item=item)
                self.count("formare")

    def bonus_orders(self, y: int, m: int):
        from apps.orders.models import Incentive

        rnd = self.rnd
        if m in BONUS_NOTES and not Incentive.objects.filter(date__year=y, date__month=m, kind__code="bonus").exists():
            jobs = self.main_jobs(date(y, m, 1))
            day = _weekday(_last_day(y, m) - timedelta(days=6))
            order = self._order("bonus", day, basis="Demersurile șefilor de subdiviziuni, decizia comisiei de premiere")
            if order is not None:
                for n, job in enumerate(rnd.sample(jobs, min(len(jobs), rnd.randint(8, 14))), start=1):
                    amount = rnd.choice([1000, 1500, 2000, 2500, 3000]) if kind_of(job.occupation) != "physicians" else rnd.choice([2500, 3000, 4000, 5000])
                    self._item(order, job.employee, {"amount": str(amount), "note": BONUS_NOTES[m]}, n)
                if self._sign(order, f"premiere {m:02d}.{y}"):
                    self.count("premii")
        if m in (5, 12):
            jobs = self.main_jobs(date(y, m, 1))
            day = _weekday(date(y, m, 10))
            order = self._order("material_aid", day, basis="Cererile salariaților")
            if order is not None:
                for n, job in enumerate(rnd.sample(jobs, 2), start=1):
                    self._item(order, job.employee, {"amount": "3000", "note": rnd.choice(["cu ocazia nașterii copilului", "pentru tratament",
                                                                                            "în legătură cu situația familială dificilă"])}, n)
                if self._sign(order, f"ajutor material {m:02d}.{y}"):
                    self.count("ajutor material")

    def allowance_order(self, y: int, m: int):
        """Sporurile pentru condiții nocive (ATI 20 %, radiologie 15 %) — din 1 ianuarie."""
        if (y, m) != (self.year, 1):
            return
        jobs = [j for j in self.main_jobs(date(y, 1, 1)) if j.subdivision.harmful and not j.allowance_pct]
        if not jobs:
            return
        order = self._order("allowance", _weekday(date(y, 1, 5)), basis="Evaluarea factorilor de risc la locul de muncă, contractul colectiv")
        if order is None:
            return
        for n, job in enumerate(jobs, start=1):
            pct = "20" if job.subdivision.code == "ATI" else "15"
            self._item(order, job.employee, {"allowance_pct": pct, "date_from": date(y, 1, 1).isoformat()}, n)
        if self._sign(order, "sporuri"):
            self.count("sporuri", len(jobs))

    def salary_orders(self, y: int, m: int):
        """Majorarea salariului de funcție pentru câțiva angajați (aprilie)."""
        if (y, m) != (self.year, 4):
            return
        rnd = self.rnd
        jobs = [j for j in self.main_jobs(date(y, m, 1)) if kind_of(j.occupation) in ("physicians", "nurses")]
        order = self._order("salary_set", _weekday(date(y, m, 1)), basis="Demersul șefului de secție, decizia consiliului de administrație")
        if order is None:
            return
        for n, job in enumerate(rnd.sample(jobs, min(len(jobs), 3)), start=1):
            new = (job.base_salary * Decimal("1.10") / 50).quantize(ONE) * 50
            self._item(order, job.employee, {"base_salary": str(new), "date_from": date(y, m, 1).isoformat()}, n)
        if self._sign(order, "majorare salarii"):
            self.count("majorări", 3)

    def hire_orders(self, y: int, m: int):
        """Două angajări în anul curent: o asistentă la traumatologie (martie) și un îngrijitor (iulie)."""
        if y != self.year or m not in (3, 7):
            return
        from apps.org.models import Occupation, Subdivision
        from apps.staff import services as staff
        from apps.staff.models import Education, Employee
        from apps.org.models import DictItem

        rnd = self.rnd
        if m == 3:
            sub, occ_name, salary, sex = "TR1", "Asistent medical de secție", 10500, "F"
        else:
            sub, occ_name, salary, sex = "GOS", "Îngrijitor încăperi", 6800, rnd.choice("MF")
        subdivision = Subdivision.objects.filter(code=sub).first()
        occ = Occupation.objects.filter(name_ro=occ_name).first()
        if subdivision is None or occ is None:
            return
        last, first = rnd.choice(SURNAMES), rnd.choice(WOMEN if sex == "F" else MEN)
        start = _weekday(date(y, m, 1))
        emp = Employee.objects.create(tab_number=staff.next_tab_number(), last_name=last, first_name=first, sex=sex,
                                      birth_date=date(y - rnd.randint(23, 45), rnd.randint(1, 12), rnd.randint(1, 28)), idnp=_idnp(rnd),
                                      phone=f"069{rnd.randint(100000, 999999)}", address=f"mun. Chișinău, str. {rnd.choice(SURNAMES)} {rnd.randint(1, 90)}",
                                      iban=f"MD{rnd.randint(10, 99)}AG{rnd.randint(10**17, 10**18 - 1)}", bank_name=BANKS[0])
        level = DictItem.objects.filter(kind="education", code="vocational" if m == 3 else "secondary").first()
        Education.objects.create(employee=emp, level=level, institution="Colegiul de Medicină din Chișinău" if m == 3 else "Liceul teoretic",
                                 year_to=start.year - rnd.randint(2, 15))
        order = self._order("hire", start, basis=f"Cererea de angajare din {(start - timedelta(days=3)):%d.%m.%Y}, CIM nr. {emp.tab_number}/{y}")
        if order is None:
            return
        self._item(order, emp, {"kind": "main", "subdivision": subdivision.pk, "occupation": occ.pk, "rate": "1", "base_salary": str(salary),
                                "date_from": start.isoformat(), "contract_number": f"{emp.tab_number}/{y}", "contract_date": start.isoformat(),
                                "probation_until": (start + timedelta(days=90)).isoformat()}, 1)
        if self._sign(order, f"angajare {m:02d}.{y}"):
            self.count("angajări")

    def terminate_order(self, y: int, m: int):
        """O eliberare prin demisie (mai), cu compensarea concediului nefolosit."""
        if (y, m) != (self.year, 5):
            return
        from apps.org.models import DictItem

        reason = DictItem.objects.filter(kind="termination", code="resignation").first()
        jobs = [j for j in self.main_jobs(date(y, m, 1)) if j.subdivision.code == "GOS" and j.employee_id not in self.plan]
        jobs = jobs or [j for j in self.main_jobs(date(y, m, 1)) if j.subdivision.code == "GOS"]
        if not jobs or reason is None:
            return
        job = jobs[-1]
        self.plan.pop(job.employee_id, None)
        day = _weekday(date(y, m, 15))
        order = self._order("terminate", day, basis=f"Cererea salariatului din {(day - timedelta(days=14)):%d.%m.%Y}")
        if order is None:
            return
        self._item(order, job.employee, {"date_from": day.isoformat(), "reason": reason.pk, "compensation_days": "7"}, 1)
        if self._sign(order, "eliberare"):
            self.count("eliberări")

    def other_leave_orders(self, y: int, m: int):
        """Un concediu neplătit (februarie) și zile libere plătite la căsătorie (august)."""
        from apps.leave import services as leave_services

        if y != self.year or m not in (2, 8):
            return
        rnd = self.rnd
        code, kind, days, basis = (("leave_unpaid", "unpaid", 5, "Cererea salariatului (motive familiale)") if m == 2
                                   else ("days_off_paid", "days_off", 3, "Cererea salariatului, certificatul de căsătorie"))
        jobs = self.main_jobs(date(y, m, 1))
        for job in rnd.sample(jobs, min(len(jobs), 6)):
            start = _weekday(date(y, m, rnd.randint(5, 18)))
            _s, end, _n = leave_services.period(kind, start, days)
            if leave_services.overlapping(job.employee, start, end).exists():
                continue
            order = self._order(code, start - timedelta(days=2), basis=basis)
            if order is None:
                return
            self._item(order, job.employee, {"date_from": start.isoformat(), "days": days}, 1)
            self._sign(order, code)
            return

    # --- luna: grafice, pontaj, avans, calcul, plată ------------------------------------------------------------
    def rosters(self, y: int, m: int, approved: bool):
        from apps.org.models import Subdivision
        from apps.worktime import services as worktime
        from apps.worktime.models import Roster

        for sub in Subdivision.objects.filter(code__in=SHIFT_SUBDIVISIONS):
            roster, _ = Roster.objects.get_or_create(subdivision=sub, year=y, month=m, defaults={"created_by": self.users.get("sef.trauma") or self.cadre})
            worktime.fill_roster(roster, overwrite=True)
            if approved and roster.status != "approved":
                roster.status, roster.approved_by = "approved", self.cadre
                roster.approved_at = timezone.make_aware(timezone.datetime(y, m, 1, 9, 0)) - timedelta(days=5)
                roster.save(update_fields=["status", "approved_by", "approved_at"])
            self.count("grafice lunare")

    def timesheets(self, y: int, m: int, closed: bool):
        from apps.org.models import Subdivision
        from apps.worktime import services as worktime
        from apps.worktime.models import Timesheet

        for sub in Subdivision.objects.filter(parent__isnull=True):
            ts, _ = Timesheet.objects.get_or_create(subdivision=sub, year=y, month=m, defaults={"created_by": self.cadre})
            if ts.status == "closed":
                continue
            worktime.fill_timesheet(ts)
            if closed and ts.lines.exists():
                when = timezone.make_aware(timezone.datetime.combine(_weekday(_last_day(y, m) + timedelta(days=1)), timezone.datetime.min.time().replace(hour=10)))
                ts.status, ts.submitted_at, ts.closed_at, ts.closed_by = "closed", when, when + timedelta(hours=3), self.cadre
                ts.save(update_fields=["status", "submitted_at", "closed_at", "closed_by"])
            self.count("tabele de pontaj")

    def _payment(self, y: int, m: int, kind: str, day: date, base=None):
        from apps.core.models import NumberSeries
        from apps.payroll import payments
        from apps.payroll.models import Payment

        pay = Payment.objects.create(year=y, month=m, kind=kind, method="all", date=day, created_by=self.contabil, payroll=base,
                                     number=NumberSeries.next_number("payroll_payment"))
        n = payments.fill(pay)
        if not n:
            pay.delete()
            return None
        pay.status, pay.paid_on = "paid", day
        pay.reference = (f"Ordinul de plată nr. {self.rnd.randint(100, 999)} din {day:%d.%m.%Y}; dispoziția de plată nr. {self.rnd.randint(10, 99)}")
        pay.save(update_fields=["status", "paid_on", "reference"])
        self.count("avansuri" if kind == "advance" else "plăți salariu")
        return pay

    def payroll(self, y: int, m: int, approve: bool):
        from apps.core.models import NumberSeries
        from apps.payroll import engine
        from apps.payroll.models import Payroll

        doc = Payroll.objects.create(year=y, month=m, date=_last_day(y, m), created_by=self.contabil, number=NumberSeries.next_number("payroll"),
                                     note="" if approve else "Luna curentă: calcul preliminar, se aprobă după închiderea pontajului.")
        engine.calculate(doc)
        if approve and doc.lines.exists():
            doc.status, doc.approved_by = "approved", self.director
            doc.approved_at = timezone.make_aware(timezone.datetime.combine(_weekday(_last_day(y, m) + timedelta(days=2)),
                                                                            timezone.datetime.min.time().replace(hour=15)))
            doc.save(update_fields=["status", "approved_by", "approved_at"])
        self.count("calcule")
        return doc

    def month(self, y: int, m: int):
        current = (y, m) == (self.today.year, self.today.month)
        self.log(f"{m:02d}.{y}" + (" (luna curentă)" if current else ""))
        # 1. ordinele și absențele lunii
        self.allowance_order(y, m)
        self.hire_orders(y, m)
        self.leave_orders(y, m)
        self.other_leave_orders(y, m)
        self.sick_leaves(y, m)
        self.travel_orders(y, m)
        if m % 2 == 0:
            self.training_orders(y, m)
        self.salary_orders(y, m)
        self.terminate_order(y, m)
        self.bonus_orders(y, m)
        # 2. graficele de gărzi și tabelele de pontaj
        self.rosters(y, m, approved=not current)
        self.timesheets(y, m, closed=not current)
        # 3. avansul (15 ale lunii), calculul, plata salariului (în luna următoare)
        advance_day = _weekday(date(y, m, 15))
        if advance_day <= self.today:
            self._payment(y, m, "advance", advance_day)
        doc = self.payroll(y, m, approve=not current)
        if not current:  # îndreptarea spre plată în baza calculului: aici se rețin CNAM și impozitul
            self._payment(y, m, "salary", _weekday(_last_day(y, m) + timedelta(days=7)),
                          base=doc if doc.status == "approved" else None)

    # --- după lună -----------------------------------------------------------------------------------------------
    def training_plan(self):
        from apps.training.models import TrainingPlan, TrainingPlanLine, TrainingRecord

        rnd = self.rnd
        plan, created = TrainingPlan.objects.get_or_create(year=self.year, defaults={
            "number": "1", "date": date(self.year - 1, 12, 20), "status": "approved", "created_by": self.cadre})
        if not created:
            return
        staff = [j for j in self.main_jobs(date(self.year, 1, 1)) if kind_of(j.occupation) in ("physicians", "nurses", "pharmacists")]
        for n, job in enumerate(rnd.sample(staff, min(len(staff), 24)), start=1):
            title, provider, hours = rnd.choice(COURSES[:4] if kind_of(job.occupation) == "physicians" else COURSES[4:])
            month = rnd.randint(2, 11)
            record = TrainingRecord.objects.filter(employee=job.employee, date_from__year=self.year, title=title).first()
            TrainingPlanLine.objects.create(plan=plan, employee=job.employee, kind="course", title=title, provider=provider, month=month,
                                            hours=Decimal(hours), record=record)
        self.count("plan de formare", 1)

    def cleanup(self):
        """Documentele lunare făcute de `crm_demo` (luna trecută) se refac aici în ordine cronologică."""
        from apps.orders.models import Incentive, Order
        from apps.payroll.models import Payment, Payroll
        from apps.worktime.models import Roster, Timesheet

        Payment.objects.all().delete()
        Payroll.objects.all().delete()
        Timesheet.objects.all().delete()
        Roster.objects.all().delete()
        for order in Order.objects.filter(order_type__code="bonus"):
            Incentive.objects.filter(order_item__order=order).delete()
            order.delete()

    def run(self):
        self.cleanup()
        self.constants()
        self.people()
        self.schedules()
        self.leave_plan()
        self.leave_schedules()
        for y, m in _months(self.year, self.today.month):
            self.month(y, m)
        # luna următoare: graficele de gărzi, pregătite (ciornă)
        ny, nm = (self.year + 1, 1) if self.today.month == 12 else (self.year, self.today.month + 1)
        self.rosters(ny, nm, approved=False)
        self.training_plan()
        return self.stats


@transaction.atomic
def run(year: int | None = None, force: bool = False, log=print) -> dict:
    from apps.payroll.models import Payroll
    from apps.staff.models import Employee

    if not Employee.objects.exists():
        raise DemoError("Baza nu are angajați: rulați întâi `crm_demo`.")
    year = year or timezone.localdate().year
    if Payroll.objects.filter(year=year, month=1).exists() and not force:
        raise DemoError(f"Anul {year} are deja calcule lunare; datele pe an se pun o singură dată (sau cu --force).")
    return Year(year, log=log).run()
