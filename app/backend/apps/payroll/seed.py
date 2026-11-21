"""Constantele salariului pentru 2026 și tipurile de calcul predefinite (se creează doar dacă lipsesc; se schimbă din interfață)."""
from datetime import date
from decimal import Decimal

from .models import PayConstant, PayType

# cod, denumire, valoarea 2026, unitatea, temeiul
CONSTANTS = [
    ("income_tax_pct", "Impozitul pe venit al persoanelor fizice", "12", "%", "Codul fiscal, art. 15"),
    ("exemption_personal", "Scutirea personală anuală", "29700", "lei", "Codul fiscal, art. 33 alin. (1)"),
    ("exemption_major", "Scutirea personală majorată anuală", "34620", "lei", "Codul fiscal, art. 33 alin. (2)"),
    ("exemption_spouse", "Scutirea anuală pentru soț / soție", "21780", "lei", "Codul fiscal, art. 34"),
    ("exemption_dependent", "Scutirea anuală pentru persoana întreținută", "9900", "lei", "Codul fiscal, art. 35"),
    ("exemption_dependent_disabled", "Scutirea anuală pentru întreținutul cu dizabilitate severă", "21780", "lei", "Codul fiscal, art. 35"),
    ("exemption_income_limit", "Venitul anual peste care scutirea personală nu se acordă", "360000", "lei", "Codul fiscal, art. 33"),
    ("cas_employer_pct", "Contribuția de asigurări sociale a angajatorului", "24", "%", "Legea BASS 2026"),
    ("cnam_employee_pct", "Prima de asigurare medicală reținută angajatului", "9", "%", "Legea FAOAM 2026"),
    ("union_pct", "Cotizația sindicală", "1", "%", "Statutul sindicatului"),
    ("min_salary", "Salariul minim pe economie (lunar)", "5500", "lei", "HG anuală (de verificat)"),
    ("avg_salary", "Salariul mediu lunar pe economie prognozat", "17200", "lei", "HG anuală (de verificat)"),
    ("night_pct", "Sporul pentru munca de noapte (la tariful orar)", "50", "%", "Codul muncii, art. 159"),
    ("overtime_pct", "Sporul pentru orele suplimentare (la tariful orar)", "50", "%", "Codul muncii, art. 157 (150 %)"),
    ("holiday_pct", "Sporul pentru munca în zile de sărbătoare / odihnă (la tariful orar)", "100", "%", "Codul muncii, art. 158 (200 %)"),
    ("sick_employer_days", "Zilele de boală plătite de angajator (de la începutul certificatului)", "5", "zile", "Legea 289/2004, art. 4"),
    ("sick_employer_pct", "Indemnizația de boală plătită de angajator (% din venitul mediu)", "75", "%", "Legea 289/2004, art. 4"),
    ("sick_avg_months", "Perioada de decontare pentru indemnizația de boală", "12", "luni", "Legea 289/2004, art. 7"),
    ("leave_avg_months", "Perioada de decontare pentru salariul mediu (concedii)", "3", "luni", "HG 426/2004"),
    ("advance_pct", "Avansul (% din salariul de funcție al raportului de bază)", "40", "%", "Contractul colectiv / regulamentul intern"),
]

# cod, denumire RO, RU, EN, categoria, formula, auto, procent, baza, scara, impozabil, CAS, CNAM, plafon lună, plafon % mediu,
# în medie, cod IPC, ordinea
T, F = True, False
TYPES = [
    ("SAL", "Salariul de funcție", "Должностной оклад", "Base salary", "accrual", "auto", "salary", "0", [], [], T, T, T, "0", "0", T, "SAL", 10),
    ("SPOR", "Sporuri fixe (din raportul de muncă)", "Постоянные надбавки", "Fixed allowances", "accrual", "auto", "allowance", "0", [], [], T, T, T, "0", "0", T, "SAL", 20),
    ("CUMUL", "Plata pentru cumul de funcții", "Доплата за совмещение", "Combination pay", "accrual", "auto", "combination", "0", [], [], T, T, T, "0", "0", T, "SAL", 30),
    # sporul pentru condiții de muncă grele, vătămătoare și / sau periculoase (Codul muncii, art. 139; mărimea — în contractul
    # colectiv / individual)
    ("NOCIV", "Spor pentru condiții nocive / vătămătoare", "Надбавка за вредные условия", "Hazardous conditions allowance", "accrual",
     "pct_salary", "none", "0", [], [], T, T, T, "0", "0", T, "SAL", 60),
    ("NOAPTE", "Munca de noapte", "Работа в ночное время", "Night work", "accrual", "auto", "night", "0", [], [], T, T, T, "0", "0", T, "SAL", 70),
    ("SARB", "Munca în zile de sărbătoare / odihnă", "Работа в праздничные / выходные дни", "Holiday work", "accrual", "auto", "holiday", "0", [], [], T, T, T, "0", "0", T, "SAL", 80),
    ("SUPL", "Ore suplimentare", "Сверхурочные часы", "Overtime", "accrual", "auto", "overtime", "0", [], [], T, T, T, "0", "0", T, "SAL", 90),
    ("CO", "Indemnizația de concediu de odihnă", "Отпускные", "Annual leave pay", "accrual", "auto", "leave", "0", [], [], T, T, T, "0", "0", F, "SAL", 100),
    ("COMP", "Compensarea concediului nefolosit", "Компенсация за неиспользованный отпуск", "Unused leave compensation", "accrual", "auto", "leave_comp", "0", [], [], T, T, T, "0", "0", F, "SAL", 110),
    ("BOALA", "Indemnizația de boală (zilele angajatorului)", "Больничный (дни работодателя)", "Sick pay (employer days)", "accrual", "auto", "sick", "0", [], [], T, F, T, "0", "0", F, "SAL", 120),
    ("PREMIU", "Premiu", "Премия", "Bonus", "accrual", "auto", "bonus", "0", [], [], T, T, T, "0", "0", T, "SAL", 130),
    ("AJUTOR", "Ajutor material", "Материальная помощь", "Financial aid", "accrual", "auto", "aid", "0", [], [], T, T, T, "0", "0", F, "SAL", 140),
    ("CADOU", "Cadouri / vouchere", "Подарки / ваучеры", "Gifts / vouchers", "accrual", "fixed", "none", "0", [], [], T, T, T, "0", "10", F, "SAL", 150),
    ("CONTRACT", "Plata la contractul de prestări servicii", "Оплата по договору оказания услуг", "Service contract pay", "accrual", "fixed", "none", "0", [], [], T, T, T, "0", "0", F, "SAL", 160),
    ("ALTE", "Alte plăți", "Прочие выплаты", "Other payments", "accrual", "fixed", "none", "0", [], [], T, T, T, "0", "0", F, "SAL", 170),
    ("IMPOZIT", "Impozitul pe venit", "Подоходный налог", "Income tax", "deduction", "auto", "income_tax", "0", [], [], F, F, F, "0", "0", F, "", 200),
    ("CNAM", "Prima de asigurare medicală (9 %)", "Взнос ОМС (9 %)", "Health insurance (9 %)", "deduction", "auto", "cnam", "0", [], [], F, F, F, "0", "0", F, "", 210),
    ("SINDICAT", "Cotizația sindicală", "Профсоюзный взнос", "Union fee", "deduction", "pct_base", "none", "1", ["SAL", "SPOR", "CUMUL", "NOCIV", "NOAPTE", "SARB", "SUPL", "CO", "PREMIU"], [], F, F, F, "0", "0", F, "", 220),
    ("PENSIE", "Pensie alimentară", "Алименты", "Alimony", "deduction", "pct_base", "none", "0", ["SAL", "SPOR", "CUMUL", "NOCIV", "NOAPTE", "SARB", "SUPL", "CO", "PREMIU"], [], F, F, F, "0", "0", F, "", 230),
    ("AVANS", "Avans plătit", "Выплаченный аванс", "Advance paid", "deduction", "auto", "advance", "0", [], [], F, F, F, "0", "0", F, "", 240),
    ("IMPRUMUT", "Împrumut / prejudiciu / alte rețineri", "Займ / ущерб / прочие удержания", "Loan / damage / other deductions", "deduction", "fixed", "none", "0", [], [], F, F, F, "0", "0", F, "", 250),
    ("CAS", "Contribuția de asigurări sociale (angajator, 24 %)", "Взнос соцстрахования (работодатель, 24 %)", "Social insurance (employer, 24 %)", "employer", "auto", "cas", "0", [], [], F, F, F, "0", "0", F, "", 300),
]


def run():
    # avansul se scade singur din plățile de avans ale lunii (bazele create înainte de plată aveau „sumă fixă”)
    PayType.objects.filter(code="AVANS", is_system=True, formula="fixed").update(formula="auto", auto="advance")
    for code, name, value, unit, source in CONSTANTS:
        if not PayConstant.objects.filter(code=code).exists():
            PayConstant.objects.create(code=code, name=name, value=Decimal(value), unit=unit, source=source, date_from=date(2026, 1, 1))
    for row in TYPES:
        (code, ro, ru, en, category, formula, auto, pct, base, scale, taxable, cas, cnam, ex_month, ex_avg, in_avg, ipc, sort) = row
        PayType.objects.get_or_create(code=code, defaults={
            "name_ro": ro, "name_ru": ru, "name_en": en, "category": category, "formula": formula, "auto": auto,
            "percent": Decimal(pct), "base_codes": base, "scale": scale, "taxable": taxable, "cas": cas, "cnam": cnam,
            "exempt_month": Decimal(ex_month), "exempt_avg_pct": Decimal(ex_avg), "in_average": in_avg, "ipc_code": ipc,
            "sort": sort, "is_system": True, "on_payslip": True})
