from decimal import Decimal, InvalidOperation

from rest_framework import serializers

from .models import (EmployeePayItem, ExemptionRequest, PayConstant, Payment, PaymentLine, Payroll, PayrollItem, PayrollLine,
                     PayType)


class PayConstantSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayConstant
        fields = ["id", "code", "name", "value", "date_from", "source", "unit"]


class PayTypeSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    formula_label = serializers.CharField(source="get_formula_display", read_only=True)

    class Meta:
        model = PayType
        fields = ["id", "code", "name_ro", "name_ru", "name_en", "category", "category_label", "formula", "formula_label", "auto",
                  "percent", "base_codes", "scale", "taxable", "cas", "cnam", "exempt_month", "exempt_year", "exempt_avg_pct",
                  "in_average", "ipc_code", "account", "on_payslip", "sort", "is_active", "is_system"]
        read_only_fields = ["is_system"]

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
        return attrs


class EmployeePayItemSerializer(serializers.ModelSerializer):
    pay_type_name = serializers.CharField(source="pay_type.name_ro", read_only=True)
    category = serializers.CharField(source="pay_type.category", read_only=True)
    employment_label = serializers.SerializerMethodField()

    class Meta:
        model = EmployeePayItem
        fields = ["id", "employee", "employment", "employment_label", "pay_type", "pay_type_name", "category", "amount", "percent",
                  "date_from", "date_to", "document", "note"]

    def get_employment_label(self, obj):
        j = obj.employment
        return f"{j.get_kind_display()}: {j.occupation.name_ro}" if j else ""

    def validate(self, attrs):
        t = attrs.get("pay_type", getattr(self.instance, "pay_type", None))
        amount = attrs.get("amount", getattr(self.instance, "amount", None))
        percent = attrs.get("percent", getattr(self.instance, "percent", None))
        if t and t.formula in ("fixed", "hourly") and amount is None:
            raise serializers.ValidationError({"amount": "Dați suma (sau tariful)."})
        if t and t.formula in ("pct_salary", "pct_base") and percent is None and not t.percent:
            raise serializers.ValidationError({"percent": "Dați procentul."})
        if t and t.formula == "auto":
            raise serializers.ValidationError({"pay_type": "Tipul se calculează singur; nu se pune pe angajat."})
        job = attrs.get("employment")
        emp = attrs.get("employee", getattr(self.instance, "employee", None))
        if job is not None and emp is not None and job.employee_id != emp.pk:
            raise serializers.ValidationError({"employment": "Raportul de muncă este al altui angajat."})
        return attrs


class ExemptionRequestSerializer(serializers.ModelSerializer):
    code = serializers.CharField(read_only=True)
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)

    class Meta:
        model = ExemptionRequest
        fields = ["id", "employee", "employee_name", "year", "date", "kind", "spouse", "spouse_name", "spouse_idnp", "dependents", "documents",
                  "date_from", "is_active", "code"]

    def validate_dependents(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("O listă de persoane.")
        return [{"name": str(d.get("name", ""))[:160], "idnp": str(d.get("idnp", ""))[:13], "disabled": bool(d.get("disabled"))}
                for d in value if isinstance(d, dict)]


class PayrollItemSerializer(serializers.ModelSerializer):
    code = serializers.CharField(source="pay_type.code", read_only=True)
    name = serializers.CharField(source="pay_type.name_ro", read_only=True)
    category = serializers.CharField(source="pay_type.category", read_only=True)

    class Meta:
        model = PayrollItem
        fields = ["id", "line", "pay_type", "code", "name", "category", "quantity", "base", "percent", "amount", "taxable_part",
                  "manual", "note", "sort"]
        read_only_fields = ["taxable_part", "manual", "sort"]


class PayrollLineSerializer(serializers.ModelSerializer):
    items = PayrollItemSerializer(many=True, read_only=True)
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)

    class Meta:
        model = PayrollLine
        fields = ["id", "payroll", "employee", "employee_name", "employment", "info", "gross", "taxable", "cnam_base", "cas",
                  "deductions", "net", "note", "sort", "items"]


class PayrollSerializer(serializers.ModelSerializer):
    deletion_mark = serializers.BooleanField(read_only=True)  # marcat pentru ștergere (formele documentelor)
    subdivision_name = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    lines_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Payroll
        fields = ["id", "deletion_mark", "number", "date", "year", "month", "subdivision", "subdivision_name", "status", "status_label", "totals",
                  "note", "lines_count", "created_at", "calculated_at", "approved_at"]
        read_only_fields = ["number", "status", "totals", "calculated_at", "approved_at"]

    def get_subdivision_name(self, obj):
        return obj.subdivision.name_ro if obj.subdivision_id else ""

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
                  "income_tax", "deductions", "amount", "manual", "note", "sort"]
        read_only_fields = ["payment", "employee", "manual", "sort"]

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

    class Meta:
        model = Payment
        extra_kwargs = {"year": {"required": False}, "month": {"required": False}}
        fields = ["id", "deletion_mark", "number", "date", "year", "month", "kind", "kind_label", "payroll", "payroll_number", "method",
                  "method_label", "status", "status_label", "paid_on", "reference", "note", "totals", "created_at"]
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
