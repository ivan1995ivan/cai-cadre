import re
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from rest_framework import serializers

from . import dependencies, explain, formula
from .models import (EmployeePayItem, ExemptionDependent, ExemptionRequest, FiscalRegime, ItParkMonth, OccupationPayItem, PayConstant,
                     PayItemChange, PayItemChangeLine, Payment, PaymentLine, Payroll, PayrollItem, PayrollLine, PayType)


class PayConstantSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayConstant
        fields = ["id", "code", "name", "value", "date_from", "source", "unit"]


class FiscalRegimeSerializer(serializers.ModelSerializer):
    """Regimul fiscal cu „în vigoare din” (luna): gol — luna următoare datei obținerii / retragerii statutului (CF art. 375)."""

    regime_label = serializers.CharField(source="get_regime_display", read_only=True)

    class Meta:
        model = FiscalRegime
        fields = ["id", "regime", "regime_label", "date_from", "status_date", "document", "note"]
        extra_kwargs = {"date_from": {"required": False, "allow_null": True}}

    def validate(self, attrs):
        from .models import next_month

        date_from = attrs.get("date_from", getattr(self.instance, "date_from", None))
        status_date = attrs.get("status_date", getattr(self.instance, "status_date", None))
        if date_from is None:
            if status_date is None:
                raise serializers.ValidationError({"date_from": "Dați luna de la care se aplică regimul sau data obținerii statutului."})
            date_from = next_month(status_date)
        date_from = date_from.replace(day=1)
        if status_date and date_from < next_month(status_date):
            raise serializers.ValidationError({"date_from": "Regimul nou se aplică din luna următoare obținerii / retragerii "
                                                            "statutului (Codul fiscal, art. 375)."})
        clash = FiscalRegime.objects.filter(date_from=date_from).exclude(pk=getattr(self.instance, "pk", None))
        if clash.exists():
            raise serializers.ValidationError({"date_from": f"Pentru luna {date_from:%m.%Y} regimul e deja dat."})
        attrs["date_from"] = date_from
        return attrs


class ItParkMonthSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItParkMonth
        fields = ["id", "year", "month", "sales_income", "submitted_on", "note"]
        read_only_fields = ["year", "month"]

    def validate_sales_income(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Venitul nu poate fi negativ.")
        return value


class PayTypeSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    formula_label = serializers.CharField(source="get_formula_display", read_only=True)
    applies_to_label = serializers.CharField(source="get_applies_to_display", read_only=True)
    how = serializers.SerializerMethodField()

    class Meta:
        model = PayType
        fields = ["id", "code", "name_ro", "name_ru", "name_en", "category", "category_label", "formula", "formula_label", "auto",
                  "expression", "applies_to", "applies_to_label", "how",
                  "percent", "base_codes", "scale", "taxable", "cas", "cnam", "exempt_month", "exempt_year", "exempt_avg_pct",
                  "in_average", "ipc_code", "account", "on_payslip", "sort", "is_active", "is_system"]
        read_only_fields = ["is_system"]

    def get_how(self, obj):
        """Din ce se calculează (RO / RU / EN): regula motorului la tipurile automate, formula / baza la celelalte."""
        cache = self.context.setdefault("_how", {}) if isinstance(self.context, dict) else {}
        if "names" not in cache:
            from django.utils import timezone

            from .engine import Constants

            cache["names"] = {t.code: (t.name_ro, t.name_ru, t.name_en) for t in PayType.objects.all()}
            cache["const"] = Constants(timezone.localdate())
        return explain.how(obj, cache["names"], cache["const"])

    def validate(self, attrs):
        for key in ("base_codes", "scale"):
            if key in attrs and not isinstance(attrs[key], list):
                raise serializers.ValidationError({key: "O listă."})
        for step in attrs.get("scale") or []:
            if not isinstance(step, dict) or set(step) != {"from", "pct"}:
                raise serializers.ValidationError({"scale": "Fiecare treaptă are „from” (ani de vechime) și „pct”."})
            try:
                if Decimal(str(step["from"])) < 0 or Decimal(str(step["pct"])) < 0:
                    raise serializers.ValidationError({"scale": "Anii și procentul nu pot fi negative."})
            except (InvalidOperation, ValueError) as exc:
                raise serializers.ValidationError({"scale": "Anii și procentul sunt numere."}) from exc
        if self.instance is None and attrs.get("formula") == "scale" and "applies_to" not in self.initial_data:
            attrs["applies_to"] = "all"  # treptele de vechime — implicit pentru toți angajații (ca până la formulă)
        check_type(self.instance, attrs)
        return attrs


def type_candidate(instance, attrs) -> PayType:
    """Tipul așa cum ar fi după salvare (nesalvat): valorile noi peste cele vechi."""
    fields = {f.name: getattr(instance, f.name) for f in PayType._meta.concrete_fields} if instance else {}
    cand = PayType(**{k: v for k, v in fields.items() if k != "id"})
    cand.pk = instance.pk if instance else None
    for k, v in attrs.items():
        setattr(cand, k, v)
    cand.code = (cand.code or "").strip()
    return cand


def check_type(instance, attrs) -> PayType:
    """Verificările tipului la salvare: formula (sintaxa, variabilele, codurile, cu poziția), baza (coduri existente, fără
    tipurile calculate după formule), dependența circulară, „pentru toți” doar unde se poate, redenumirea unui cod folosit."""
    cand = type_candidate(instance, attrs)
    if (instance is None or cand.code != instance.code) and not re.fullmatch(r"[A-Za-z0-9_\-]+", cand.code):
        raise serializers.ValidationError({"code": "Codul: litere latine, cifre, „_” și „-” (în formule se scrie [COD])."})
    others = [t for t in PayType.objects.all() if t.pk != cand.pk]
    by_code = {t.code: t for t in others}
    known = set(by_code) | {cand.code}
    if cand.formula == "expr":
        try:
            parsed = formula.check(cand.expression, type_codes=known,
                                   constant_codes=set(PayConstant.objects.values_list("code", flat=True)))
        except formula.FormulaError as exc:
            raise serializers.ValidationError({"expression": exc.text()}) from None
        refs = parsed.refs
    else:
        refs = []
    if cand.formula in ("pct_base", "expr", "scale"):
        unknown = [c for c in cand.base_codes or [] if c not in known]
        if unknown:
            raise serializers.ValidationError({"base_codes": "Tipurile nu există: " + ", ".join(unknown)})
        for code in [*(cand.base_codes or []), *refs]:
            t = cand if code == cand.code else by_code.get(code)
            if t is not None and t.formula == "auto" and t.auto in dependencies.LATE_AUTOS:
                raise serializers.ValidationError({"expression" if code in refs else "base_codes": (
                    f"{code} ({t.name_ro}) se calculează după formule sau la plată; nu poate intra în baza / formula altui tip.")})
    if cand.applies_to == "all" and cand.formula not in PayType.GENERAL_FORMULAS:
        raise serializers.ValidationError({"applies_to": "„Toți angajații” — doar la formulă, trepte de vechime și procente; "
                                                         "suma fixă și tariful orar vin din rândul angajatului."})
    graph = {t.code: dependencies.deps_of(t) for t in others}
    graph[cand.code] = dependencies.deps_of(cand)
    path = dependencies.find_cycle(graph, cand.code)
    if path:
        field = "expression" if cand.formula == "expr" else "base_codes"
        raise serializers.ValidationError({field: dependencies.cycle_text(path)})
    if instance is not None and cand.code != instance.code:
        users = dependencies.users_of(instance.code, others)
        if users:
            raise serializers.ValidationError({"code": f"Codul {instance.code} e folosit în baza / formula tipurilor "
                                                       f"{', '.join(t.code for t in users)}; schimbați-le întâi."})
    return cand


class EmployeePayItemSerializer(serializers.ModelSerializer):
    """Rândul din fila „Salariu”. Cel venit dintr-un document (ordinul, „Modificarea acumulărilor planificate”) are sursa cu
    legătura spre el și nu se schimbă de mână (doar observațiile): se modifică / se oprește printr-un document nou."""

    pay_type_name = serializers.CharField(source="pay_type.name_ro", read_only=True)
    pay_type_code = serializers.CharField(source="pay_type.code", read_only=True)
    formula = serializers.CharField(source="pay_type.formula", read_only=True)
    category = serializers.CharField(source="pay_type.category", read_only=True)
    employment_label = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()

    class Meta:
        model = EmployeePayItem
        fields = ["id", "employee", "employment", "employment_label", "pay_type", "pay_type_name", "pay_type_code", "formula",
                  "category", "amount", "percent", "quantity", "date_from", "date_to", "document", "note", "source"]

    def get_employment_label(self, obj):
        j = obj.employment
        return f"{j.get_kind_display()}: {j.occupation.name_ro}" if j else ""

    def get_source(self, obj):
        """De unde vine rândul: {kind: order | change | manual, id, label}."""
        if obj.order_item_id:
            order = obj.order_item.order
            return {"kind": "order", "id": order.pk, "label": f"Ordinul nr. {order.reference()}", "status": order.status,
                    "number": order.number, "date": order.date}
        if obj.change_line_id:
            doc = obj.change_line.change
            return {"kind": "change", "id": doc.pk, "label": f"Modificarea acumulărilor {doc.reference()}", "status": doc.status,
                    "number": doc.number, "date": doc.date}
        return {"kind": "manual", "id": None, "label": "", "status": ""}

    def validate(self, attrs):
        if self.instance is not None and self.instance.from_document:
            changed = [k for k, v in attrs.items() if k != "note" and v != getattr(self.instance, k)]
            if changed:
                raise serializers.ValidationError({"detail": "Rândul vine dintr-un document; se modifică / se oprește printr-un ordin "
                                                             "sau prin „Modificarea acumulărilor planificate”."})
            return attrs
        t = attrs.get("pay_type", getattr(self.instance, "pay_type", None))
        amount = attrs.get("amount", getattr(self.instance, "amount", None))
        percent = attrs.get("percent", getattr(self.instance, "percent", None))
        problem = row_problem(t, amount, percent)
        if problem:
            raise serializers.ValidationError(problem)
        job = attrs.get("employment")
        emp = attrs.get("employee", getattr(self.instance, "employee", None))
        if job is not None and emp is not None and job.employee_id != emp.pk:
            raise serializers.ValidationError({"employment": "Raportul de muncă este al altui angajat."})
        start = attrs.get("date_from", getattr(self.instance, "date_from", None))
        end = attrs.get("date_to", getattr(self.instance, "date_to", None))
        if start and end and end < start:
            raise serializers.ValidationError({"date_to": "Sfârșitul este înaintea începutului."})
        return attrs


def row_problem(t, amount, percent) -> dict | None:
    """Ce lipsește rândului angajatului pentru tipul `t` (aceleași reguli în fila „Salariu”, în ordin și în document)."""
    if t is None:
        return {"pay_type": "Alegeți tipul de calcul."}
    if t.formula == "auto":
        return {"pay_type": "Tipul se calculează singur; nu se pune pe angajat."}
    if t.formula in ("fixed", "hourly") and amount is None:
        return {"amount": "Dați suma (sau tariful)."}
    if t.formula in ("pct_salary", "pct_base") and percent is None and not t.percent:
        return {"percent": "Dați procentul."}
    for value, field in ((amount, "amount"), (percent, "percent")):
        if value is not None and Decimal(value) < 0:
            return {field: "Nu poate fi negativ."}
    return None


class OccupationPayItemSerializer(serializers.ModelSerializer):
    """Acumularea-tip a funcției (clasificatorul funcțiilor)."""

    pay_type_code = serializers.CharField(source="pay_type.code", read_only=True)
    pay_type_name = serializers.CharField(source="pay_type.name_ro", read_only=True)

    class Meta:
        model = OccupationPayItem
        fields = ["id", "occupation", "pay_type", "pay_type_code", "pay_type_name", "amount", "percent", "quantity", "sort"]

    def validate(self, attrs):
        t = attrs.get("pay_type", getattr(self.instance, "pay_type", None))
        problem = row_problem(t, attrs.get("amount", getattr(self.instance, "amount", None)),
                              attrs.get("percent", getattr(self.instance, "percent", None)))
        if problem:
            raise serializers.ValidationError(problem)
        return attrs


class PayItemChangeLineSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    tab_number = serializers.CharField(source="employee.tab_number", read_only=True)
    pay_type_code = serializers.CharField(source="pay_type.code", read_only=True)
    pay_type_name = serializers.CharField(source="pay_type.name_ro", read_only=True)
    action_label = serializers.CharField(source="get_action_display", read_only=True)
    employment_label = serializers.SerializerMethodField()

    class Meta:
        model = PayItemChangeLine
        fields = ["id", "employee", "employee_name", "tab_number", "employment", "employment_label", "pay_type", "pay_type_code",
                  "pay_type_name", "action", "action_label", "target", "amount", "percent", "quantity", "date_from", "date_to",
                  "document", "result", "sort"]
        read_only_fields = ["result", "sort"]

    def get_employment_label(self, obj):
        j = obj.employment
        return f"{j.get_kind_display()}: {j.occupation.name_ro}" if j else ""


class PayItemChangeSerializer(serializers.ModelSerializer):
    """Documentul „Modificarea acumulărilor planificate” cu rândurile lui (se trimit cu documentul și îl înlocuiesc întreg)."""

    deletion_mark = serializers.BooleanField(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    lines = PayItemChangeLineSerializer(many=True, required=False)
    employees = serializers.SerializerMethodField()

    class Meta:
        model = PayItemChange
        fields = ["id", "deletion_mark", "number", "date", "status", "status_label", "note", "created_at", "approved_at", "lines",
                  "employees"]
        read_only_fields = ["number", "status", "created_at", "approved_at"]

    def get_employees(self, obj):
        names = list(dict.fromkeys(ln.employee.short_name() for ln in obj.lines.all()))
        return ", ".join(names[:4]) + (f" și încă {len(names) - 4}" if len(names) > 4 else "")

    def validate(self, attrs):
        for n, ln in enumerate(attrs.get("lines") or [], start=1):
            emp, job, t, target = ln.get("employee"), ln.get("employment"), ln.get("pay_type"), ln.get("target")
            if job is not None and job.employee_id != emp.pk:
                raise serializers.ValidationError({"lines": f"Rândul {n}: raportul de muncă este al altui angajat."})
            if target is not None and (target.employee_id != emp.pk or target.pay_type_id != t.pk):
                raise serializers.ValidationError({"lines": f"Rândul {n}: rândul ales din fila „Salariu” e al altui angajat / tip."})
            action = ln.get("action", "add")
            if action == "add":
                problem = row_problem(t, ln.get("amount"), ln.get("percent"))
                if problem:
                    raise serializers.ValidationError({"lines": f"Rândul {n}, {t.code}: {next(iter(problem.values()))}"})
            elif t.formula == "auto":
                raise serializers.ValidationError({"lines": f"Rândul {n}: tipul {t.code} se calculează singur."})
            for key in ("amount", "percent", "quantity"):
                if ln.get(key) is not None and ln[key] < 0:
                    raise serializers.ValidationError({"lines": f"Rândul {n}: valorile nu pot fi negative."})
            if ln.get("date_from") and ln.get("date_to") and ln["date_to"] < ln["date_from"] and action != "stop":
                raise serializers.ValidationError({"lines": f"Rândul {n}: „până la” este înaintea lui „de la”."})
        return attrs

    def _save_lines(self, doc, rows):
        if rows is None:
            return
        keep = []
        for n, data in enumerate(rows, start=1):
            pk = data.pop("id", None)
            obj = doc.lines.filter(pk=pk).first() if pk else None
            if obj is None:
                obj = PayItemChangeLine(change=doc)
            for k, v in data.items():
                setattr(obj, k, v)
            obj.sort = n * 10
            obj.save()
            keep.append(obj.pk)
        doc.lines.exclude(pk__in=keep).delete()

    @transaction.atomic
    def create(self, validated_data):
        rows = validated_data.pop("lines", [])
        doc = super().create(validated_data)
        self._save_lines(doc, rows)
        return doc

    @transaction.atomic
    def update(self, instance, validated_data):
        rows = validated_data.pop("lines", None)
        doc = super().update(instance, validated_data)
        self._save_lines(doc, rows)
        return doc


FAMILY_RELATION = {"son": "child", "daughter": "child", "mother": "parent", "father": "parent"}  # rudenia din „Familia”


def _idnp(value, field):
    if value and not re.fullmatch(r"\d{13}", value):
        raise serializers.ValidationError({field: "Codul fiscal (IDNP) are 13 cifre."})


class ExemptionDependentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    code = serializers.CharField(read_only=True)
    relation_label = serializers.CharField(source="get_relation_display", read_only=True)
    disability_label = serializers.CharField(source="get_disability_display", read_only=True)

    class Meta:
        model = ExemptionDependent
        fields = ["id", "family_member", "name", "idnp", "birth_date", "relation", "relation_label", "disability", "disability_label",
                  "date_from", "date_to", "document", "income_ok", "note", "code"]
        extra_kwargs = {"name": {"required": False, "allow_blank": True}}


class ExemptionRequestSerializer(serializers.ModelSerializer):
    """Cererea de scutire cu persoanele întreținute (rândurile se trimit cu cererea și o înlocuiesc întreagă)."""

    code = serializers.SerializerMethodField()
    code_now = serializers.SerializerMethodField()
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    dependents = ExemptionDependentSerializer(many=True, required=False)
    warnings = serializers.SerializerMethodField()
    place_label = serializers.CharField(source="get_place_display", read_only=True)

    class Meta:
        model = ExemptionRequest
        fields = ["id", "employee", "employee_name", "number", "date", "date_from", "date_to", "kind", "major_category",
                  "major_document", "spouse_major", "spouse_name", "spouse_idnp", "spouse_category", "spouse_document",
                  "waiver_date", "place", "place_label", "documents", "needs_review", "review_note", "is_active", "dependents", "code",
                  "code_now", "warnings"]

    def get_code(self, obj):
        return obj.code()

    def get_code_now(self, obj):
        return obj.code(timezone.localdate().replace(day=1)) if obj.valid_in(timezone.localdate().replace(day=1)) else ""

    def get_warnings(self, obj):
        from .engine import Constants

        out = []
        if obj.needs_review:
            out.append(obj.review_note or "Cererea este de verificat.")
        limit = Constants(timezone.localdate())("exemption_dependent_income", "12400")
        for d in obj.dependents.all():
            if not d.income_ok:
                out.append(f"{d.name}: venitul anual peste {limit:g} lei — scutirea pentru această persoană nu se acordă.")
        out += it_park_warning(obj)
        return out

    def validate(self, attrs):
        get = lambda k: attrs.get(k, getattr(self.instance, k, None))  # noqa: E731
        if get("kind") == "major" and not get("major_category"):
            raise serializers.ValidationError({"major_category": "Alegeți categoria scutirii majorate (CF art. 33 alin. (2))."})
        if get("spouse_major"):
            if not (get("spouse_name") or "").strip() or not get("spouse_idnp"):
                raise serializers.ValidationError({"spouse_idnp": "Pentru Sm dați numele și codul fiscal al soțului / soției."})
            if not get("spouse_category"):
                raise serializers.ValidationError({"spouse_category": "Sm se acordă pentru soțul / soția din categoriile CF art. 33 alin. (2)."})
        _idnp(get("spouse_idnp"), "spouse_idnp")
        if get("date_to") and get("date_from") and get("date_to") < get("date_from"):
            raise serializers.ValidationError({"date_to": "Sfârșitul este înaintea începutului."})
        if get("waiver_date") and get("kind") == "none":
            raise serializers.ValidationError({"waiver_date": "Renunțarea privește doar scutirea P / M."})
        employee = get("employee")
        for n, d in enumerate(attrs.get("dependents") or [], start=1):
            fm = d.get("family_member")
            if fm is not None:
                if employee is not None and fm.employee_id != employee.pk:
                    raise serializers.ValidationError({"dependents": f"Rândul {n}: membrul familiei este din alt dosar."})
                # alegerea din „Familia” completează rândul (ce s-a scris de mână rămâne)
                d["name"] = d.get("name") or fm.full_name
                d["idnp"] = d.get("idnp") or fm.idnp
                d["birth_date"] = d.get("birth_date") or fm.birth_date
                if "relation" not in d and fm.relation_id:
                    d["relation"] = FAMILY_RELATION.get(fm.relation.code, "other")
            if not (d.get("name") or "").strip():
                raise serializers.ValidationError({"dependents": f"Rândul {n}: numele persoanei întreținute."})
            _idnp(d.get("idnp"), "dependents")
            if d.get("relation") == "sibling" and not d.get("disability"):
                raise serializers.ValidationError({"dependents": f"Rândul {n}: fratele / sora se ia în întreținere doar cu dizabilitate."})
            if d.get("date_to") and d.get("date_from") and d["date_to"] < d["date_from"]:
                raise serializers.ValidationError({"dependents": f"Rândul {n}: sfârșitul dreptului e înaintea începutului."})
        return attrs

    def _save_dependents(self, req, rows):
        if rows is None:
            return
        keep = []
        for n, d in enumerate(rows, start=1):
            pk = d.pop("id", None)
            obj = req.dependents.filter(pk=pk).first() if pk else None
            if obj is None:
                obj = ExemptionDependent(request=req)
            for k, v in d.items():
                setattr(obj, k, v)
            obj.sort = n * 10
            obj.save()
            keep.append(obj.pk)
        req.dependents.exclude(pk__in=keep).delete()

    @transaction.atomic
    def create(self, validated_data):
        rows = validated_data.pop("dependents", [])
        if "place" not in self.initial_data:  # implicit: locul de bază, dacă angajatul are aici raport de bază; altfel — cumulul
            from apps.staff.models import MAIN_KINDS

            main = validated_data["employee"].main_employment()
            validated_data["place"] = "main" if main is not None and main.kind in MAIN_KINDS else "secondary"
        req = super().create(validated_data)
        self._save_dependents(req, rows)
        req.replace_previous()
        return req

    @transaction.atomic
    def update(self, instance, validated_data):
        rows = validated_data.pop("dependents", None)
        req = super().update(instance, validated_data)
        self._save_dependents(req, rows)
        return req


class PayrollItemSerializer(serializers.ModelSerializer):
    code = serializers.CharField(source="pay_type.code", read_only=True)
    name = serializers.CharField(source="pay_type.name_ro", read_only=True)
    category = serializers.CharField(source="pay_type.category", read_only=True)

    class Meta:
        model = PayrollItem
        fields = ["id", "line", "pay_type", "code", "name", "category", "quantity", "base", "percent", "amount", "taxable_part",
                  "manual", "note", "sort"]
        read_only_fields = ["taxable_part", "manual", "sort"]


def it_park_warning(req) -> list:
    """Lunile în regim IT Park din perioada cererii: pe salariul din regim scutirile nu se acordă (CF art. 377 alin. (2));
    se acordă doar în lunile din regimul general, iar în luna cu venit în ambele regimuri — deloc."""
    from datetime import date

    from . import it_park
    from .models import next_month

    if not it_park.ever_it_park():
        return []
    start = (req.date_from or next_month(req.date)).replace(day=1)
    today = timezone.localdate()
    end = req.date_to or date(max(today.year, start.year), 12, 31)
    months = sorted(it_park.it_park_months(start, end))
    if not months:
        return []
    first, last = months[0], months[-1]
    span = f"{first[1]:02d}.{first[0]}" + (f" – {last[1]:02d}.{last[0]}" if last != first else "")
    return [f"Regimul IT Park ({span}, {len(months)} luni): în aceste luni scutirile nu se acordă — salariul e impozitat final "
            "(Codul fiscal, art. 377 alin. (2)). Cererea se aplică doar în lunile din regimul general."]


class PayrollLineSerializer(serializers.ModelSerializer):
    items = PayrollItemSerializer(many=True, read_only=True)
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)

    class Meta:
        model = PayrollLine
        fields = ["id", "payroll", "employee", "employee_name", "employment", "info", "gross", "taxable", "cnam_base", "cas",
                  "deductions", "net", "it_park", "note", "sort", "items"]


class PayrollSerializer(serializers.ModelSerializer):
    deletion_mark = serializers.BooleanField(read_only=True)  # marcat pentru ștergere (formele documentelor)
    subdivision_name = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    lines_count = serializers.IntegerField(read_only=True, default=0)
    it_park = serializers.SerializerMethodField()

    class Meta:
        model = Payroll
        fields = ["id", "deletion_mark", "number", "date", "year", "month", "subdivision", "subdivision_name", "status", "status_label", "totals",
                  "note", "lines_count", "created_at", "calculated_at", "approved_at", "it_park"]
        read_only_fields = ["number", "status", "totals", "calculated_at", "approved_at"]

    def get_subdivision_name(self, obj):
        return obj.subdivision.name_ro if obj.subdivision_id else ""

    def get_it_park(self, obj):
        """Luna calculului e în regimul IT Park (salariul din CIM — impozitat final)."""
        from . import it_park

        return it_park.is_it_park(obj.year, obj.month)

    def validate(self, attrs):
        month = attrs.get("month", getattr(self.instance, "month", 1))
        if not 1 <= month <= 12:
            raise serializers.ValidationError({"month": "Luna este între 1 și 12."})
        return attrs


class PaymentLineSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    tab_number = serializers.CharField(source="employee.tab_number", read_only=True)

    class Meta:
        model = PaymentLine
        fields = ["id", "payment", "employee", "employee_name", "tab_number", "method", "iban", "gross", "exemption", "cnam",
                  "income_tax", "deductions", "amount", "final_gross", "manual", "note", "sort"]
        read_only_fields = ["payment", "employee", "manual", "sort", "final_gross"]

    def validate_amount(self, value):
        if value < 0:
            raise serializers.ValidationError("Suma nu poate fi negativă.")
        return value


class PaymentSerializer(serializers.ModelSerializer):
    deletion_mark = serializers.BooleanField(read_only=True)
    payroll_number = serializers.SerializerMethodField()
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    method_label = serializers.CharField(source="get_method_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    totals = serializers.SerializerMethodField()
    it_park = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        extra_kwargs = {"year": {"required": False}, "month": {"required": False}}
        fields = ["id", "deletion_mark", "number", "date", "year", "month", "kind", "kind_label", "payroll", "payroll_number", "method",
                  "method_label", "status", "status_label", "paid_on", "reference", "note", "totals", "created_at", "it_park"]

    def get_it_park(self, obj):
        """Luna pentru care se plătește e în regimul IT Park: salariul din CIM se plătește fără reținerea impozitului și CNAM."""
        from . import it_park

        return it_park.is_it_park(obj.year, obj.month)
        read_only_fields = ["number", "status", "paid_on"]

    def get_totals(self, obj):
        from .payments import totals

        return totals(obj)

    def get_payroll_number(self, obj):
        p = obj.payroll
        return f"{p.number} · {p.month:02d}.{p.year}" + (f" · {p.subdivision.name_ro}" if p.subdivision_id else "") if p else ""

    def validate(self, attrs):
        """În baza calculului: doar salariul, calculul aprobat; luna se ia din calcul."""
        payroll = attrs.get("payroll", getattr(self.instance, "payroll", None))
        kind = attrs.get("kind", getattr(self.instance, "kind", "salary"))
        if payroll is not None:
            if kind != "salary":
                raise serializers.ValidationError({"payroll": "Avansul nu se face în baza unui calcul."})
            if "payroll" in attrs and (payroll.status != "approved" or payroll.deletion_mark):
                raise serializers.ValidationError({"payroll": "Îndreptarea spre plată se face în baza unui calcul aprobat."})
            attrs["year"], attrs["month"] = payroll.year, payroll.month
        if self.instance is None and ("year" not in attrs or "month" not in attrs):
            raise serializers.ValidationError({"month": "Alegeți luna sau calculul de bază."})
        month = attrs.get("month", getattr(self.instance, "month", 1))
        if not 1 <= month <= 12:
            raise serializers.ValidationError({"month": "Luna este între 1 și 12."})
        return attrs
