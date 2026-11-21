from rest_framework import serializers

from apps.leave.models import Absence

from .models import Incentive, Order, OrderItem, Sanction


class OrderItemSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_tab = serializers.SerializerMethodField()
    order_label = serializers.SerializerMethodField()
    order_status = serializers.CharField(source="order.status", read_only=True)
    warnings = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ["id", "order", "order_label", "order_status", "employee", "employee_name", "employee_tab", "employment",
                  "params", "text", "text_edited", "sort", "acknowledged_on", "result", "warnings"]
        read_only_fields = ["result"]

    def get_employee_name(self, obj):
        return obj.employee.full_name() if obj.employee_id else ""

    def get_employee_tab(self, obj):
        return obj.employee.tab_number if obj.employee_id else ""

    def get_order_label(self, obj):
        return obj.order.reference()

    def get_warnings(self, obj):
        """Ordinul de angajare / transfer / salariu cu salariul de funcție sub salariul minim pe țară."""
        from datetime import date

        from apps.payroll.alerts import min_wage_warning

        p = obj.params or {}
        if p.get("base_salary") in (None, ""):
            return []
        try:
            day = date.fromisoformat(str(p.get("date_from"))[:10]) if p.get("date_from") else obj.order.date
        except ValueError:
            day = obj.order.date
        text = min_wage_warning(p.get("base_salary"), p.get("kind") or "main", day)
        return [text] if text else []

    def validate(self, attrs):
        employee = attrs.get("employee", getattr(self.instance, "employee", None))
        employment = attrs.get("employment", getattr(self.instance, "employment", None))
        if employment is not None and employee is not None and employment.employee_id != employee.pk:
            raise serializers.ValidationError({"employment": "Raportul de muncă este al altui angajat."})
        params = attrs.get("params")
        if params is not None and not isinstance(params, dict):
            raise serializers.ValidationError({"params": "Parametrii sunt un obiect."})
        rows = (params or {}).get("pay_items")
        if rows is not None:
            if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
                raise serializers.ValidationError({"params": "Tabelul „Acumulări și rețineri” este o listă de rânduri."})
            if any(r.get("action", "add") not in ("add", "modify", "stop") for r in rows):
                raise serializers.ValidationError({"params": "Acțiunea rândului: adaugă, modifică sau oprește."})
        return attrs


class OrderSerializer(serializers.ModelSerializer):
    type_code = serializers.CharField(source="order_type.code", read_only=True)
    type_name = serializers.CharField(source="order_type.name_ro", read_only=True)
    effect = serializers.CharField(source="order_type.effect", read_only=True)
    collective = serializers.BooleanField(source="order_type.collective", read_only=True)
    group = serializers.CharField(source="order_type.group", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    employees = serializers.SerializerMethodField()
    cancelled_by_label = serializers.SerializerMethodField()
    legal_bases_ref = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ["id", "order_type", "type_code", "type_name", "effect", "collective", "group", "register", "year", "seq",
                  "number", "date", "title", "preamble", "basis", "legal_bases", "legal_bases_ref", "footer", "signer_name",
                  "signer_position", "approvals", "status", "status_label", "cancelled_by", "cancelled_by_label", "notes",
                  "created_at", "signed_at", "items", "employees"]
        read_only_fields = ["register", "year", "number", "status", "cancelled_by", "created_at", "signed_at"]

    def get_employees(self, obj):
        names = [i.employee.short_name() for i in obj.items.all() if i.employee_id]
        return ", ".join(names[:4]) + (f" și încă {len(names) - 4}" if len(names) > 4 else "")

    def get_cancelled_by_label(self, obj):
        return str(obj.cancelled_by) if obj.cancelled_by_id else ""

    def get_legal_bases_ref(self, obj):
        from apps.org.models import LegalBasis

        return LegalBasis.combined(obj.legal_bases.all())

    def validate_approvals(self, value):
        if not isinstance(value, list) or any(not isinstance(v, dict) for v in value):
            raise serializers.ValidationError("Vizele sunt o listă de {name, position}.")
        return [{"name": str(v.get("name", ""))[:150], "position": str(v.get("position", ""))[:150]} for v in value]


class OrderListSerializer(OrderSerializer):
    class Meta(OrderSerializer.Meta):
        fields = [f for f in OrderSerializer.Meta.fields if f != "items"]


class AbsenceSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    order = serializers.SerializerMethodField()

    class Meta:
        model = Absence
        fields = ["id", "employee", "employment", "kind", "kind_label", "date_from", "date_to", "days", "work_year_from",
                  "work_year_to", "destination", "note", "recalled_on", "days_returned", "order"]

    def get_order(self, obj):
        return {"id": obj.order_item.order_id, "label": obj.order_item.order.reference()} if obj.order_item_id else None


class SanctionSerializer(serializers.ModelSerializer):
    kind_name = serializers.CharField(source="kind.name_ro", read_only=True)
    order = serializers.SerializerMethodField()

    class Meta:
        model = Sanction
        fields = ["id", "employee", "kind", "kind_name", "date", "misconduct", "valid_until", "lifted_on", "order"]

    def get_order(self, obj):
        return {"id": obj.order_item.order_id, "label": obj.order_item.order.reference()} if obj.order_item_id else None


class IncentiveSerializer(serializers.ModelSerializer):
    kind_name = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()

    class Meta:
        model = Incentive
        fields = ["id", "employee", "kind", "kind_name", "date", "amount", "percent", "note", "order"]

    def get_kind_name(self, obj):
        return obj.kind.name_ro if obj.kind_id else ""

    def get_order(self, obj):
        return {"id": obj.order_item.order_id, "label": obj.order_item.order.reference()} if obj.order_item_id else None
