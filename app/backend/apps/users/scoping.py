"""Filtrarea înregistrărilor după nivelul de acces al rolului („doar ale mele / ale echipei / toate”)."""


def scope_queryset(qs, user, module: str, owner_field: str = "manager"):
    """Rândurile vizibile: toate, sau ale lui și ale agenților pe care îi vede (supervizorul — echipa lui)."""
    ids = user.agent_ids(module)
    if ids is None:
        return qs
    if len(ids) == 1:
        return qs.filter(**{owner_field: user})
    return qs.filter(**{f"{owner_field}__in": ids})


def can_access(obj, user, module: str, owner_field: str = "manager_id") -> bool:
    ids = user.agent_ids(module)
    return ids is None or getattr(obj, owner_field) in ids
