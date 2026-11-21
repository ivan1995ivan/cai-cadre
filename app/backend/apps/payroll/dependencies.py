"""Dependențele dintre tipurile de calcul și ordinea lor în motor.

Un tip depinde de tipurile din baza lui (`base_codes`: la „% din bază”, la treptele de vechime — implicit SAL — și la formulă,
pentru variabila `Baza`) și de cele scrise ca `[COD]` în formulă. Motorul calculează întâi tipurile automate, apoi
completarea până la minim, apoi celelalte în ordine topologică: un tip după toate tipurile de care depinde. O dependență
circulară se respinge la salvarea tipului (și oprește calculul, dacă ar ajunge totuși în bază).
"""
import heapq

from rest_framework.exceptions import ValidationError

from . import formula

# tipurile automate calculate DUPĂ formule (CAS pe bazele lunii) sau la plată (impozitul, CNAM, avansul): nu pot fi în baza
# sau în formula altui tip — ar da mereu 0
LATE_AUTOS = ("cas", "cas_min", "income_tax", "cnam", "advance")
FIRST = ("fixed", "pct_salary", "hourly")  # fără dependențe: se calculează primele (și sporurile din tariful orar)
CATEGORY_ORDER = {"accrual": 0, "deduction": 1, "employer": 2}


def deps_of(t) -> list:
    """Codurile tipurilor de care depinde tipul `t` (în ordinea scrierii, fără repetări)."""
    codes = []
    if t.formula in ("pct_base", "expr"):
        codes += list(t.base_codes or [])
    elif t.formula == "scale":
        codes += list(t.base_codes or ["SAL"])
    if t.formula == "expr":
        codes += formula.references(t.expression)
    return list(dict.fromkeys(codes))


def find_cycle(graph: dict, start: str):
    """Drumul de la `start` înapoi la el (lista codurilor) sau None. `graph` = {cod: [coduri de care depinde]}."""
    stack = [(start, [start])]
    seen = set()
    while stack:
        node, path = stack.pop()
        for nxt in graph.get(node, []):
            if nxt == start:
                return path + [start]
            if nxt not in seen and nxt in graph:
                seen.add(nxt)
                stack.append((nxt, path + [nxt]))
    return None


def cycle_text(path) -> str:
    return "Dependență circulară: " + " → ".join(path)


def calc_order(types) -> list:
    """Tipurile care nu sunt automate, în ordinea de calcul (topologic; la egalitate: întâi cele fără dependențe, apoi
    categoria, ordinea din clasificator, codul)."""
    by_code = {t.code: t for t in types if t.formula != "auto"}
    graph = {code: [d for d in deps_of(t) if d in by_code] for code, t in by_code.items()}
    waiting = {code: len(set(deps)) for code, deps in graph.items()}
    users = {code: [] for code in by_code}
    for code, deps in graph.items():
        for d in set(deps):
            users[d].append(code)

    def key(code):
        t = by_code[code]
        return (0 if t.formula in FIRST else 1, CATEGORY_ORDER.get(t.category, 9), t.sort, t.code)

    ready = [key(c) for c, n in waiting.items() if n == 0]
    heapq.heapify(ready)
    out = []
    while ready:
        code = heapq.heappop(ready)[-1]
        out.append(by_code[code])
        for u in users[code]:
            waiting[u] -= 1
            if waiting[u] == 0:
                heapq.heappush(ready, key(u))
    if len(out) < len(by_code):
        left = sorted(c for c in by_code if waiting[c] > 0)
        path = next((p for p in (find_cycle(graph, c) for c in left) if p), left)
        raise ValidationError({"detail": cycle_text(path) + ". Corectați baza / formula tipurilor de calcul."})
    return out


def users_of(code: str, types, exclude=None) -> list:
    """Tipurile care îl folosesc pe `code` în bază sau în formulă."""
    return [t for t in types if t.pk != exclude and code in deps_of(t)]
