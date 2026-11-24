"""Textele punctelor „ORDON:” — câte unul pentru fiecare tip de ordin, completat din dosar și din parametri.

Textul se poate schimba în Administrare → Setări → Tipuri de ordine (câmpul „Textul punctului”) sau direct în ordin. Câmpurile
din acolade: {angajat}, {tab}, {functia}, {sectia}, {norma}, {salariul}, {sporuri}, {din}, {pana}, {zile}, {an_de},
{an_pana}, {motivul}, {destinatia}, {scopul}, {suma}, {suma_text}, {procent}, {sanctiunea}, {abaterea},
{fel}, {proba}, {termen}, {data}, {ore}, {suplinit}, {cum}, {plata}, {cauza}, {plata_timp}, {ordin_anulat}, {text}, {acumulari}, {tarife}. Tabelul „Acumulări și rețineri”
({acumulari}) se adaugă la sfârșitul punctului dacă textul-model nu îl are.
"""
from collections import defaultdict
from decimal import Decimal

DEFAULT_POINTS = {
    "hire": "Se angajează {angajat} în funcția de {functia}, {sectia}, {norma} normă, {fel}, cu salariul de funcție de "
            "{salariul} lei{sporuri}, începând cu {din}{termen}{proba}.",
    "hire_transfer": "Se angajează prin transfer {angajat} în funcția de {functia}, {sectia}, {norma} normă, cu salariul de "
                     "funcție de {salariul} lei{sporuri}, începând cu {din}.",
    "transfer": "Se transferă {angajat} (nr. de tabel {tab}) în funcția de {functia}, {sectia}, {norma} normă, cu salariul de "
                "funcție de {salariul} lei{sporuri}, începând cu {din}.",
    "change_rate": "Se stabilește {angajat} (nr. de tabel {tab}), {functia}, {sectia}, norma de {norma} începând cu {din}.",
    "change_terms": "Se modifică contractul individual de muncă al {angajat} (nr. de tabel {tab}), {functia}, {sectia}, "
                    "începând cu {din}: {text}.",
    "extend_contract": "Se prelungește contractul individual de muncă al {angajat} (nr. de tabel {tab}), {functia}, {sectia}, "
                       "până la {pana}.",
    "substitution": "Se pune în sarcina {angajat}, {functia}, suplinirea temporară a funcției de {functia_noua} ({sectia}){suplinit} "
                    "{cum}pe perioada {din} – {pana}, cu {plata}.",
    "combination": "Se permite {angajat}, {functia}, cumularea funcției de {functia_noua}, {sectia}, {cum}pe perioada {din} – "
                   "{pana}, cu {plata}.",
    "acting": "Se pune în sarcina {angajat}, {functia}, exercitarea interimatului funcției de {functia_noua} ({sectia}) {cum}pe "
              "perioada {din} – {pana}, cu {plata}.",
    "travel": "Se deleghează {angajat}, {functia}, {sectia}, la {destinatia} pe perioada {din} – {pana} ({zile} zile), "
              "în scopul {scopul}, cu menținerea salariului mediu.",
    "suspend": "Se suspendă contractul individual de muncă al {angajat} (nr. de tabel {tab}), {functia}, {sectia}, începând "
               "cu {din}, în legătură cu {motivul}.",
    "resume": "Se consideră reluată activitatea {angajat} (nr. de tabel {tab}), {functia}, {sectia}, începând cu {din}.",
    "terminate": "Se eliberează din funcție {angajat} (nr. de tabel {tab}), {functia}, {sectia}, la {din}, în temeiul: "
                 "{motivul}. Contabilitatea va efectua calculul definitiv{compensare}.",
    "cancel_order": "Se anulează ordinul nr. {ordin_anulat}.",
    "leave_annual": "Se acordă concediul de odihnă anual plătit {angajat} (nr. de tabel {tab}), {functia}, {sectia}, de "
                    "{zile} zile calendaristice, de la {din} până la {pana}, pentru anul de muncă {an_de} – {an_pana}.",
    "leave_extra": "Se acordă concediul de odihnă suplimentar plătit {angajat} (nr. de tabel {tab}), {functia}, {sectia}, "
                   "de {zile} zile calendaristice, de la {din} până la {pana}{motiv}.",
    "leave_unpaid": "Se acordă concediu neplătit {angajat} (nr. de tabel {tab}), {functia}, {sectia}, de {zile} zile "
                    "calendaristice, de la {din} până la {pana}{motiv}.",
    "leave_maternity": "Se acordă concediul de maternitate {angajat} (nr. de tabel {tab}), {functia}, {sectia}, de la {din} "
                       "până la {pana} ({zile} zile calendaristice), în baza certificatului medical.",
    "leave_paternity": "Se acordă concediul paternal {angajat} (nr. de tabel {tab}), {functia}, {sectia}, de {zile} zile "
                       "calendaristice, de la {din} până la {pana}.",
    "leave_childcare": "Se acordă concediul parțial plătit pentru îngrijirea copilului {angajat} (nr. de tabel {tab}), "
                       "{functia}, {sectia}, de la {din} până la {pana}.",
    "leave_childcare_unpaid": "Se acordă concediul suplimentar neplătit pentru îngrijirea copilului {angajat} (nr. de tabel "
                              "{tab}), {functia}, {sectia}, de la {din} până la {pana}.",
    "leave_study": "Se acordă concediul de studii {angajat} (nr. de tabel {tab}), {functia}, {sectia}, de {zile} zile "
                   "calendaristice, de la {din} până la {pana}{motiv}.",
    "days_off_paid": "Se acordă {angajat} (nr. de tabel {tab}), {functia}, {sectia}, {zile} zile libere plătite, de la {din} "
                     "până la {pana}{motiv}.",
    "leave_recall": "Se recheamă din concediu {angajat} (nr. de tabel {tab}), {functia}, {sectia}, începând cu {din}. Zilele "
                    "neutilizate ({zile}) se acordă ulterior.",
    "leave_postpone": "Se amână concediul de odihnă al {angajat} (nr. de tabel {tab}), {functia}, {sectia}{amanare}{motiv}.",
    "leave_compensation": "Se plătește {angajat} (nr. de tabel {tab}), {functia}, compensația pentru {zile} zile de concediu "
                          "nefolosit.",
    "schedule": "Se aprobă graficul de lucru {text}.",
    "rest_day_work": "Se antrenează la muncă în zi de odihnă / sărbătoare, la {din}, {angajat}, {functia}, {sectia}, cu "
                     "plata în mărime dublă{text}.",
    "overtime": "Se antrenează la muncă suplimentară {angajat}, {functia}, {sectia}, la {din}, {ore} ore, cu plata conform "
                "legislației.",
    "hours_change": "Se stabilește {angajat} (nr. de tabel {tab}), {functia}, {sectia}, începând cu {din}: {text}.",
    "idle": "Se declară staționare pentru {angajat} (nr. de tabel {tab}), {functia}, {sectia}, de la {din} până la {pana}, "
            "{cauza}; timpul de staționare {plata_timp}{motiv}.",
    "tech_unemployment": "Se instituie șomaj tehnic pentru {angajat} (nr. de tabel {tab}), {functia}, {sectia}, de la {din} "
                         "până la {pana}, cu plata {plata_timp}{motiv}.",
    "salary_set": "Se stabilește {angajat} (nr. de tabel {tab}), {functia}, {sectia}, salariul de funcție de {salariul} "
                  "lei{sporuri}, începând cu {din}.",
    "allowance": "Se stabilește {angajat} (nr. de tabel {tab}), {functia}, {sectia}, spor la salariu de {procent}%, "
                 "începând cu {din}{motiv}.",
    "bonus": "Se acordă premiu {angajat}, {functia}, {sectia}, {suma_text}{motiv}.",
    "material_aid": "Se acordă ajutor material {angajat}, {functia}, {sectia}, în sumă de {suma} lei{motiv}.",
    "indexation": "Se majorează salariul de funcție al {angajat}, {functia}, până la {salariul} lei, începând cu {din}.",
    "deduction": "Se reține din salariul {angajat} (nr. de tabel {tab}), {functia}, {sectia}, {suma_text}, începând cu "
                 "{din}{motiv}.",
    "sanction": "Pentru {abaterea}, se aplică {angajat} (nr. de tabel {tab}), {functia}, {sectia}, sancțiunea "
                "disciplinară „{sanctiunea}”.",
    "sanction_lift": "Se ridică înainte de termen sancțiunea disciplinară aplicată {angajat}, {functia}, {sectia}{motiv}.",
    "training": "Se trimite {angajat}, {functia}, {sectia}, la formare profesională la {destinatia}, pe perioada "
                "{din} – {pana}{scop}, cu menținerea salariului mediu.",
    "medical_exam": "Se trimite la examenul medical {angajat}, {functia}, {sectia}, până la {pana}{motiv}.",
    "staff_list": "Se aprobă statele de personal în vigoare de la {din}{text}.",
    "leave_schedule": "Se aprobă graficul concediilor de odihnă anuale {text}.",
    "appoint_responsible": "Se desemnează {angajat}, {functia}, {text}.",
    "free_text": "{text}",
}

KIND_TEXT = {"main": "funcție de bază", "main_student": "funcție de bază (student)", "internal": "prin cumul intern",
             "external": "prin cumul extern", "substitute": "pentru suplinire",
             "contractor": "prin contract de prestări servicii"}


def _fmt_money(value):
    try:
        value = Decimal(str(value))
    except Exception:  # noqa: BLE001
        return str(value or "")
    text = f"{value:,.2f}".replace(",", " ").replace(".", ",")
    return text[:-3] if text.endswith(",00") else text


def _fmt_rate(value):
    try:
        value = Decimal(str(value))
    except Exception:  # noqa: BLE001
        return str(value or "")
    return format(value.normalize(), "f").replace(".", ",")


def _d(value):
    from datetime import date

    if not value:
        return ""
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value)
        except ValueError:
            return value
    return value.strftime("%d.%m.%Y")


def _substituted(p: dict) -> str:
    """Pe cine suplinește: numele scris sau angajatul raportului ales."""
    if p.get("substituted_name"):
        return p["substituted_name"]
    if p.get("substitutes"):
        from apps.staff.models import Employment

        job = Employment.objects.filter(pk=p["substitutes"]).select_related("employee").first()
        return job.employee.full_name() if job else ""
    return ""


def context(item) -> dict:
    """Valorile pentru textul punctului: din parametri, apoi din raportul de muncă al angajatului."""
    from apps.org.models import DictItem, Occupation, Specialty, Subdivision

    p = item.params or {}
    emp, job = item.employee, item.employment
    if emp is not None and job is None:
        job = emp.main_employment()
    occ = Occupation.objects.filter(pk=p.get("occupation")).first() if p.get("occupation") else None
    sub = Subdivision.objects.filter(pk=p.get("subdivision")).first() if p.get("subdivision") else None
    order_code = item.order.order_type.code
    new_post = order_code in ("hire", "hire_transfer", "transfer", "salary_set", "change_rate", "indexation")
    functia = (occ.name_ro if occ and new_post else None) or (job.occupation.name_ro if job else "")
    sectia = (sub.name_ro if sub else None) or (job.subdivision.name_ro if job else "")
    salary = p.get("base_salary") if p.get("base_salary") not in (None, "") else (job.base_salary if job else "")
    allowance = p.get("allowance_pct") if p.get("allowance_pct") not in (None, "") else (job.allowance_pct if job else 0)
    rate = p.get("rate") if p.get("rate") not in (None, "") else (job.rate if job else 1)

    def dict_name(pk):
        obj = DictItem.objects.filter(pk=pk).first() if pk else None
        return obj.name_ro if obj else ""

    spec = Specialty.objects.filter(pk=p.get("specialty")).first() if p.get("specialty") else None
    amount = p.get("amount")
    percent = p.get("percent")
    ctx = defaultdict(str, {
        "angajat": emp.full_name() if emp else "", "tab": emp.tab_number if emp else "",
        "functia": functia, "sectia": sectia, "norma": _fmt_rate(rate), "salariul": _fmt_money(salary),
        "sporuri": f" și sporuri de {_fmt_rate(allowance)}%" if allowance and Decimal(str(allowance)) else "",
        "fel": KIND_TEXT.get(p.get("kind") or (job.kind if job else "main"), ""),
        "din": _d(p.get("date_from") or p.get("date")), "pana": _d(p.get("date_to")), "zile": p.get("days") or "",
        "an_de": _d(p.get("work_year_from")), "an_pana": _d(p.get("work_year_to")),
        "motivul": dict_name(p.get("reason")) if str(p.get("reason", "")).isdigit() else (p.get("reason") or ""),
        "motiv": f", {p['note']}" if p.get("note") else "",
        "destinatia": p.get("destination") or "", "scopul": p.get("purpose") or "",
        "scop": f", în scopul {p['purpose']}" if p.get("purpose") else "",
        "suma": _fmt_money(amount) if amount not in (None, "") else "",
        "procent": _fmt_rate(percent) if percent not in (None, "") else "",
        "suma_text": (f"în sumă de {_fmt_money(amount)} lei" if amount not in (None, "")
                      else f"în mărime de {_fmt_rate(percent)}% din salariul de funcție" if percent not in (None, "") else ""),
        "categoria": dict_name(p.get("category")).lower(), "specialitatea": spec.name_ro if spec else "",
        "sanctiunea": dict_name(p.get("sanction")).lower(), "abaterea": p.get("misconduct") or "abaterea disciplinară",
        "functia_noua": (occ.name_ro if occ else functia), "ore": p.get("hours") or "",
        "termen": f", pe durată determinată până la {_d(p['date_to'])}" if p.get("date_to") and order_code in ("hire", "hire_transfer") else "",
        "proba": f", cu perioadă de probă până la {_d(p['probation_until'])}" if p.get("probation_until") else "",
        "suplinit": f", pe durata absenței {_substituted(p)}" if _substituted(p) else "",
        "compensare": f" și compensația pentru {p['compensation_days']} zile de concediu nefolosit" if p.get("compensation_days") else "",
        "amanare": (f", planificat de la {_d(p['planned_from'])}, pentru perioada {_d(p.get('date_from'))} – {_d(p.get('date_to'))}"
                    if p.get("planned_from") and p.get("date_to") else
                    f", cu începere de la {_d(p.get('date_from'))}" if p.get("date_from") else ""),
        "ordin_anulat": p.get("cancelled_label") or "", "text": p.get("text") or "", "data": _d(item.order.date),
        **combination_text(p, order_code),
        **idle_text(p, order_code),
    })
    if order_code in ("substitution", "combination", "acting") and job is not None and (p.get("mode") or "on_base") != "separate":
        ctx["functia"] = job.occupation.name_ro  # funcția de bază (cumularea e pe raportul de bază)
    return ctx


IDLE_CAUSE_TEXT = {"employer": "din vina angajatorului", "nobody": "fără vina angajatorului și a salariatului",
                   "worker": "din vina salariatului"}


def idle_text(p: dict, order_code: str) -> dict:
    """{cauza} și {plata_timp} la staționare (CM art. 80¹) și șomajul tehnic (CM art. 80): procentul scris în ordin sau cel
    legal după cauză."""
    if order_code not in ("idle", "tech_unemployment"):
        return {}
    pct = p.get("pay_pct")
    has_pct = pct not in (None, "")
    if order_code == "tech_unemployment":
        return {"cauza": "", "plata_timp": f"de {_fmt_rate(pct)}% din salariul de bază" if has_pct
                else "de cel puțin 50% din salariul de bază"}
    cause = p.get("cause") or "nobody"
    if cause == "worker" and not has_pct:
        return {"cauza": IDLE_CAUSE_TEXT[cause], "plata_timp": "nu se plătește"}
    if has_pct:
        paid = f"se plătește cu {_fmt_rate(pct)}% din salariul de bază" + (", dar nu mai puțin decât salariul minim pe oră"
                                                                if cause == "nobody" else "")
    else:
        paid = ("se plătește integral (100% din salariul de bază)" if cause == "employer"
                else "se plătește cu 2/3 din salariul de bază, dar nu mai puțin decât salariul minim pe oră")
    return {"cauza": IDLE_CAUSE_TEXT.get(cause, ""), "plata_timp": paid}


def combination_text(p: dict, order_code: str) -> dict:
    """{cum} și {plata} la cumularea funcțiilor / suplinire / interimat: pe același contract (CM art. 156) — plata după
    modalitate; ca raport separat — norma și salariul lui."""
    if order_code not in ("substitution", "combination", "acting"):
        return {"cum": "", "plata": ""}
    if (p.get("mode") or "on_base") == "separate":
        rate = p.get("rate") or "0.5"
        salary = p.get("base_salary")
        return {"cum": f"prin raport de muncă separat, {_fmt_rate(rate)} normă, ",
                "plata": f"salariul de funcție de {_fmt_money(salary)} lei" if salary not in (None, "") else "salariul funcției"}
    from apps.worktime.models import HourType

    value = p.get("value") if p.get("value") not in (None, "") else p.get("percent")
    v = _fmt_rate(value) if value not in (None, "") else "…"
    mode = p.get("pay_mode") or "pct_own"
    if mode == "pct_other":
        other = p.get("other_salary")
        plata = f"plata de {v}% din salariul funcției {'(' + _fmt_money(other) + ' lei)' if other not in (None, '') else 'cumulate'}"
    elif mode == "fixed":
        plata = f"plata suplimentară de {_fmt_money(value) if value not in (None, '') else '…'} lei pe lună"
    elif mode == "hourly":
        ht = HourType.objects.filter(pk=p.get("hour_type")).first() if p.get("hour_type") else None
        plata = f"plata de {_fmt_money(value) if value not in (None, '') else '…'} lei pe oră" + (f" ({ht.name_ro.lower()})" if ht else "")
    else:
        plata = f"plata de {v}% din salariul de funcție"
    return {"cum": "fără eliberare de la munca de bază, ", "plata": plata}


ACTIONS_TEXT = {"add": "se stabilește", "modify": "se modifică", "stop": "se oprește"}


def pay_items_text(item) -> str:
    """„Acumulări și rețineri: se stabilește NOCIV Spor … 10 % de la 01.03.2026; se oprește SINDICAT … de la …”."""
    from apps.payroll.models import PayType

    rows = (item.params or {}).get("pay_items") or []
    if not isinstance(rows, list):
        return ""
    types = {t.pk: t for t in PayType.objects.filter(pk__in=[r.get("pay_type") for r in rows if isinstance(r, dict)])}
    parts = []
    for r in rows:
        if not isinstance(r, dict) or r.get("pay_type") not in types:
            continue
        t = types[r["pay_type"]]
        action = r.get("action") or "add"
        words = [ACTIONS_TEXT.get(action, ""), t.name_ro.lower() if t.name_ro else t.code]
        if action != "stop":
            if r.get("amount") not in (None, ""):
                words.append(f"{_fmt_money(r['amount'])} lei")
            if r.get("percent") not in (None, ""):
                words.append(f"{_fmt_rate(r['percent'])}%")
            if r.get("quantity") not in (None, ""):
                words.append(f"× {_fmt_rate(r['quantity'])}")
        if r.get("date_from"):
            words.append(f"de la {_d(r['date_from'])}")
        if r.get("date_to"):
            words.append(f"până la {_d(r['date_to'])}")
        if r.get("document"):
            words.append(f"({r['document']})")
        parts.append(" ".join(w for w in words if w))
    return ("Acumulări și rețineri: " + "; ".join(parts) + ".") if parts else ""


def hour_rates_text(item) -> str:
    """„Tarife pe tipuri de ore: se stabilește ore de zbor 350 lei pe oră, garantat 50 ore pe lună; …”."""
    from apps.worktime.models import HourType

    rows = (item.params or {}).get("hour_rates") or []
    if not isinstance(rows, list):
        return ""
    types = {t.pk: t for t in HourType.objects.filter(pk__in=[r.get("hour_type") for r in rows if isinstance(r, dict)])}
    parts = []
    for r in rows:
        if not isinstance(r, dict) or r.get("hour_type") not in types:
            continue
        ht = types[r["hour_type"]]
        action = r.get("action") or "add"
        words = [ACTIONS_TEXT.get(action, ""), "tariful pentru", ht.name_ro.lower()]
        if action != "stop":
            if r.get("rate") not in (None, ""):
                words.append(f"— {_fmt_money(r['rate'])} lei pe oră")
            if r.get("guaranteed_hours") not in (None, ""):
                words.append(f", garantat {_fmt_rate(r['guaranteed_hours'])} ore pe lună")
        if r.get("date_from"):
            words.append(f"de la {_d(r['date_from'])}")
        if r.get("date_to"):
            words.append(f"până la {_d(r['date_to'])}")
        parts.append(" ".join(w for w in words if w).replace(" ,", ","))
    return ("Tarife pe tipuri de ore: " + "; ".join(parts) + ".") if parts else ""


PAY_MODE_TEXT = {"hourly": "tarif orar", "hour_types": "pe tipuri de ore", "mixed": "salariu lunar și tarife pe tipuri de ore",
                 "piece": "în acord (după lucrările din rapoartele de producție)"}


def point_text(item) -> str:
    ot = item.order.order_type
    template = ot.point_template_ro or DEFAULT_POINTS.get(ot.code) or "{text}"
    p = item.params or {}
    mode = p.get("pay_mode")
    if mode in PAY_MODE_TEXT and ot.effect in ("hire", "change", "salary") and "{remunerare}" not in template:
        template = template + " {remunerare}"
    pay = pay_items_text(item)
    if pay and "{acumulari}" not in template:
        template = template + " {acumulari}"
    rates_text = hour_rates_text(item)
    if rates_text and "{tarife}" not in template:
        template = template + " {tarife}"
    try:
        ctx = context(item)
        ctx["acumulari"] = pay
        ctx["tarife"] = rates_text
        ctx["remunerare"] = (f"Modalitatea de remunerare: {PAY_MODE_TEXT[mode]}"
                             + (f", tariful orar {_fmt_money(p['hourly_rate'])} lei" if mode == "hourly" and p.get("hourly_rate") else "")
                             + (f", tariful orar al categoriei {_fmt_money(p['hourly_rate'])} lei" if mode == "piece" and p.get("hourly_rate")
                                else "")
                             + ".") if mode in PAY_MODE_TEXT else ""
        text = template.format_map(ctx)
    except (KeyError, ValueError, IndexError) as exc:
        return f"[Textul-model are o greșeală: {exc}] " + (item.params or {}).get("text", "")
    return " ".join(text.split())
