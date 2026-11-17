"""Treptele licenței (fără Django, ca să le folosească și tools/license_tool.py)."""

# Treptele licenței după numărul de utilizatori activi (cerut 2026-10-03): Start 1–5, Business 10–50, Corporate 100,
# Enterprise 500. Licența poartă treapta („plan”) și numărul exact de utilizatori; cele vechi (fără treaptă) o primesc
# după numărul de utilizatori.
class PlanError(ValueError):
    pass


PLANS = {
    "start": {"name": "Start", "min": 1, "max": 5},
    "business": {"name": "Business", "min": 10, "max": 50},
    "corporate": {"name": "Corporate", "min": 100, "max": 100},
    "enterprise": {"name": "Enterprise", "min": 500, "max": 500},
}


def plan_for(users: int) -> str:
    """Treapta în care intră numărul de utilizatori (pentru licențele fără treaptă)."""
    for key, plan in PLANS.items():
        if users <= plan["max"]:
            return key
    return "enterprise"


def check_plan(plan: str, users: int):
    """Instrumentul de emitere: treapta există și numărul de utilizatori intră în ea."""
    if plan not in PLANS:
        raise PlanError(f"Treapta „{plan}” nu există: {', '.join(PLANS)}.")
    p = PLANS[plan]
    if not p["min"] <= users <= p["max"]:
        limits = f"{p['min']}–{p['max']}" if p["min"] != p["max"] else str(p["max"])
        raise PlanError(f"Treapta {p['name']} este pentru {limits} utilizatori, nu {users}.")
