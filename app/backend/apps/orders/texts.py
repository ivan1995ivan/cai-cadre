"""Textele punctelor „ORDON:” — câte unul pentru fiecare tip de ordin, completat din dosar și din parametri.

Textul se poate schimba în Administrare → Setări → Tipuri de ordine (câmpul „Textul punctului”) sau direct în ordin. Câmpurile
din acolade: {angajat}, {tab}, {functia}, {sectia}, {norma}, {salariul}, {sporuri}, {din}, {pana}, {zile}, {an_de},
{an_pana}, {motivul}, {destinatia}, {scopul}, {suma}, {suma_text}, {procent}, {sanctiunea}, {abaterea},
{fel}, {proba}, {termen}, {data}, {ore}, {suplinit}, {ordin_anulat}, {text}.
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
                    "pe perioada {din} – {pana}, cu plata de {procent}% din salariul de funcție.",
    "combination": "Se permite {angajat} cumularea funcției de {functia_noua}, {sectia}, {norma} normă, pe perioada {din} – "
                   "{pana}, cu plata de {procent}% din salariul de funcție.",
    "acting": "Se pune în sarcina {angajat} exercitarea interimatului funcției de {functia_noua} ({sectia}) pe perioada "
              "{din} – {pana}, cu plata diferenței de salariu.",
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
        "suplinit": f", pe durata absenței {p['substituted_name']}" if p.get("substituted_name") else "",
        "compensare": f" și compensația pentru {p['compensation_days']} zile de concediu nefolosit" if p.get("compensation_days") else "",
        "amanare": (f", planificat de la {_d(p['planned_from'])}, pentru perioada {_d(p.get('date_from'))} – {_d(p.get('date_to'))}"
                    if p.get("planned_from") and p.get("date_to") else
                    f", cu începere de la {_d(p.get('date_from'))}" if p.get("date_from") else ""),
        "ordin_anulat": p.get("cancelled_label") or "", "text": p.get("text") or "", "data": _d(item.order.date),
    })
    return ctx


def point_text(item) -> str:
    ot = item.order.order_type
    template = ot.point_template_ro or DEFAULT_POINTS.get(ot.code) or "{text}"
    try:
        text = template.format_map(context(item))
    except (KeyError, ValueError, IndexError) as exc:
        return f"[Textul-model are o greșeală: {exc}] " + (item.params or {}).get("text", "")
    return " ".join(text.split())
