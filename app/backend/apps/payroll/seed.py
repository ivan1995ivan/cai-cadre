"""Constantele salariului pentru 2026 (și 2027, unde e adoptat) și tipurile de calcul predefinite: se creează doar dacă
lipsesc (constantele — pe cod și dată); valorile se schimbă din interfață."""
from datetime import date
from decimal import Decimal

from .models import PayConstant, PayType

Y26, Y27 = date(2026, 1, 1), date(2027, 1, 1)
CHECK = " — de verificat"  # temeiul neconfirmat încă din textul oficial: valoarea se poate corecta din Constante

# cod, denumire, valoarea, unitatea, temeiul, în vigoare din. Rândurile sunt pe (cod, dată): o valoare nouă adoptată (2027)
# se adaugă alături de cea veche; proiectele de acte nu se pun.
CONSTANTS = [
    ("income_tax_pct", "Impozitul pe venit al persoanelor fizice", "12", "%", "Codul fiscal, art. 15", Y26),
    ("exemption_personal", "Scutirea personală anuală (P)", "29700", "lei", "Codul fiscal, art. 33 alin. (1)", Y26),
    ("exemption_personal", "Scutirea personală anuală (P)", "40020", "lei", "Codul fiscal, art. 33 alin. (1); Legea nr. 247 din 22.10.2026", Y27),
    ("exemption_major", "Scutirea personală majorată anuală (M)", "34620", "lei", "Codul fiscal, art. 33 alin. (2)", Y26),
    ("exemption_major", "Scutirea personală majorată anuală (M)", "46680", "lei", "Codul fiscal, art. 33 alin. (2); Legea nr. 247 din 22.10.2026", Y27),
    ("exemption_spouse", "Scutirea anuală pentru soț / soție (Sm)", "21780", "lei", "Codul fiscal, art. 34 alin. (2)", Y26),
    ("exemption_dependent", "Scutirea anuală pentru persoana întreținută (N)", "9900", "lei", "Codul fiscal, art. 35 alin. (1)", Y26),
    ("exemption_dependent", "Scutirea anuală pentru persoana întreținută (N)", "11040", "lei", "Codul fiscal, art. 35 alin. (1); Legea nr. 247 din 22.10.2026", Y27),
    ("exemption_dependent_disabled", "Scutirea anuală pentru întreținutul cu dizabilitate din copilărie, severă sau accentuată (H)",
     "21780", "lei", "Codul fiscal, art. 35 alin. (1)", Y26),
    ("exemption_dependent_income", "Venitul anual maxim al persoanei întreținute", "12400", "lei", "Codul fiscal, art. 35 alin. (2) lit. b)", Y26),
    ("exemption_income_limit", "Venitul anual impozabil de la care nu se acordă scutirea P / M", "360000", "lei", "Codul fiscal, art. 33 alin. (1)", Y26),
    ("exemption_limit_alert_pct", "Alerta: venitul anual la angajator a atins % din plafonul scutirii P / M", "90", "%", "Setarea întreprinderii", Y26),
    ("cas_employer_pct", "Contribuția de asigurări sociale a angajatorului", "24", "%", "Legea 489/1999, anexa nr. 1; Legea BASS 2026", Y26),
    ("cas_min_part_pct", "Timp parțial: CAS cel puțin % din CAS-ul pe salariul minim", "25", "%", "Legea 489/1999, art. 22 alin. (1)", Y26),
    ("cnam_employee_pct", "Prima de asigurare medicală reținută angajatului", "9", "%", "Legea FAOAM 2026", Y26),
    ("union_pct", "Cotizația sindicală", "1", "%", "Statutul sindicatului", Y26),
    ("min_salary", "Salariul minim pe țară (lunar)", "6300", "lei", "HG nr. 771 din 17.12.2025", Y26),
    ("min_salary_hours", "Norma de ore pentru tariful orar minim (salariul minim / ore = 37,28 lei/oră)", "169", "ore", "HG nr. 771/2025", Y26),
    ("avg_salary", "Salariul mediu lunar pe economie prognozat", "17400", "lei", "HG nr. 773/2025", Y26),
    ("night_pct", "Sporul pentru munca de noapte (la tariful orar)", "50", "%", "Codul muncii, art. 159", Y26),
    ("overtime_first_hours", "Ore suplimentare: câte ore pe zi se plătesc cu tariful întâi", "2", "ore", "Codul muncii, art. 157 alin. (1)", Y26),
    ("overtime_first_pct", "Ore suplimentare: primele ore (din salariul de bază pe oră)", "150", "%", "Codul muncii, art. 157 alin. (1)", Y26),
    ("overtime_next_pct", "Ore suplimentare: orele următoare (din salariul de bază pe oră)", "200", "%", "Codul muncii, art. 157 alin. (1)", Y26),
    ("holiday_pct", "Sărbători / zile de repaus, salariul lunar: în limita normei lunare (+ % pe oră peste salariu)", "100", "%",
     "Codul muncii, art. 158 alin. (1)", Y26),
    ("holiday_over_norm_pct", "Sărbători / zile de repaus, salariul lunar: peste norma lunară (+ % pe oră peste salariu)", "200", "%",
     "Codul muncii, art. 158 alin. (1)", Y26),
    ("holiday_hourly_pct", "Sărbători / zile de repaus, tarif pe oră / acord: plata (% din tarif)", "200", "%", "Codul muncii, art. 158 alin. (1)", Y26),
    ("sick_employer_days", "Zilele de boală plătite de angajator (de la începutul certificatului)", "5", "zile", "Legea 289/2004, art. 4 alin. (2¹)", Y26),
    ("sick_employer_year_days", "Zilele de boală plătite de angajator: cel mult pe an calendaristic", "15", "zile", "Legea 289/2004, art. 4 alin. (2¹)", Y26),
    ("sick_accident_days", "Accident de muncă / boală profesională: zilele plătite de angajator", "20", "zile",
     "Legea 756/1999 (asigurarea pentru accidente de muncă)" + CHECK, Y26),
    ("sick_accident_pct", "Accident de muncă / boală profesională: indemnizația (% din venitul mediu)", "100", "%",
     "Legea 756/1999 (asigurarea pentru accidente de muncă)" + CHECK, Y26),
    ("sick_employer_pct", "Indemnizația de boală plătită de angajator (% din venitul mediu)", "75", "%", "Legea 289/2004" + CHECK, Y26),
    ("sick_avg_months", "Perioada de calcul a venitului mediu pentru indemnizația de boală", "12", "luni", "Legea 289/2004, art. 7 alin. (1)", Y26),
    ("sick_avg_cap_salaries", "Plafonul venitului mediu lunar pentru boală (salarii medii prognozate)", "5", "", "Legea 289/2004, art. 7 alin. (3)", Y26),
    ("leave_avg_months", "Perioada de calcul a salariului mediu (concedii)", "3", "luni", "HG nr. 426/2004", Y26),
    ("advance_pct", "Avansul (% din salariul de funcție al raportului de bază)", "40", "%", "Contractul colectiv / regulamentul intern", Y26),
    # S5b: timpul fără producție (CM art. 80, 80¹, 161) — procentele legale minime; ordinul poate da un procent mai mare
    ("idle_employer_pct", "Staționarea din vina angajatorului: plata (% din salariul de bază pe oră)", "100", "%",
     "Codul muncii, art. 80¹" + CHECK, Y26),
    ("idle_nofault_pct", "Staționarea fără vina părților: plata (% din salariul de bază pe oră; nu sub salariul minim pe oră)",
     "66.6667", "%", "Codul muncii, art. 80¹" + CHECK, Y26),
    ("idle_worker_pct", "Staționarea din vina salariatului: plata (% din salariul de bază pe oră)", "0", "%",
     "Codul muncii, art. 80¹" + CHECK, Y26),
    ("tech_unemployment_pct", "Șomajul tehnic: plata (% din salariul de bază)", "50", "%", "Codul muncii, art. 80" + CHECK, Y26),
    ("shortfall_nofault_pct", "Acord, norma neîndeplinită fără vina părților: garanția (% din tariful categoriei pe oră)",
     "66.6667", "%", "Codul muncii, art. 161" + CHECK, Y26),
    # tichetele de masă (Legea 166/2017, HG 227/2018 cu modificările din 22.01.2026)
    ("meal_voucher_value", "Tichetele de masă: valoarea nominală a tichetului (0 — nu se acordă)", "0", "lei",
     "Ordinul conducătorului (HG 227/2018, pct. 8)", Y26),
    ("meal_voucher_min", "Tichetele de masă: valoarea nominală minimă", "35", "lei", "Legea 166/2017; Codul fiscal, art. 24" + CHECK, Y26),
    ("meal_voucher_cap", "Tichetele de masă: valoarea neimpozabilă a tichetului (peste ea — facilitate impozabilă)", "70", "lei",
     "Codul fiscal, art. 19 lit. a¹), art. 24; HG 227/2018 (modif. 22.01.2026)" + CHECK, Y26),
    ("meal_voucher_night_pct", "Tichetele de masă: schimbul e de noapte dacă orele de noapte sunt cel puțin % din el", "50", "%",
     "Setarea întreprinderii (HG 227/2018, pct. 12)", Y26),
    # regimul IT Park (se folosesc doar în lunile în regim — Setări → Constantele salarizării → Regimul fiscal)
    ("it_park_tax_pct", "IT Park: impozitul unic (% din venitul lunar din vânzări)", "7", "%", "Codul fiscal, art. 370 alin. (1)", Y26),
    ("it_park_min_pct", "IT Park: impozitul unic minim pe angajat (% din salariul mediu lunar prognozat)", "30", "%",
     "Codul fiscal, art. 370 alin. (2)", Y26),
    ("it_park_insured_pct", "IT Park: venitul asigurat al angajatului (% din salariul mediu lunar prognozat)", "68", "%",
     "Legea 77/2016, art. 16 alin. (1); HG 108/2005, pct. 70¹", Y26),
    ("it_park_sick_covered", "IT Park: zilele de boală plătite de angajator sunt acoperite de impozitul unic (1 — da, 0 — nu)", "1", "",
     "Codul fiscal, art. 372 alin. (1), art. 377" + CHECK, Y26),
    ("it_park_count_maternity", "IT Park: angajatul în concediu de maternitate (fără zi lucrată) se numără la impozitul minim (1 — da, 0 — nu)",
     "1", "", "Codul fiscal, art. 369 alin. (2)" + CHECK, Y26),
    ("it_park_sales_alert_day", "IT Park: alerta „lipsește venitul din vânzări” din ziua lunii următoare (termenul IU17 — 25)", "20",
     "zi", "Setarea întreprinderii; OMF 135/2017 (IU17 — până la 25)", Y26),
]

# cod, denumire RO, RU, EN, categoria, formula, auto, procent, baza, scara, impozabil, CAS, CNAM, plafon lună, plafon % mediu,
# în medie, cod IPC, ordinea
T, F = True, False
TYPES = [
    ("SAL", "Salariul de funcție", "Должностной оклад", "Base salary", "accrual", "auto", "salary", "0", [], [], T, T, T, "0", "0", T, "SAL", 10),
    ("SPOR", "Sporuri fixe (din raportul de muncă)", "Постоянные надбавки", "Fixed allowances", "accrual", "auto", "allowance", "0", [], [], T, T, T, "0", "0", T, "SAL", 20),
    # CM art. 131 alin. (3): salariul de funcție sub salariul minim × norma se completează (fără sporuri, premii)
    ("MINIM", "Completare până la salariul minim", "Доплата до минимальной зарплаты", "Top-up to the minimum wage", "accrual", "auto", "min_wage", "0", [], [], T, T, T, "0", "0", T, "SAL", 15),
    # cumularea funcțiilor / suplinirea / interimatul pe același CIM (CM art. 156) — din înregistrările de pe raport; cumulul
    # (intern / extern) e raport separat, cu salariul lui (SAL)
    ("CUMUL", "Plata pentru cumularea funcțiilor / suplinire", "Доплата за совмещение / замещение", "Pay for combining posts / substitution",
     "accrual", "auto", "combination", "0", [], [], T, T, T, "0", "0", T, "SAL", 30),
    # orele pe tipuri (instruire, examinare, zbor…): ore plătite × tariful raportului, ore plătite = max(efective, garantate)
    ("ORE", "Ore pe tipuri (tariful pe oră)", "Часы по видам (часовой тариф)", "Hours by type (hourly rate)", "accrual", "auto",
     "hour_types", "0", [], [], T, T, T, "0", "0", T, "SAL", 35),
    # salarizarea în acord (S5a): lucrările din rapoartele de producție aprobate; sporul acordului progresiv — după treptele
    # tipului (de la % îndeplinire a normei: spor %), pe care le scrie întreprinderea din contractul colectiv (livrat fără trepte)
    ("ACORD", "Salarizarea în acord (lucrările din rapoartele de producție)", "Сдельная оплата (работы из отчётов о выработке)",
     "Piece-rate pay (works from production reports)", "accrual", "auto", "piece", "0", [], [], T, T, T, "0", "0", T, "SAL", 12),
    ("ACORDP", "Acord progresiv: sporul pentru producția peste normă", "Прогрессивная сдельщина: доплата за выработку сверх нормы",
     "Progressive piece rate: supplement for output over the norm", "accrual", "auto", "piece_prog", "0", [], [], T, T, T, "0", "0",
     T, "SAL", 13),
    # sporul pentru condiții de muncă grele, vătămătoare și / sau periculoase (Codul muncii, art. 139; mărimea — în contractul
    # colectiv / individual)
    ("NOCIV", "Spor pentru condiții nocive / vătămătoare", "Надбавка за вредные условия", "Hazardous conditions allowance", "accrual",
     "pct_salary", "none", "0", [], [], T, T, T, "0", "0", T, "SAL", 60),
    # S5b: sporul pentru condiții vătămătoare din subdiviziune / funcție (procentul lor × salariul de bază pe oră × orele
    # lucrate acolo); rândul personal NOCIV, dacă există, îl înlocuiește
    ("VATAM", "Spor pentru condiții vătămătoare (din subdiviziune / funcție)", "Надбавка за вредные условия (из подразделения / должности)",
     "Hazardous conditions allowance (from department / post)", "accrual", "auto", "harmful", "0", [], [], T, T, T, "0", "0", T,
     "SAL", 61),
    ("NOAPTE", "Munca de noapte", "Работа в ночное время", "Night work", "accrual", "auto", "night", "0", [], [], T, T, T, "0", "0", T, "SAL", 70),
    ("SARB", "Munca în zile de sărbătoare / odihnă", "Работа в праздничные / выходные дни", "Holiday work", "accrual", "auto", "holiday", "0", [], [], T, T, T, "0", "0", T, "SAL", 80),
    ("SUPL", "Ore suplimentare", "Сверхурочные часы", "Overtime", "accrual", "auto", "overtime", "0", [], [], T, T, T, "0", "0", T, "SAL", 90),
    # timpul fără producție (S5b): staționarea și șomajul tehnic — din ordine (pontajul: St / Șt); garanția acordului
    ("STATIONARE", "Plata timpului de staționare", "Оплата времени простоя", "Downtime pay", "accrual", "auto", "idle", "0", [], [],
     T, T, T, "0", "0", F, "SAL", 92),
    ("SOMAJT", "Plata pentru șomajul tehnic", "Оплата технического простоя", "Technical unemployment pay", "accrual", "auto",
     "tech_unemployment", "0", [], [], T, T, T, "0", "0", F, "SAL", 94),
    ("GARANT", "Garanția la neîndeplinirea normei (acord)", "Гарантия при невыполнении норм (сдельщина)",
     "Guarantee when the output norm is not met (piece rate)", "accrual", "auto", "piece_guarantee", "0", [], [], T, T, T, "0",
     "0", T, "SAL", 14),
    ("CO", "Indemnizația de concediu de odihnă", "Отпускные", "Annual leave pay", "accrual", "auto", "leave", "0", [], [], T, T, T, "0", "0", F, "SAL", 100),
    ("COMP", "Compensarea concediului nefolosit", "Компенсация за неиспользованный отпуск", "Unused leave compensation", "accrual", "auto", "leave_comp", "0", [], [], T, T, T, "0", "0", F, "SAL", 110),
    ("BOALA", "Indemnizația de boală (zilele angajatorului)", "Больничный (дни работодателя)", "Sick pay (employer days)", "accrual", "auto", "sick", "0", [], [], T, F, T, "0", "0", F, "SAL", 120),
    ("BOALAACC", "Indemnizația pentru accident de muncă / boală profesională (zilele angajatorului)",
     "Пособие при несчастном случае на производстве (дни работодателя)", "Work accident benefit (employer days)", "accrual", "auto",
     "sick_accident", "0", [], [], T, F, T, "0", "0", F, "SAL", 125),
    ("PREMIU", "Premiu", "Премия", "Bonus", "accrual", "auto", "bonus", "0", [], [], T, T, T, "0", "0", T, "SAL", 130),
    ("AJUTOR", "Ajutor material", "Материальная помощь", "Financial aid", "accrual", "auto", "aid", "0", [], [], T, T, T, "0", "0", F, "SAL", 140),
    ("CADOU", "Cadouri / vouchere", "Подарки / ваучеры", "Gifts / vouchers", "accrual", "fixed", "none", "0", [], [], T, T, T, "0", "10", F, "SAL", 150),
    # tichetele de masă (S5b): doar partea peste valoarea neimpozabilă (facilitate impozabilă), din borderoul aprobat, și
    # reținerea ei — tichetele sunt deja pe card, nu se plătesc a doua oară în bani
    ("TICHET", "Tichete de masă: partea peste valoarea neimpozabilă", "Талоны на питание: часть сверх необлагаемой стоимости",
     "Meal vouchers: part above the tax-free value", "accrual", "auto", "meal_voucher", "0", [], [], T, T, T, "0", "0", F, "SAL", 155),
    ("CONTRACT", "Plata la contractul de prestări servicii", "Оплата по договору оказания услуг", "Service contract pay", "accrual", "fixed", "none", "0", [], [], T, T, T, "0", "0", F, "SAL", 160),
    ("ALTE", "Alte plăți", "Прочие выплаты", "Other payments", "accrual", "fixed", "none", "0", [], [], T, T, T, "0", "0", F, "SAL", 170),
    ("IMPOZIT", "Impozitul pe venit", "Подоходный налог", "Income tax", "deduction", "auto", "income_tax", "0", [], [], F, F, F, "0", "0", F, "", 200),
    ("CNAM", "Prima de asigurare medicală (9 %)", "Взнос ОМС (9 %)", "Health insurance (9 %)", "deduction", "auto", "cnam", "0", [], [], F, F, F, "0", "0", F, "", 210),
    ("SINDICAT", "Cotizația sindicală", "Профсоюзный взнос", "Union fee", "deduction", "pct_base", "none", "1", ["SAL", "ACORD", "ACORDP", "GARANT", "MINIM", "SPOR", "CUMUL", "ORE", "NOCIV", "VATAM", "NOAPTE", "SARB", "SUPL", "STATIONARE", "SOMAJT", "CO", "PREMIU"], [], F, F, F, "0", "0", F, "", 220),
    ("PENSIE", "Pensie alimentară", "Алименты", "Alimony", "deduction", "pct_base", "none", "0", ["SAL", "ACORD", "ACORDP", "GARANT", "MINIM", "SPOR", "CUMUL", "ORE", "NOCIV", "VATAM", "NOAPTE", "SARB", "SUPL", "STATIONARE", "SOMAJT", "CO", "PREMIU"], [], F, F, F, "0", "0", F, "", 230),
    ("AVANS", "Avans plătit", "Выплаченный аванс", "Advance paid", "deduction", "auto", "advance", "0", [], [], F, F, F, "0", "0", F, "", 240),
    ("TICHETN", "Tichete de masă acordate în natură", "Талоны на питание, выданные в натуральной форме",
     "Meal vouchers given in kind", "deduction", "auto", "meal_voucher_offset", "0", [], [], F, F, F, "0", "0", F, "", 245),
    ("IMPRUMUT", "Împrumut / prejudiciu / alte rețineri", "Займ / ущерб / прочие удержания", "Loan / damage / other deductions", "deduction", "fixed", "none", "0", [], [], F, F, F, "0", "0", F, "", 250),
    ("CAS", "Contribuția de asigurări sociale (angajator, 24 %)", "Взнос соцстрахования (работодатель, 24 %)", "Social insurance (employer, 24 %)", "employer", "auto", "cas", "0", [], [], F, F, F, "0", "0", F, "", 300),
    ("CASMIN", "CAS pe diferența până la baza minimă (salariul minim)", "Взнос соцстрахования на разницу до минимальной базы",
     "Social insurance on the gap to the minimum base", "employer", "auto", "cas_min", "0", [], [], F, F, F, "0", "0", F, "", 310),
]


# baza sindicatului / pensiei alimentare livrată înainte: până la 1.7 (fără MINIM), până la S4b (fără ORE), până la S5a (fără
# ACORD / ACORDP) și până la S5b (fără GARANT, VATAM, STATIONARE, SOMAJT)
OLD_BASES = (["SAL", "SPOR", "CUMUL", "NOCIV", "NOAPTE", "SARB", "SUPL", "CO", "PREMIU"],
             ["SAL", "MINIM", "SPOR", "CUMUL", "NOCIV", "NOAPTE", "SARB", "SUPL", "CO", "PREMIU"],
             ["SAL", "MINIM", "SPOR", "CUMUL", "ORE", "NOCIV", "NOAPTE", "SARB", "SUPL", "CO", "PREMIU"],
             ["SAL", "ACORD", "ACORDP", "MINIM", "SPOR", "CUMUL", "ORE", "NOCIV", "NOAPTE", "SARB", "SUPL", "CO", "PREMIU"])


def run():
    # avansul se scade singur din plățile de avans ale lunii (bazele create înainte de plată aveau „sumă fixă”)
    PayType.objects.filter(code="AVANS", is_system=True, formula="fixed").update(formula="auto", auto="advance")
    for code, name, value, unit, source, since in CONSTANTS:
        # pe (cod, dată): valoarea adoptată pentru anul următor se adaugă și la instalările existente
        PayConstant.objects.get_or_create(code=code, date_from=since, defaults={
            "name": name, "value": Decimal(value), "unit": unit, "source": source})
    for row in TYPES:
        (code, ro, ru, en, category, formula, auto, pct, base, scale, taxable, cas, cnam, ex_month, ex_avg, in_avg, ipc, sort) = row
        PayType.objects.get_or_create(code=code, defaults={
            "name_ro": ro, "name_ru": ru, "name_en": en, "category": category, "formula": formula, "auto": auto,
            "percent": Decimal(pct), "base_codes": base, "scale": scale, "taxable": taxable, "cas": cas, "cnam": cnam,
            "exempt_month": Decimal(ex_month), "exempt_avg_pct": Decimal(ex_avg), "in_average": in_avg, "ipc_code": ipc,
            "sort": sort, "is_system": True, "on_payslip": True})
    # completarea până la salariul minim, orele pe tipuri, acordul și timpul fără producție intră în baza sindicatului / pensiei alimentare — doar unde
    # baza e încă cea livrată
    for t in PayType.objects.filter(code__in=("SINDICAT", "PENSIE"), is_system=True):
        if t.base_codes in OLD_BASES:
            t.base_codes = [c for c in TYPES_BY_CODE[t.code][8]]
            t.save(update_fields=["base_codes"])


TYPES_BY_CODE = {row[0]: row for row in TYPES}
