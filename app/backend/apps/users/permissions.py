from rest_framework.permissions import BasePermission

METHOD_ACTIONS = {
    "GET": "view",
    "HEAD": "view",
    "OPTIONS": "view",
    "POST": "create",
    "PUT": "edit",
    "PATCH": "edit",
    "DELETE": "delete",
}
# acțiunile comune ale mai multor view-uri (scoaterea marcajului de ștergere cere dreptul de ștergere)
ACTION_DEFAULTS = {"unmark": "delete"}


class RolePermission(BasePermission):
    """Verifică drepturile din rolurile utilizatorului.

    În view se declară:
        perm_module = "users"                 – dreptul se deduce din metoda HTTP
        perm_module = ("catalog", "purchases") – ajunge dreptul din oricare modul
        perm_actions = {"approve": "approve"} – acțiune DRF (@action) → acțiune drept
        public = True                         – fără autentificare
    Fără perm_module ajunge ca utilizatorul să fie autentificat.
    """

    message = "Nu aveți drept pentru această acțiune."

    def has_permission(self, request, view):
        if getattr(view, "public", False):
            return True
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        module = getattr(view, "perm_module", None)
        if not module:
            return True
        action = None
        drf_action = getattr(view, "action", None)
        if drf_action:
            action = getattr(view, "perm_actions", {}).get(drf_action) or ACTION_DEFAULTS.get(drf_action)
        action = action or METHOD_ACTIONS.get(request.method, "view")
        modules = module if isinstance(module, (tuple, list)) else (module,)
        return any(user.has_crm_perm(f"{m}.{action}") for m in modules)


def require(user, code: str):
    from rest_framework.exceptions import PermissionDenied

    if not user.has_crm_perm(code):
        raise PermissionDenied(RolePermission.message)
