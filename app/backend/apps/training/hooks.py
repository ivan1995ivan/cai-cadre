"""Legăturile formării cu celelalte module: alerta creditelor, efectul ordinului de perfecționare, rapoartele."""
from datetime import timedelta


def credits_missing(today, days, cfg):
    from apps.alerts.engine import Alert, _d

    from . import services

    out = []
    for r in services.credits_rows(today):
        if r["expiry"] and today <= r["expiry"] <= today + timedelta(days=days) and r["credits"] < r["required"]:
            out.append(Alert("credits_missing", f"credits:{r['employee']}:{r['expiry']}", "Credite EMC insuficiente",
                             f"{r['name']} — {r['credits']:g} din {r['required']:g} credite; categoria expiră la {_d(r['expiry'])}",
                             r["expiry"], "warning", r["employee"], r["name"], {r["subdivision_id"]},
                             f"/employees/{r['employee']}?tab=education"))
    return out


def register():
    from apps.alerts import engine
    from apps.orders import effects
    from apps.reports import registry

    from . import reports, services  # noqa: F401 — rapoartele se înregistrează la import

    engine.register("credits_missing", True, 365, ("hr", "head"), credits_missing)
    effects.CODE_EFFECTS["training"] = (services.training_effect, services.undo_training_effect)
    registry.GROUPS.setdefault("training", ("Formare și atestare", "Обучение и аттестация", "Training and attestation"))
