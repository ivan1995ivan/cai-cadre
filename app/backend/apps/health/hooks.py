"""Alertele sănătății în muncă și raportul din catalog."""

TITLES = {"exam": ("medical_exam_due", "Examenul medical periodic"), "briefing": ("briefing_due", "Instructajul SSM"),
          "vaccine": ("vaccination_due", "Vaccinarea")}


def _alerts(what):
    def collect(today, days, cfg):
        from apps.alerts.engine import Alert, _d

        from . import services

        kind, title = TITLES[what]
        out = []
        for r in services.due_rows(today, what=what, horizon=days):
            if r["status"] == "missing":
                continue  # lipsa totală se vede în pagina „Sănătatea în muncă”, nu umple alertele zilnic
            due = r["due"] or today
            when = f"termenul {_d(r['due'])}" if r["due"] else "nu este înregistrat"
            out.append(Alert(kind, f"{kind}:{r['employee']}:{r['label']}:{r['due']}", title,
                             f"{r['name']} — {r['label']}: {when}", due, "warning" if r["status"] == "overdue" else "task",
                             r["employee"], r["name"], {r["subdivision_id"]}, f"/employees/{r['employee']}?tab=health"))
        return out
    return collect


def register():
    from apps.alerts import engine

    from . import reports  # noqa: F401

    engine.register("medical_exam_due", True, 30, ("hr", "head"), _alerts("exam"))
    engine.register("briefing_due", True, 14, ("hr", "head"), _alerts("briefing"))
    engine.register("vaccination_due", True, 30, ("hr",), _alerts("vaccine"))

