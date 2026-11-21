"""„Din ce se calculează”: textul (RO / RU / EN) al fiecărui tip de calcul, ca baza să fie vizibilă și la tipurile automate."""
import re
from decimal import Decimal

# regula motorului (apps.payroll.engine) pentru fiecare cheie „auto”
AUTO_HOW = {
    "salary": ("salariul de funcție × norma raportului × orele lucrate / norma lunii (orele obișnuite + cele de sărbătoare în "
               "limita normei); la modalitatea „tarif orar” — tariful orar × orele lucrate; la „pe tipuri de ore” — nu se calculează",
               "оклад × ставка × отработанные часы / норма месяца (обычные + праздничные в пределах нормы); при способе «почасовой "
               "тариф» — тариф × отработанные часы; при «по видам часов» — не начисляется",
               "base salary × rate × hours worked / monthly norm (regular hours + holiday hours within the norm); for the “hourly "
               "rate” mode — hourly rate × hours worked; for “by hour types” — not calculated"),
    "allowance": ("SalariuFunctie × partea lucrată × sporul fix (%) din raportul de muncă",
                  "SalariuFunctie × отработанная доля × постоянная надбавка (%) из трудового отношения",
                  "SalariuFunctie × worked share × fixed allowance (%) of the employment"),
    "combination": ("cumularea funcțiilor / suplinirea de pe raportul de muncă (CM art. 156): % din salariul propriu sau al "
                    "funcției cumulate × partea lucrată × zilele în vigoare; suma fixă × zilele în vigoare; pe ore — orele tipului × "
                    "tariful",
                    "совмещение / замещение в трудовом отношении (ТК ст. 156): % от своего оклада или оклада совмещаемой "
                    "должности × отработанная доля × дни действия; фиксированная сумма × дни действия; почасово — часы вида × "
                    "тариф",
                    "combining posts / substitution on the employment (LC art. 156): % of own salary or of the combined post × "
                    "worked share × days in force; fixed amount × days in force; hourly — hours of the type × rate"),
    "hour_types": ("pe fiecare tip de ore cu tarif pe raport: ore plătite × tariful, ore plătite = max(efective; garantate × "
                   "zilele disponibile / zilele lucrătoare ale lunii) — la modalitățile „pe tipuri de ore” și „mixt”",
                   "по каждому виду часов с тарифом: оплачиваемые часы × тариф, оплачиваемые = max(фактические; гарантированные × "
                   "доступные дни / рабочие дни месяца) — при способах «по видам часов» и «смешанный»",
                   "for each hour type with a rate: paid hours × rate, paid = max(actual; guaranteed × available days / working "
                   "days of the month) — for the “by hour types” and “mixed” pay modes"),
    "night": ("tariful orar × orele de noapte × C.night_pct % (CM art. 159)",
              "часовой тариф × ночные часы × C.night_pct % (КТ ст. 159)",
              "hourly rate × night hours × C.night_pct % (LC art. 159)"),
    "holiday": ("tariful orar × (orele în limita normei × C.holiday_pct % + peste normă × C.holiday_over_norm_pct %), CM art. 158; "
                "la tariful pe oră — până la C.holiday_hourly_pct % din tarif",
                "часовой тариф × (часы в пределах нормы × C.holiday_pct % + сверх нормы × C.holiday_over_norm_pct %), КТ ст. 158; "
                "при почасовой оплате — до C.holiday_hourly_pct % тарифа",
                "hourly rate × (hours within the norm × C.holiday_pct % + over the norm × C.holiday_over_norm_pct %), LC art. 158; "
                "at an hourly rate — up to C.holiday_hourly_pct % of the rate"),
    "overtime": ("tariful orar × (primele 2 ore pe zi × C.overtime_first_pct % + restul × C.overtime_next_pct %), CM art. 157",
                 "часовой тариф × (первые 2 часа в день × C.overtime_first_pct % + остальные × C.overtime_next_pct %), КТ ст. 157",
                 "hourly rate × (first 2 hours a day × C.overtime_first_pct % + the rest × C.overtime_next_pct %), LC art. 157"),
    "leave": ("media zilnică (tipurile „intră în medie” din ultimele C.leave_avg_months luni / zilele lor, HG 426/2004) × zilele "
              "de concediu",
              "среднедневной заработок (виды «входит в средний» за последние C.leave_avg_months мес. / их дни, ПП 426/2004) × "
              "дни отпуска",
              "average daily pay (types “in the average” over the last C.leave_avg_months months / their days, GD 426/2004) × "
              "leave days"),
    "leave_comp": ("media zilnică (ca la concediu) × zilele compensate", "среднедневной заработок (как для отпуска) × "
                   "компенсируемые дни", "average daily pay (as for leave) × compensated days"),
    "sick": ("C.sick_employer_pct % × venitul mediu zilnic (C.sick_avg_months luni, plafon C.sick_avg_cap_salaries salarii "
             "medii) × primele C.sick_employer_days zile ale certificatului, cel mult C.sick_employer_year_days pe an (Legea 289/2004)",
             "C.sick_employer_pct % × среднедневной доход (C.sick_avg_months мес., потолок C.sick_avg_cap_salaries средних зарплат) "
             "× первые C.sick_employer_days дней листка, не более C.sick_employer_year_days в год (Закон 289/2004)",
             "C.sick_employer_pct % × average daily income (C.sick_avg_months months, cap C.sick_avg_cap_salaries average wages) "
             "× the first C.sick_employer_days days of the certificate, at most C.sick_employer_year_days a year (Law 289/2004)"),
    "sick_accident": ("C.sick_accident_pct % × venitul mediu zilnic × primele C.sick_accident_days zile (în afara plafonului anual)",
                      "C.sick_accident_pct % × среднедневной доход × первые C.sick_accident_days дней (вне годового лимита)",
                      "C.sick_accident_pct % × average daily income × the first C.sick_accident_days days (outside the yearly cap)"),
    "min_wage": ("salariul minim × norma × partea lucrată − salariul de funcție plătit (CM art. 131 alin. (3)), dacă e mai mare",
                 "минимальная зарплата × ставка × отработанная доля − выплаченный оклад (КТ ст. 131 ч. (3)), если больше",
                 "minimum wage × rate × worked share − base salary paid (LC art. 131(3)), if higher"),
    "bonus": ("suma sau % din SalariuFunctie din ordinele de premiere ale lunii", "сумма или % от SalariuFunctie из приказов о премировании месяца",
              "amount or % of SalariuFunctie from the month's bonus orders"),
    "aid": ("suma sau % din SalariuFunctie din ordinele de ajutor material ale lunii",
            "сумма или % от SalariuFunctie из приказов о материальной помощи месяца",
            "amount or % of SalariuFunctie from the month's financial aid orders"),
    "advance": ("avansurile plătite în lună (îndreptările spre plată de avans)", "выплаченные в месяце авансы (ведомости аванса)",
                "advances paid in the month (advance payment documents)"),
    "income_tax": ("C.income_tax_pct % × (baza impozitului − CNAM − scutirile lunii), la plată",
                   "C.income_tax_pct % × (налоговая база − ОМС − льготы месяца), при выплате",
                   "C.income_tax_pct % × (tax base − health insurance − the month's exemptions), at payment"),
    "cnam": ("C.cnam_employee_pct % × baza CNAM, la plată", "C.cnam_employee_pct % × база ОМС, при выплате",
             "C.cnam_employee_pct % × health insurance base, at payment"),
    "cas": ("C.cas_employer_pct % × baza CAS (acumulările cu „CAS”)", "C.cas_employer_pct % × база соцстраха (начисления с «CAS»)",
            "C.cas_employer_pct % × social insurance base (accruals marked “CAS”)"),
    "cas_min": ("C.cas_employer_pct % × (salariul minim × timpul lucrat − baza CAS reală), Legea 489/1999 art. 22",
                "C.cas_employer_pct % × (минимальная зарплата × отработанное время − фактическая база), Закон 489/1999 ст. 22",
                "C.cas_employer_pct % × (minimum wage × time worked − actual CAS base), Law 489/1999 art. 22"),
    "none": ("—", "—", "—"),
}

LANGS = ("ro", "ru", "en")


def _pct(value) -> str:
    d = Decimal(value or 0)
    text = format(d, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text.replace(".", ",")


def _names(codes, names: dict, lang: int) -> str:
    out = []
    for c in codes:
        n = names.get(c)
        out.append(f"{c} {n[lang] or n[0]}" if n else c)
    return " + ".join(out)


def how(t, names: dict, const=None) -> dict:
    """{ro, ru, en}: din ce se calculează tipul `t`. `names` = {cod: (denumirea RO, RU, EN)} pentru baza de calcul;
    `const(cod)` — valoarea constantei în vigoare: în regula unui tip automat `C.<cod>` se înlocuiește cu ea."""
    out = {}
    for i, lang in enumerate(LANGS):
        base = _names(t.base_codes or [], names, i)
        rows = ("din rândul angajatului", "из строки сотрудника", "from the employee's row")[i]
        if t.formula == "auto":
            text = AUTO_HOW.get(t.auto, AUTO_HOW["none"])[i]
            if const is not None:
                text = re.sub(r"C\.([a-z0-9_]+)", lambda m: _pct(const(m.group(1))), text)
        elif t.formula == "fixed":
            text = ("suma pe lună " + rows, "сумма в месяц " + rows, "monthly amount " + rows)[i]
        elif t.formula == "pct_salary":
            text = (f"SalariuFunctie × partea lucrată × procentul ({rows}; implicit {_pct(t.percent)} %)",
                    f"SalariuFunctie × отработанная доля × процент ({rows}; по умолчанию {_pct(t.percent)} %)",
                    f"SalariuFunctie × worked share × percent ({rows}; default {_pct(t.percent)} %)")[i]
        elif t.formula == "pct_base":
            text = (f"baza × procentul ({rows}; implicit {_pct(t.percent)} %); baza: {base or '—'}",
                    f"база × процент ({rows}; по умолчанию {_pct(t.percent)} %); база: {base or '—'}",
                    f"base × percent ({rows}; default {_pct(t.percent)} %); base: {base or '—'}")[i]
        elif t.formula == "hourly":
            text = ("tariful pe oră din rândul angajatului × orele lucrate (+ sporul pentru suplimentare și pentru sărbători)",
                    "часовой тариф из строки сотрудника × отработанные часы (+ доплата за сверхурочные и праздничные)",
                    "hourly rate from the employee's row × hours worked (+ overtime and holiday premium)")[i]
        elif t.formula == "scale":
            steps = ", ".join(f"{_pct(s.get('from'))}+ — {_pct(s.get('pct'))} %" for s in sorted(t.scale or [], key=lambda s: float(s.get("from", 0))))
            base = base or _names(["SAL"], names, i)
            text = (f"baza × % treptei de vechime totală ({steps or '—'}); baza: {base}",
                    f"база × % ступени общего стажа ({steps or '—'}); база: {base}",
                    f"base × % of the total service step ({steps or '—'}); base: {base}")[i]
        elif t.formula == "expr":
            text = (f"formula: {t.expression or '—'}", f"формула: {t.expression or '—'}", f"formula: {t.expression or '—'}")[i]
            if t.base_codes:
                text += ("; Baza: ", "; Baza (база): ", "; Baza (base): ")[i] + base
        else:
            text = "—"
        if t.formula != "auto" and t.applies_to == "all":
            text += ("; pentru toți angajații", "; для всех сотрудников", "; for all employees")[i]
        out[lang] = text
    return out
