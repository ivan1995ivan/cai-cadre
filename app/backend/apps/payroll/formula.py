"""Formula tipului de calcul: o expresie sigură, fără cod Python.

Sintaxa (pentru utilizatorii din Moldova):
- numerele cu `.` sau `,` zecimal (`1,5` = `1.5`); argumentele funcțiilor se despart cu `;`;
- operatorii `+ - * / ( )`, comparațiile `< <= > >= = <>`, `și` / `sau` (și `and` / `or`);
- funcțiile `min`, `max`, `round(x; n)` (rotunjire comercială), `abs`, `daca(condiție; da; nu)` (și `if`);
- variabilele din `VARIABLES` (fără diacritice, nu contează literele mari / mici), `C.<cod>` — constanta salariului după cod,
  `[COD]` — suma deja calculată a altui tip de calcul în același rând.

Cum: textul se împarte în atomi (cu poziția fiecăruia în textul utilizatorului), se traduce în sintaxa Python, se citește
cu `ast` și se verifică după o listă albă de noduri; apoi arborele se evaluează de mână, în `Decimal`. Nu se folosește
`eval` / `compile`; numele, apelurile și indicii permiși sunt doar cei de mai jos.
"""
import ast
import re
from decimal import ROUND_HALF_UP, Decimal, DivisionByZero, InvalidOperation

MAX_LENGTH = 1000
MAX_DEPTH = 30
MAX_NODES = 300

# numele variabilei → descrierea (RO, RU, EN) pentru editorul formulei
VARIABLES = {
    "SalariuFunctie": ("Salariul de funcție pentru norma raportului de muncă (salariul × norma)",
                       "Оклад за ставку трудового отношения (оклад × ставка)",
                       "Base salary for the employment's rate (salary × rate)"),
    "Norma": ("Norma de ore a lunii pentru raport", "Норма часов месяца по трудовому отношению", "Monthly hours norm of the employment"),
    "OreLucrate": ("Orele lucrate în lună (pontajul)", "Отработанные часы за месяц (табель)", "Hours worked in the month (timesheet)"),
    "ZileLucrate": ("Zilele lucrate în lună (pontajul)", "Отработанные дни за месяц (табель)", "Days worked in the month (timesheet)"),
    "ZileNorma": ("Zilele lucrătoare ale lunii după calendar (cât e activ raportul)",
                  "Рабочие дни месяца по календарю (пока действует отношение)",
                  "Working days of the month by calendar (while the employment is active)"),
    "TarifOrar": ("Tariful pe oră: SalariuFunctie / Norma", "Часовой тариф: SalariuFunctie / Norma", "Hourly rate: SalariuFunctie / Norma"),
    "ParteLucrata": ("Partea lucrată din normă (0…1), ca la salariul de funcție",
                     "Отработанная доля нормы (0…1), как у оклада", "Worked share of the norm (0…1), as for the base salary"),
    "OreNoapte": ("Orele de noapte (22:00–06:00)", "Ночные часы (22:00–06:00)", "Night hours (22:00–06:00)"),
    "OreSarbatoare": ("Orele în zilele de sărbătoare și de repaus (în limita normei + peste normă)",
                      "Часы в праздничные и выходные дни (в пределах нормы + сверх нормы)",
                      "Hours on public holidays and rest days (within the norm + over it)"),
    "OreOdihna": ("Din acestea — orele în zilele de repaus după grafic", "Из них — часы в выходные дни по графику",
                  "Of which — hours on scheduled rest days"),
    "OreSarbatoareInNorma": ("Orele de sărbătoare / repaus în limita normei lunare", "Праздничные / выходные часы в пределах месячной нормы",
                             "Holiday / rest-day hours within the monthly norm"),
    "OreSarbatoarePesteNorma": ("Orele de sărbătoare / repaus peste norma lunară", "Праздничные / выходные часы сверх месячной нормы",
                                "Holiday / rest-day hours over the monthly norm"),
    "OreSuplim2": ("Orele suplimentare: primele 2 ore pe zi (CM art. 157)", "Сверхурочные: первые 2 часа в день (КТ ст. 157)",
                   "Overtime: the first 2 hours a day (LC art. 157)"),
    "OreSuplimPeste": ("Orele suplimentare: următoarele (peste primele 2 pe zi)", "Сверхурочные: последующие (сверх первых 2 в день)",
                       "Overtime: the following hours (over the first 2 a day)"),
    "Suma": ("Suma din rândul angajatului (fila „Salariu”, ordinul, documentul)", "Сумма из строки сотрудника (вкладка «Зарплата», приказ, документ)",
             "Amount from the employee's row (Pay tab, order, document)"),
    "Procent": ("Procentul din rândul angajatului (gol — procentul tipului)", "Процент из строки сотрудника (пусто — процент вида)",
                "Percent from the employee's row (empty — the type's percent)"),
    "Cantitate": ("Cantitatea din rândul angajatului (ore, zile, bucăți)", "Количество из строки сотрудника (часы, дни, штуки)",
                  "Quantity from the employee's row (hours, days, pieces)"),
    "Baza": ("Suma tipurilor din „Baza de calcul” a acestui tip", "Сумма видов из «Базы расчёта» этого вида",
             "Sum of the types in this type's calculation base"),
    "SalariuMinim": ("Salariul minim pe țară (constanta min_salary)", "Минимальная зарплата по стране (константа min_salary)",
                     "National minimum wage (constant min_salary)"),
    "SalariuMediu": ("Salariul mediu lunar pe economie prognozat (avg_salary)", "Прогнозная средняя зарплата по экономике (avg_salary)",
                     "Forecast average monthly wage (avg_salary)"),
    "NormaRaport": ("Norma raportului de muncă (1; 0,5; 0,25…)", "Ставка трудового отношения (1; 0,5; 0,25…)",
                    "Employment rate (1; 0.5; 0.25…)"),
    "VechimeAni": ("Vechimea totală în muncă, ani întregi (la sfârșitul lunii)", "Общий трудовой стаж, полных лет (на конец месяца)",
                   "Total length of service, whole years (at month end)"),
    "VechimeIntreprindereAni": ("Vechimea în întreprindere, ani întregi (la sfârșitul lunii)", "Стаж на предприятии, полных лет (на конец месяца)",
                                "Length of service in the company, whole years (at month end)"),
}

FUNCTIONS = {
    "min": ("min(a; b; …) — cel mai mic", "min(a; b; …) — наименьшее", "min(a; b; …) — the smallest"),
    "max": ("max(a; b; …) — cel mai mare", "max(a; b; …) — наибольшее", "max(a; b; …) — the largest"),
    "round": ("round(x; n) — rotunjirea comercială la n zecimale (implicit 0)", "round(x; n) — коммерческое округление до n знаков (по умолчанию 0)",
              "round(x; n) — commercial rounding to n decimals (default 0)"),
    "abs": ("abs(x) — valoarea absolută", "abs(x) — модуль", "abs(x) — absolute value"),
    "daca": ("daca(condiție; da; nu) — după condiție (și „if”)", "daca(условие; да; нет) — по условию (и «if»)",
             "daca(condition; yes; no) — by condition (also “if”)"),
}
ARITY = {"min": (1, 20), "max": (1, 20), "round": (1, 2), "abs": (1, 1), "daca": (3, 3)}
_FUNC_ALIASES = {"min": "min", "max": "max", "round": "round", "abs": "abs", "daca": "daca", "dacă": "daca", "if": "daca"}
_LOGIC = {"și": "and", "si": "and", "şi": "and", "and": "and", "sau": "or", "or": "or"}
_VAR_BY_LOWER = {v.lower(): v for v in VARIABLES}
REF, CONST = "_ref", "_const"  # numele interne (utilizatorul nu poate scrie „_”)

_TOKEN = re.compile(r"""
    (?P<space>\s+)
  | (?P<number>\d+(?:[.,]\d+)?)
  | (?P<const>C\.(?P<ccode>[A-Za-z0-9_]+))
  | (?P<ref>\[(?P<rcode>[^\[\]]*)\])
  | (?P<name>[A-Za-zĂÂÎȘȚŞŢăâîșțşţ][A-Za-z0-9_ĂÂÎȘȚŞŢăâîșțşţ]*)
  | (?P<op><=|>=|<>|==|!=|[-+*/()<>=;])
""", re.VERBOSE)


class FormulaError(Exception):
    """Eroarea formulei cu poziția ei în textul utilizatorului (de la 1)."""

    def __init__(self, message: str, position: int | None = None):
        self.message, self.position = message, position
        super().__init__(self.text())

    def text(self) -> str:
        return f"{self.message} (poziția {self.position})" if self.position else self.message


def fmt(value) -> str:
    """Numărul pentru explicație: fără zerourile de la coadă, cu virgulă zecimală (37.2800 → „37,28”)."""
    text = format(Decimal(value or 0), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in ("-0", ""):
        text = "0"
    return text.replace(".", ",").replace("-", "−")


class Parsed:
    """Formula citită: arborele, textul tradus, harta pozițiilor și ce folosește (variabile, constante, tipuri)."""

    def __init__(self, source: str, tree, translated: str, positions: list):
        self.source, self.tree, self.translated, self.positions = source, tree, translated, positions
        self.variables, self.constants, self.refs = [], [], []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in VARIABLES and node.id not in self.variables:
                self.variables.append(node.id)
            if isinstance(node, ast.Subscript):
                code = node.slice.value
                target = self.refs if node.value.id == REF else self.constants
                if code not in target:
                    target.append(code)

    def pos(self, node) -> int:
        return original_position(self.positions, getattr(node, "col_offset", 0))


def original_position(positions, offset: int) -> int:
    best = 1
    for trans, orig in positions:
        if trans <= offset:
            best = orig
        else:
            break
    return best


def _translate(text: str):
    """Atomii formulei → textul Python și harta (poziția în textul tradus, poziția în original, de la 1)."""
    out, positions, i, depth, length = [], [], 0, 0, 0
    while i < len(text):
        m = _TOKEN.match(text, i)
        if not m:
            ch = text[i]
            if ch == ",":
                raise FormulaError("Argumentele funcțiilor se despart cu „;”, nu cu „,” (virgula e doar zecimală: 1,5)", i + 1)
            if ch == ".":
                raise FormulaError("Atributele nu sunt permise (doar C.<cod> pentru constante)", i + 1)
            if ch == "_":
                raise FormulaError("Numele cu „_” nu sunt permise", i + 1)
            raise FormulaError(f"Caracterul „{ch}” nu este permis", i + 1)
        kind = next(k for k in ("space", "number", "const", "ref", "name", "op") if m.group(k) is not None)
        raw = m.group(0)
        piece = None
        if kind == "space":
            i = m.end()
            continue
        if kind == "number":
            nxt = text[m.end():m.end() + 1]
            if nxt and (nxt.isalpha() or nxt == "_"):
                raise FormulaError(f"Numărul „{raw}” e lipit de un nume", i + 1)
            if nxt == "." or (nxt == "," and text[m.end() + 1:m.end() + 2].isdigit()):
                raise FormulaError(f"Numărul „{raw}{nxt}…” nu este corect", i + 1)
            piece = raw.replace(",", ".")
        elif kind == "const":
            if text[m.end():m.end() + 1] == ".":
                raise FormulaError("Atributele nu sunt permise (doar C.<cod> pentru constante)", m.end() + 1)
            piece = f'{CONST}["{m.group("ccode")}"]'
        elif kind == "ref":
            code = m.group("rcode").strip()
            if not code:
                raise FormulaError("Între paranteze pătrate se scrie codul tipului de calcul: [PREMIU]", i + 1)
            if not re.fullmatch(r"[A-Za-z0-9_\-]+", code):
                raise FormulaError(f"Codul „{code}” nu este un cod de tip de calcul", i + 1)
            piece = f'{REF}["{code}"]'
        elif kind == "name":
            low = raw.lower()
            if text[m.end():m.end() + 1] == ".":
                raise FormulaError(f"Atributele nu sunt permise („{raw}.”); constantele se scriu C.<cod>", m.end() + 1)
            if low in _LOGIC:
                piece = f" {_LOGIC[low]} "
            elif low in _FUNC_ALIASES:
                rest = text[m.end():].lstrip()
                if not rest.startswith("("):
                    raise FormulaError(f"După funcția „{raw}” urmează paranteza: {raw}(…)", i + 1)
                piece = _FUNC_ALIASES[low]
            elif low in _VAR_BY_LOWER:
                piece = _VAR_BY_LOWER[low]
            else:
                raise FormulaError(f"Variabila sau funcția „{raw}” nu există", i + 1)
        elif kind == "op":
            if raw == "(":
                depth += 1
            elif raw == ")":
                depth -= 1
                if depth < 0:
                    raise FormulaError("Paranteza „)” nu are pereche", i + 1)
            piece = {";": ",", "=": "==", "<>": "!=", "==": "==", "!=": "!="}.get(raw, raw)
        positions.append((length + (len(piece) - len(piece.lstrip())), i + 1))
        out.append(piece)
        length += len(piece)
        i = m.end()
    if depth > 0:
        raise FormulaError("Lipsește paranteza „)”", len(text))
    return "".join(out), positions


_BIN = {ast.Add: "+", ast.Sub: "−", ast.Mult: "×", ast.Div: "/"}
_CMP = {ast.Lt: "<", ast.LtE: "≤", ast.Gt: ">", ast.GtE: "≥", ast.Eq: "=", ast.NotEq: "≠"}
_ALLOWED = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.Call, ast.Name, ast.Constant, ast.Subscript,
            ast.Load, ast.And, ast.Or, ast.USub, ast.UAdd, *_BIN, *_CMP)


def _depth(node, level=0) -> int:
    children = list(ast.iter_child_nodes(node))
    return max((_depth(c, level + 1) for c in children), default=level)


def parse(text: str) -> Parsed:
    """Citește și verifică formula (sintaxa, lista albă); erorile — `FormulaError` cu poziția."""
    text = (text or "").strip()
    if not text:
        raise FormulaError("Formula este goală")
    if len(text) > MAX_LENGTH:
        raise FormulaError(f"Formula e prea lungă (cel mult {MAX_LENGTH} de caractere)")
    translated, positions = _translate(text)
    try:
        tree = ast.parse(translated, mode="eval")
    except SyntaxError as exc:
        offset = (exc.offset or 1) - 1
        raise FormulaError("Formula nu este scrisă corect (lipsește un operator, un număr sau o paranteză)",
                           original_position(positions, offset)) from None
    nodes = list(ast.walk(tree))
    if len(nodes) > MAX_NODES:
        raise FormulaError("Formula e prea complicată")
    if _depth(tree) > MAX_DEPTH:
        raise FormulaError("Formula are prea multe niveluri de paranteze / funcții")
    for node in nodes:
        where = original_position(positions, getattr(node, "col_offset", 0))
        if not isinstance(node, _ALLOWED):
            raise FormulaError("Construcția nu este permisă în formulă", where)
        if isinstance(node, ast.Constant) and (isinstance(node.value, bool) or not isinstance(node.value, (int, float, str))):
            raise FormulaError("Valoarea nu este permisă în formulă", where)
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in FUNCTIONS or node.keywords:
                raise FormulaError("Se pot folosi doar funcțiile min, max, round, abs, daca", where)
            lo, hi = ARITY[node.func.id]
            if not lo <= len(node.args) <= hi:
                need = f"{lo}" if lo == hi else f"{lo}–{hi}"
                raise FormulaError(f"Funcția {node.func.id} primește {need} argumente (despărțite cu „;”)", where)
        if isinstance(node, ast.Subscript):
            if not (isinstance(node.value, ast.Name) and node.value.id in (REF, CONST) and isinstance(node.slice, ast.Constant)
                    and isinstance(node.slice.value, str)):
                raise FormulaError("Construcția nu este permisă în formulă", where)
        if isinstance(node, ast.Name) and node.id not in VARIABLES and node.id not in FUNCTIONS and node.id not in (REF, CONST):
            raise FormulaError(f"Variabila „{node.id}” nu există", where)
    for node in nodes:  # numele de funcție doar ca apel, numele interne doar ca indice
        if isinstance(node, ast.Name) and node.id in FUNCTIONS:
            parent_ok = any(isinstance(c, ast.Call) and c.func is node for c in nodes)
            if not parent_ok:
                raise FormulaError(f"„{node.id}” este o funcție: {node.id}(…)", original_position(positions, node.col_offset))
        if isinstance(node, ast.Name) and node.id in (REF, CONST):
            if not any(isinstance(c, ast.Subscript) and c.value is node for c in nodes):
                raise FormulaError("Construcția nu este permisă în formulă", original_position(positions, node.col_offset))
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if not any(isinstance(c, ast.Subscript) and c.slice is node for c in nodes):
                raise FormulaError("Textul nu este permis în formulă", original_position(positions, node.col_offset))
    return Parsed(text, tree, translated, positions)


def check(text: str, type_codes=None, constant_codes=None) -> Parsed:
    """Verificarea la salvare: sintaxa + codurile tipurilor ([COD]) și ale constantelor (C.cod) există."""
    parsed = parse(text)
    for node in ast.walk(parsed.tree):
        if isinstance(node, ast.Subscript):
            code = node.slice.value
            if node.value.id == REF and type_codes is not None and code not in type_codes:
                raise FormulaError(f"Tipul de calcul [{code}] nu există", parsed.pos(node))
            if node.value.id == CONST and constant_codes is not None and code not in constant_codes:
                raise FormulaError(f"Constanta C.{code} nu există", parsed.pos(node))
    return parsed


class Result:
    def __init__(self, value: Decimal, used: dict, explanation: str):
        self.value, self.used, self.explanation = value, used, explanation


class Evaluator:
    """Evaluează formula citită. `resolve(kind, name)` dă valoarea: kind = "var" | "const" | "ref"."""

    def __init__(self, parsed: Parsed, resolve):
        self.p, self.resolve = parsed, resolve
        self.values = {}  # id(nod) → valoarea frunzei (pentru explicație)
        self.used = {}  # eticheta → valoarea, în ordinea folosirii

    def run(self) -> Result:
        value = self._eval(self.p.tree.body)
        return Result(value, self.used, f"{self._render(self.p.tree.body)} = {fmt(value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))}")

    def _leaf(self, node, label, kind, name):
        try:
            value = Decimal(self.resolve(kind, name))
        except FormulaError as exc:
            raise FormulaError(exc.message, exc.position or self.p.pos(node)) from None
        self.values[id(node)] = value
        self.used.setdefault(label, value)
        return value

    def _eval(self, node) -> Decimal:
        if isinstance(node, ast.Constant):
            value = Decimal(ast.get_source_segment(self.p.translated, node) or str(node.value))
            self.values[id(node)] = value
            return value
        if isinstance(node, ast.Name):
            return self._leaf(node, node.id, "var", node.id)
        if isinstance(node, ast.Subscript):
            code = node.slice.value
            if node.value.id == REF:
                return self._leaf(node, f"[{code}]", "ref", code)
            return self._leaf(node, f"C.{code}", "const", code)
        if isinstance(node, ast.UnaryOp):
            v = self._eval(node.operand)
            return -v if isinstance(node.op, ast.USub) else v
        if isinstance(node, ast.BinOp):
            a, b = self._eval(node.left), self._eval(node.right)
            if isinstance(node.op, ast.Add):
                return a + b
            if isinstance(node.op, ast.Sub):
                return a - b
            if isinstance(node.op, ast.Mult):
                return a * b
            if b == 0:
                raise FormulaError(f"Împărțire la zero ({self._render(node.right)} = 0); folosiți daca(… > 0; …; 0)",
                                   self.p.pos(node.right))
            try:
                return a / b
            except (DivisionByZero, InvalidOperation):
                raise FormulaError("Împărțire la zero", self.p.pos(node.right)) from None
        if isinstance(node, ast.Compare):
            left = self._eval(node.left)
            for op, right_node in zip(node.ops, node.comparators):
                right = self._eval(right_node)
                ok = {ast.Lt: left < right, ast.LtE: left <= right, ast.Gt: left > right, ast.GtE: left >= right,
                      ast.Eq: left == right, ast.NotEq: left != right}[type(op)]
                if not ok:
                    return Decimal(0)
                left = right
            return Decimal(1)
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return Decimal(1) if all(self._eval(v) != 0 for v in node.values) else Decimal(0)
            return Decimal(1) if any(self._eval(v) != 0 for v in node.values) else Decimal(0)
        if isinstance(node, ast.Call):
            name = node.func.id
            if name == "daca":
                cond = self._eval(node.args[0])
                return self._eval(node.args[1] if cond != 0 else node.args[2])
            args = [self._eval(a) for a in node.args]
            if name == "min":
                return min(args)
            if name == "max":
                return max(args)
            if name == "abs":
                return abs(args[0])
            if name == "round":
                places = args[1] if len(args) > 1 else Decimal(0)
                if places != places.to_integral_value() or not 0 <= places <= 6:
                    raise FormulaError("round(x; n): n este un număr întreg de la 0 la 6", self.p.pos(node))
                return args[0].quantize(Decimal(1).scaleb(-int(places)), rounding=ROUND_HALF_UP)
        raise FormulaError("Construcția nu este permisă în formulă", self.p.pos(node))  # nu se ajunge (lista albă)

    # -- explicația: formula cu valorile ei --
    _PREC = {ast.Or: 1, ast.And: 2}

    def _prec(self, node) -> int:
        if isinstance(node, ast.BoolOp):
            return self._PREC[type(node.op)]
        if isinstance(node, ast.Compare):
            return 3
        if isinstance(node, ast.BinOp):
            return 4 if isinstance(node.op, (ast.Add, ast.Sub)) else 5
        if isinstance(node, ast.UnaryOp):
            return 6
        return 7

    def _wrap(self, child, parent_prec, right=False) -> str:
        text = self._render(child)
        p = self._prec(child)
        return f"({text})" if p < parent_prec or (right and p == parent_prec and p in (4, 5)) else text

    def _render(self, node) -> str:
        v = self.values.get(id(node))
        if isinstance(node, ast.Constant):
            return fmt(v if v is not None else node.value)
        if isinstance(node, ast.Name):
            return f"{node.id} {fmt(v)}" if v is not None else node.id
        if isinstance(node, ast.Subscript):
            label = f"[{node.slice.value}]" if node.value.id == REF else f"C.{node.slice.value}"
            return f"{label} {fmt(v)}" if v is not None else label
        if isinstance(node, ast.UnaryOp):
            sign = "−" if isinstance(node.op, ast.USub) else "+"
            return sign + self._wrap(node.operand, 6)
        if isinstance(node, ast.BinOp):
            p = self._prec(node)
            return f"{self._wrap(node.left, p)} {_BIN[type(node.op)]} {self._wrap(node.right, p, right=True)}"
        if isinstance(node, ast.Compare):
            parts = [self._wrap(node.left, 4)]
            for op, c in zip(node.ops, node.comparators):
                parts += [_CMP[type(op)], self._wrap(c, 4)]
            return " ".join(parts)
        if isinstance(node, ast.BoolOp):
            word = " și " if isinstance(node.op, ast.And) else " sau "
            return word.join(self._wrap(v, self._prec(node)) for v in node.values)
        if isinstance(node, ast.Call):
            return f"{node.func.id}({'; '.join(self._render(a) for a in node.args)})"
        return "?"


def evaluate(text_or_parsed, resolve) -> Result:
    parsed = text_or_parsed if isinstance(text_or_parsed, Parsed) else parse(text_or_parsed)
    return Evaluator(parsed, resolve).run()


def references(text: str) -> list:
    """Codurile tipurilor folosite ca [COD] (gol dacă formula nu se citește)."""
    try:
        return parse(text).refs
    except FormulaError:
        return []
