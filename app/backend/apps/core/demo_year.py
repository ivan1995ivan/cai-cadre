"""Datele demo pe un an întreg, peste întreprinderea făcută de `crm_demo` („Demo Producție” SRL): evidența lunară completă
din noiembrie anul trecut până în luna curentă — graficele de ture ale atelierului, tabelele de pontaj (închise), avansul și
salariul (calculate, aprobate, achitate), ordinele anului (concedii din graficul anual, delegări la clienți și furnizori,
formare profesională, premii trimestriale, ajutor material, sporul pentru condiții vătămătoare, majorări de salariu, angajări,
o eliberare), foile de boală, cererile de scutire, cotizațiile și reținerile personale, graficul concediilor și planul de
formare. Totul trece prin serviciile modulelor, ca în lucru.

Se rulează o singură dată, după `crm_demo`:  manage.py crm_demo_year
"""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .demo import COURSES, DEMO_DOMAIN, MEN, SHIFT_OCCUPATION, SHIFT_SECTOR, SURNAMES, WOMEN, DemoError, _idnp, group_of, \
    is_production

ONE = Decimal("1")
SHIFT_SUBDIVISIONS = ("ATL",)  # graficul lunar de ture: atelierul de producție (cu sectoarele lui)
LEAVE_WEIGHTS = [3, 3, 4, 5, 6, 9, 10, 9, 6, 4, 3, 3]  # în ce luni pleacă oamenii în concediu (vara cel mai mult)
BANKS = ["BC „Moldova-Agroindbank” S.A.", "BC „Victoriabank” S.A.", "BC „Moldindconbank” S.A."]
TRAVEL = [("mun. Bălți, clientul „Demo Nord” SRL", "negocierii contractului de livrare"),
          ("or. Cahul, clientul „Demo Sud” SRL", "montării și punerii în funcțiune a construcțiilor livrate"),
          ("Iași, România — târgul de utilaje industriale", "participării la târg"),
          ("or. Orhei, furnizorul „Demo Metal” SRL", "recepției materiei prime")]
TRAVELLERS = ("VNZ", "ATL")  # cine pleacă în delegare: vânzările și inginerii atelierului
SICK_ISSUERS = ["Centrul de sănătate „Demo” SRL", "Clinica „Demo Familia” SRL", "Centrul medical „Demo Plus” SRL"]
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
        self.users = {u.username: u for u in User.objects.filter(username__in=("cadre", "director", "contabil", "sef.productie"))}
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
            family = list(FamilyMember.objects.filter(employee=emp, dependent=True))
            if not ExemptionRequest.objects.filter(employee=emp).exists():
                y = self.year - 1  # cererea nu se reînnoiește anual: una, de la începutul anului trecut
                req = ExemptionRequest.objects.create(
                    employee=emp, date=date(y - 1, 12, rnd.randint(8, 28)), date_from=date(y, 1, 1), kind="personal",
                    documents="copia buletinului" + (", certificatele de naștere" if family else ""))
                for n, f in enumerate(family, start=1):
                    req.dependents.create(family_member=f, name=f.full_name, idnp=f.idnp, birth_date=f.birth_date,
                                          relation="child", disability="severe" if f.disabled else "", sort=n * 10,
                                          document="certificatul de naștere")
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
        """Graficele de lucru: operatorii din sectorul de prelucrare mecanică — ture de 12 ore (zi / noapte); `crm_demo` le pune
        celor angajați de el, aici — și celor angajați după."""
        from apps.worktime import seed as worktime_seed
        from apps.worktime.models import JobSchedule, WorkSchedule

        worktime_seed.run()
        zn = WorkSchedule.objects.filter(code="ZN", deletion_mark=False).first()
        if zn is None:
            return
        for i, job in enumerate(self.main_jobs(self.today)):
            if (job.subdivision.code != SHIFT_SECTOR or job.occupation.name_ro != SHIFT_OCCUPATION
                    or JobSchedule.objects.filter(employment=job).exists()):
                continue
            JobSchedule.objects.create(employment=job, schedule=zn, date_from=job.date_from, cycle_offset=i % 4)
            self.count("grafice ZN")

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
                             issued_on=start, issued_by=rnd.choice(SICK_ISSUERS),
                             kind=rnd.choice(["illness", "illness", "illness", "household_injury", "child_care"]),
                             date_from=start, date_to=end, return_date=_weekday(end + timedelta(days=1)), created_by=self.cadre)
            try:
                leave_services.save_sick_leave(sick)
                self.count("foi de boală")
            except ValidationError as exc:
                self.log(f"  foaia de boală nu s-a înregistrat: {exc.detail}")

    def travel_orders(self, y: int, m: int):
        rnd = self.rnd
        who = [j for j in self.main_jobs(date(y, m, 1)) if j.subdivision.code in TRAVELLERS and group_of(j.occupation) in ("1", "2", "3")]
        if not who:
            return
        day = _weekday(date(y, m, rnd.randint(3, 18)))
        order = self._order("travel", day - timedelta(days=2) if day.day > 2 else day, basis="Demersul șefului subdiviziunii")
        if order is None:
            return
        for n, job in enumerate(rnd.sample(who, min(len(who), rnd.randint(1, 2))), start=1):
            where, purpose = rnd.choice(TRAVEL)
            self._item(order, job.employee, {"date_from": day.isoformat(), "date_to": (day + timedelta(days=rnd.randint(1, 2))).isoformat(),
                                             "destination": where, "purpose": purpose}, n)
        if self._sign(order, f"delegare {m:02d}.{y}"):
            self.count("delegări")

    def training_orders(self, y: int, m: int):
        from apps.leave import services as leave_services
        from apps.training.models import TrainingRecord

        rnd = self.rnd
        staff = self.main_jobs(date(y, m, 1))
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
            title, provider, hours = rnd.choice(COURSES["production" if is_production(job.subdivision) else "office"])
            self._item(order, job.employee, {"date_from": start.isoformat(), "date_to": end.isoformat(), "destination": provider,
                                             "purpose": f"participării la cursul „{title}”"}, n)
            chosen.append((job, title, provider, hours))
        if not n:
            order.delete()
            return
        if self._sign(order, f"formare {m:02d}.{y}"):
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
                    amount = rnd.choice([2500, 3000, 4000, 5000]) if group_of(job.occupation) in ("1", "2") else rnd.choice([1000, 1500, 2000, 2500, 3000])
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
        """Sporul pentru condiții vătămătoare (sectorul de sudură și vopsire, 10 %) — din 1 ianuarie."""
        if (y, m) != (self.year, 1):
            return
        jobs = [j for j in self.main_jobs(date(y, 1, 1)) if j.subdivision.harmful and not j.allowance_pct]
        if not jobs:
            return
        order = self._order("allowance", _weekday(date(y, 1, 5)), basis="Evaluarea factorilor de risc la locul de muncă, contractul colectiv")
        if order is None:
            return
        for n, job in enumerate(jobs, start=1):
            self._item(order, job.employee, {"allowance_pct": "10", "date_from": date(y, 1, 1).isoformat()}, n)
        if self._sign(order, "sporuri"):
            self.count("sporuri", len(jobs))

    def salary_orders(self, y: int, m: int):
        """Majorarea salariului de funcție pentru câțiva angajați (aprilie)."""
        if (y, m) != (self.year, 4):
            return
        rnd = self.rnd
        jobs = [j for j in self.main_jobs(date(y, m, 1)) if group_of(j.occupation) in ("7", "8")]
        order = self._order("salary_set", _weekday(date(y, m, 1)), basis="Demersul șefului atelierului de producție, decizia directorului")
        if order is None:
            return
        for n, job in enumerate(rnd.sample(jobs, min(len(jobs), 3)), start=1):
            new = (job.base_salary * Decimal("1.10") / 50).quantize(ONE) * 50
            self._item(order, job.employee, {"base_salary": str(new), "date_from": date(y, m, 1).isoformat()}, n)
        if self._sign(order, "majorare salarii"):
            self.count("majorări", 3)

    def hire_orders(self, y: int, m: int):
        """Două angajări în anul curent: un operator în sectorul de prelucrare mecanică (martie) și un magaziner (iulie)."""
        if y != self.year or m not in (3, 7):
            return
        from apps.org.models import Occupation, Subdivision
        from apps.staff import services as staff
        from apps.staff.models import Education, Employee
        from apps.org.models import DictItem

        rnd = self.rnd
        if m == 3:
            sub, occ_name, salary, sex = SHIFT_SECTOR, SHIFT_OCCUPATION, 11500, "M"
        else:
            sub, occ_name, salary, sex = "DEP", "Magaziner", 10000, rnd.choice("MF")
        subdivision = Subdivision.objects.filter(code=sub).first()
        occ = Occupation.objects.filter(name_ro=occ_name).first()
        if subdivision is None or occ is None:
            return
        last, first = rnd.choice(SURNAMES), rnd.choice(WOMEN if sex == "F" else MEN)
        start = _weekday(date(y, m, 1))
        emp = Employee.objects.create(tab_number=staff.next_tab_number(), last_name=last, first_name=first, sex=sex,
                                      birth_date=date(y - rnd.randint(23, 45), rnd.randint(1, 12), rnd.randint(1, 28)), idnp=_idnp(rnd),
                                      phone=f"069{rnd.randint(100000, 999999)}", email=f"angajat.{y}.{m:02d}@{DEMO_DOMAIN}", address=f"mun. Chișinău, str. {rnd.choice(SURNAMES)} {rnd.randint(1, 90)}",
                                      iban=f"MD{rnd.randint(10, 99)}AG{rnd.randint(10**17, 10**18 - 1)}", bank_name=BANKS[0])
        level = DictItem.objects.filter(kind="education", code="secondary" if m == 3 else "vocational").first()
        Education.objects.create(employee=emp, level=level, institution="Școala profesională nr. 3 din Chișinău" if m == 3
                                 else "Colegiul Politehnic din Chișinău",
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
        jobs = [j for j in self.main_jobs(date(y, m, 1)) if j.subdivision.code == "DEP" and j.employee_id not in self.plan]
        jobs = jobs or [j for j in self.main_jobs(date(y, m, 1)) if j.subdivision.code == "DEP"]
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
            roster, _ = Roster.objects.get_or_create(subdivision=sub, year=y, month=m, defaults={"created_by": self.users.get("sef.productie") or self.cadre})
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
        # 2. graficele de ture și tabelele de pontaj
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
        staff = self.main_jobs(date(self.year, 1, 1))
        for n, job in enumerate(rnd.sample(staff, min(len(staff), 24)), start=1):
            title, provider, hours = rnd.choice(COURSES["production" if is_production(job.subdivision) else "office"])
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
        # luna următoare: graficul de ture, pregătit (ciornă)
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
