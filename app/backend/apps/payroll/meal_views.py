"""API-ul borderoului tichetelor de masă (apps.payroll.meal_vouchers): lista, completarea din pontaj, numărul scris de mână,
aprobarea / anularea, tiparul. Dreptul — al salarizării (payroll.*); aprobarea cere „approve”."""
from django.db import transaction
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.core.deletion import DeletionMarkMixin
from apps.core.models import NumberSeries

from . import meal_vouchers as mv
from .models import MealVoucherLine, MealVoucherList


class MealVoucherLineSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    tab_number = serializers.CharField(source="employee.tab_number", read_only=True)
    occupation = serializers.CharField(source="employment.occupation.name_ro", read_only=True)
    subdivision = serializers.CharField(source="employment.subdivision.name_ro", read_only=True)

    class Meta:
        model = MealVoucherLine
        fields = ["id", "employee", "employee_name", "tab_number", "employment", "occupation", "subdivision", "days", "day_hours",
                  "night_hours", "shifts", "count", "manual", "amount", "taxable", "note"]
        read_only_fields = fields


class MealVoucherListSerializer(serializers.ModelSerializer):
    deletion_mark = serializers.BooleanField(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    subdivision_name = serializers.CharField(source="subdivision.name_ro", read_only=True, default="")
    lines = MealVoucherLineSerializer(many=True, read_only=True)
    totals = serializers.SerializerMethodField()
    problems = serializers.SerializerMethodField()
    value = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)
    cap = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)

    class Meta:
        model = MealVoucherList
        fields = ["id", "deletion_mark", "number", "date", "year", "month", "subdivision", "subdivision_name", "value", "cap",
                  "status", "status_label", "note", "created_at", "approved_at", "lines", "totals", "problems"]
        read_only_fields = ["number", "status", "created_at", "approved_at"]

    def get_totals(self, obj):
        return mv.totals(obj)

    def get_problems(self, obj):
        return mv.problems(obj) if obj.status == "draft" and self.context.get("detail") else []

    def validate(self, attrs):
        month = attrs.get("month", getattr(self.instance, "month", None))
        if month is not None and not 1 <= month <= 12:
            raise serializers.ValidationError({"month": "Luna este între 1 și 12."})
        if attrs.get("value") is not None and attrs["value"] < 0:
            raise serializers.ValidationError({"value": "Valoarea nu poate fi negativă."})
        return attrs


class MealVoucherViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    perm_module = "payroll"
    serializer_class = MealVoucherListSerializer
    perm_actions = {"approve": "approve", "unapprove": "approve", "print": "view", "fill": "edit", "set_count": "edit"}

    def get_queryset(self):
        qs = MealVoucherList.objects.select_related("subdivision").prefetch_related(
            "lines__employee", "lines__employment__occupation", "lines__employment__subdivision")
        p = self.request.query_params
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("year"):
            qs = qs.filter(date__year=p["year"])
        return qs

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "detail": self.action != "list"}

    def perform_create(self, serializer):
        date = serializer.validated_data.get("date")
        from django.utils import timezone

        c = mv.constants(date or timezone.localdate())
        value = serializer.validated_data.pop("value", None)
        doc = serializer.save(created_by=self.request.user, number=NumberSeries.next_number("meal_vouchers"),
                              value=value if value is not None else c["value"], cap=c["cap"])
        mv.fill(doc)

    def perform_update(self, serializer):
        mv.editable(serializer.instance)
        doc = serializer.save()
        doc.cap = mv.constants(doc.date)["cap"]
        doc.save(update_fields=["cap"])
        for ln in MealVoucherLine.objects.filter(voucher_list=doc):
            mv.price(ln, doc)
            ln.save(update_fields=["amount", "taxable"])

    def check_delete(self, instance):
        mv.editable(instance)

    def _fresh(self, pk):
        return self.get_serializer(MealVoucherList.objects.get(pk=pk)).data

    @action(detail=True, methods=["post"])
    def fill(self, request, pk=None):
        """Completarea din pontajul lunii lucrate; `reset=1` — și numerele scrise de mână se socotesc din nou."""
        doc = self.get_object()
        mv.fill(doc, keep_manual=str(request.data.get("reset", "")) not in ("1", "true", "True"))
        return Response(self._fresh(doc.pk))

    @action(detail=True, methods=["post"], url_path="set-count")
    def set_count(self, request, pk=None):
        """Numărul tichetelor scris de mână pe un rând (`count`); gol — înapoi la cel socotit din pontaj."""
        doc = self.get_object()
        mv.editable(doc)
        line = doc.lines.filter(pk=request.data.get("line")).first()
        if line is None:
            raise ValidationError({"line": "Rândul nu este în borderou."})
        raw = request.data.get("count")
        if raw in (None, ""):
            line.manual = False
            line.save(update_fields=["manual"])
            mv.fill(doc)
        else:
            try:
                count = int(raw)
            except (TypeError, ValueError):
                raise ValidationError({"count": "Numărul tichetelor e un număr întreg."}) from None
            if not 0 <= count <= 62:
                raise ValidationError({"count": "Numărul tichetelor e între 0 și 62."})
            line.count, line.manual = count, True
            mv.price(line, doc)
            line.save(update_fields=["count", "manual", "amount", "taxable"])
        return Response(self._fresh(doc.pk))

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        with transaction.atomic():
            doc = MealVoucherList.objects.select_for_update().get(pk=self.get_object().pk)
            mv.approve(doc, request.user)
        return Response(self._fresh(doc.pk))

    @action(detail=True, methods=["post"])
    def unapprove(self, request, pk=None):
        with transaction.atomic():
            doc = MealVoucherList.objects.select_for_update().get(pk=self.get_object().pk)
            mv.unapprove(doc)
        return Response(self._fresh(doc.pk))

    @action(detail=True, methods=["get"])
    def print(self, request, pk=None):
        return mv.print_list(request, self.get_object())
