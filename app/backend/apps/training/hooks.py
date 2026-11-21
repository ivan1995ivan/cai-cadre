"""Legăturile formării cu celelalte module: alerta certificatelor care expiră, efectul ordinului de perfecționare, rapoartele."""


def register():
    from apps.alerts import engine
    from apps.orders import effects
    from apps.reports import registry

    from . import reports, services  # noqa: F401 — rapoartele se înregistrează la import

    engine.register("training_expiry", True, 60, ("hr", "head"), services.expiry_alerts)
    effects.CODE_EFFECTS["training"] = (services.training_effect, services.undo_training_effect)
    registry.GROUPS.setdefault("training", ("Formarea profesională", "Обучение персонала", "Staff training"))
