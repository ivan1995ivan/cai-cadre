"""Raportul sănătății și securității în muncă în catalogul general."""
from collections import Counter

from apps.reports.personnel import COMMON, _d
from apps.reports.registry import GROUPS, LINKS, Link, col, report, subtitle_parts

from . import services

GROUPS.setdefault("health", ("Sănătatea și securitatea în muncă", "Охрана здоровья и труда", "Occupational health and safety"))
WHAT_T = {"exam": ("Examenul medical", "Медосмотр", "Medical exam"), "briefing": ("Instructajul SSM", "Инструктаж по ОТ", "Safety briefing")}
STATUS_T = {"overdue": ("Depășit", "Просрочено", "Overdue"), "missing": ("Lipsește", "Нет записи", "Missing"),
            "due": ("Urmează", "Предстоит", "Due")}


@report("health_due", "health", ("Termenele sănătății în muncă", "Сроки охраны здоровья", "Occupational health deadlines"),
        ("Cine trebuie trimis la examenul medical periodic sau la instructajul SSM: termenele depășite, lipsă și cele din "
         "următoarele zile — lista pentru medicina muncii și pentru responsabilul SSM.",
         "Кого направить на медосмотр или инструктаж по охране труда: просроченные, отсутствующие и ближайшие сроки.",
         "Who is due for a medical exam or a safety briefing: overdue, missing and upcoming."),
        ["on_date", "subdivision"])
def health_due(p):
    rows = services.due_rows(p.on_date, p.sub_ids, None, p.lang)
    counts = Counter(r["what"] for r in rows)
    return {
        "subtitle": subtitle_parts(p, f"{p.t(('la data de', 'на', 'as of'))} {p.on_date:%d.%m.%Y}"),
        "columns": [col("tab", p.t(COMMON["tab"])), col("name", p.t(COMMON["name"])), col("sub", p.t(COMMON["sub"])),
                    col("occ", p.t(COMMON["occ"])), col("what", p.t(("Ce", "Что", "What"))),
                    col("last", p.t(("Ultima dată", "Последний раз", "Last")), "date"), col("due", p.t(("Termenul", "Срок", "Due")), "date"),
                    col("status", p.t(("Situația", "Состояние", "Status")))],
        "rows": [{"tab": r["tab"], "name": r["name"], "sub": r["subdivision"], "occ": r["occupation"],
                  "what": p.t(WHAT_T[r["what"]]), "last": _d(r["last"]), "due": _d(r["due"]),
                  "status": p.t(STATUS_T[r["status"]])} for r in rows],
        "summary": [{"label": p.t(WHAT_T[k]), "value": counts[k]} for k in ("exam", "briefing")],
    }


LINKS.append(Link("health_page", "health", ("Sănătatea și securitatea în muncă", "Охрана здоровья и труда", "Occupational health and safety"),
                  ("Examenele medicale, periodicitatea lor pe funcții, instructajul SSM, ordinul de trimitere la examen.",
                   "Медосмотры, их периодичность по должностям, инструктажи, приказ о направлении на медосмотр.",
                   "Medical exams, their periodicity by position, safety briefings."),
                  "/health", "health.view"))
