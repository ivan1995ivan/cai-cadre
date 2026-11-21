from datetime import date

from django.db.models import Count, Q
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core import excel_import
from apps.core.deletion import DeletionMarkMixin
from apps.users.permissions import require

from . import printing, services
from .imports import SPECS
from .models import (ORDER_EFFECTS, ORDER_GROUPS, ORDER_REGISTERS, DictItem, LegalBasis, Occupation,
                     OrderType, Specialty, StaffList, StaffListLine, Subdivision)
from .serializers import (DictItemSerializer, LegalBasisSerializer, OccupationSerializer, OrderTypeSerializer,
                          SpecialtySerializer, StaffListLineSerializer, StaffListSerializer, SubdivisionSerializer)


class SearchMixin:
    search_fields = ("code", "name_ro", "name_ru", "name_en")

    def filter_search(self, qs):
        q = (self.request.query_params.get("q") or "").strip()
        if q:
            cond = Q()
            for f in self.search_fields:
                cond |= Q(**{f"{f}__icontains": q})
            qs = qs.filter(cond)
        if self.request.query_params.get("active") == "1":
            qs = qs.filter(is_active=True, deletion_mark=False)
        return qs


class OccupationViewSet(DeletionMarkMixin, SearchMixin, viewsets.ModelViewSet):
    perm_module = "dictionaries"
    serializer_class = OccupationSerializer
    pagination_class = None

    def get_queryset(self):
        qs = self.filter_search(Occupation.objects.select_related("category"))
        category = self.request.query_params.get("category")
        if category == "none":
            qs = qs.filter(category__isnull=True)
        elif category and category.isdigit():
            qs = qs.filter(category_id=category)
        if self.request.query_params.get("no_code") == "1":
            qs = qs.filter(code="")
        return qs


class SpecialtyViewSet(DeletionMarkMixin, SearchMixin, viewsets.ModelViewSet):
    perm_module = "dictionaries"
    serializer_class = SpecialtySerializer
    pagination_class = None

    def get_queryset(self):
        return self.filter_search(Specialty.objects.all())


class DictItemViewSet(DeletionMarkMixin, SearchMixin, viewsets.ModelViewSet):
    perm_module = "dictionaries"
    serializer_class = DictItemSerializer
    pagination_class = None

    def get_queryset(self):
        qs = self.filter_search(DictItem.objects.all())
        if self.request.query_params.get("kind"):
            qs = qs.filter(kind=self.request.query_params["kind"])
        return qs


class LegalBasisViewSet(DeletionMarkMixin, SearchMixin, viewsets.ModelViewSet):
    perm_module = "dictionaries"
    serializer_class = LegalBasisSerializer
    pagination_class = None
    search_fields = ("code", "article", "name_ro", "name_ru", "act")

    def get_queryset(self):
        return self.filter_search(LegalBasis.objects.all())

    @action(detail=False, methods=["get"])
    def preamble(self, request):
        """Preambulul pentru temeiurile alese (?ids=3,7 — în ordinea alegerii): „În temeiul …,”."""
        ids = [int(x) for x in str(request.query_params.get("ids", "")).split(",") if x.strip().isdigit()]
        found = {b.pk: b for b in LegalBasis.objects.filter(pk__in=ids)}
        return Response({"text": LegalBasis.preamble([found[i] for i in ids if i in found])})


class OrderTypeViewSet(DeletionMarkMixin, SearchMixin, viewsets.ModelViewSet):
    perm_module = "dictionaries"
    serializer_class = OrderTypeSerializer
    pagination_class = None

    def get_queryset(self):
        qs = self.filter_search(OrderType.objects.prefetch_related("legal_bases"))
        if self.request.query_params.get("group"):
            qs = qs.filter(group=self.request.query_params["group"])
        return qs


class SubdivisionViewSet(DeletionMarkMixin, SearchMixin, viewsets.ModelViewSet):
    perm_module = "org"
    serializer_class = SubdivisionSerializer
    pagination_class = None

    def get_queryset(self):
        return self.filter_search(Subdivision.objects.select_related("parent"))

    def list(self, request, *args, **kwargs):
        rows = self.get_serializer(self.get_queryset(), many=True).data
        if request.query_params.get("tree") != "1":
            return Response(rows)
        by_parent = {}
        for row in rows:
            by_parent.setdefault(row["parent"], []).append(row)
        ids = {row["id"] for row in rows}

        def build(parent_id, depth=0):
            out = []
            for row in by_parent.get(parent_id, []):
                children = build(row["id"], depth + 1) if depth < 20 else []
                out.append({**row, "children": children} if children else dict(row))
            return out

        # rădăcinile: fără părinte sau cu părintele filtrat (căutare)
        roots = [r for r in rows if r["parent"] is None or r["parent"] not in ids]
        tree = []
        for root in roots:
            children = build(root["id"])
            tree.append({**root, "children": children} if children else dict(root))
        return Response(tree)


class StaffListViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    perm_module = "org"
    perm_actions = {"approve": "approve", "cancel": "approve", "new_version": "create", "diff": "view", "totals": "view",
                    "print": "view"}
    serializer_class = StaffListSerializer

    def get_queryset(self):
        qs = StaffList.objects.select_related("previous").annotate(lines_count=Count("lines"))
        if self.request.query_params.get("status"):
            qs = qs.filter(status=self.request.query_params["status"])
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, status="draft")

    def perform_update(self, serializer):
        services.check_editable(serializer.instance)
        serializer.save()

    def check_delete(self, instance):
        if instance.status == "approved":
            raise ValidationError({"detail": "Statele aprobate nu se șterg; le puteți anula."})

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return Response(self.get_serializer(services.approve(self.get_object(), request.user)).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return Response(self.get_serializer(services.cancel(self.get_object())).data)

    @action(detail=True, methods=["post"], url_path="new-version")
    def new_version(self, request, pk=None):
        raw = request.data.get("effective_from")
        try:
            effective = date.fromisoformat(raw) if raw else None
        except ValueError:
            effective = None
        if effective is None:
            raise ValidationError({"effective_from": "Data intrării în vigoare (AAAA-LL-ZZ) este obligatorie."})
        copy = services.new_version(self.get_object(), effective, request.user)
        return Response(self.get_serializer(StaffList.objects.annotate(lines_count=Count("lines")).get(pk=copy.pk)).data,
                        status=201)

    @action(detail=True, methods=["get"])
    def diff(self, request, pk=None):
        return Response(services.diff(self.get_object(), lang=request.user.language or "ro"))

    @action(detail=True, methods=["get"])
    def totals(self, request, pk=None):
        return Response(services.totals(self.get_object(), lang=request.user.language or "ro"))

    @action(detail=True, methods=["get"])
    def print(self, request, pk=None):
        return printing.print_staff_list(request, self.get_object())


class StaffListLineViewSet(viewsets.ModelViewSet):
    perm_module = "org"
    serializer_class = StaffListLineSerializer
    pagination_class = None

    def get_queryset(self):
        qs = StaffListLine.objects.select_related("subdivision", "occupation", "staff_list", "category", "occupation__category")
        sl = self.request.query_params.get("staff_list")
        if sl:
            qs = qs.filter(staff_list_id=sl)
        elif self.action == "list":
            return qs.none()
        return qs.order_by("subdivision__sort", "subdivision__name_ro", "sort", "id")

    def _edit_check(self, staff_list):
        if not self.request.user.has_crm_perm("org.edit"):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Nu aveți drept de modificare a statelor de personal.")
        services.check_editable(staff_list)

    def perform_create(self, serializer):
        self._edit_check(serializer.validated_data["staff_list"])
        serializer.save()

    def perform_update(self, serializer):
        self._edit_check(serializer.instance.staff_list)
        if "staff_list" in serializer.validated_data and serializer.validated_data["staff_list"] != serializer.instance.staff_list:
            raise ValidationError({"staff_list": "Rândul nu se mută în alt stat."})
        serializer.save()

    def perform_destroy(self, instance):
        self._edit_check(instance.staff_list)
        instance.delete()


class OccupancyView(APIView):
    perm_module = "org"

    def get(self, request):
        sl = None
        if request.query_params.get("staff_list"):
            sl = StaffList.objects.filter(pk=request.query_params["staff_list"]).first()
        on = request.query_params.get("date")
        try:
            on_date = date.fromisoformat(on) if on else None
        except ValueError:
            raise ValidationError({"date": "Data se scrie AAAA-LL-ZZ."}) from None
        return Response(services.occupancy(sl, on_date, lang=request.user.language or "ro"))


class MetaView(APIView):
    """Codurile enumerărilor (traducerea lor e în interfață)."""

    def get(self, request):
        return Response({
            "order_groups": [c for c, _ in ORDER_GROUPS],
            "order_registers": [c for c, _ in ORDER_REGISTERS],
            "order_effects": [c for c, _ in ORDER_EFFECTS],
            "dict_kinds": [c for c, _ in DictItem.KINDS],
            "subdivision_kinds": [c for c, _ in Subdivision.KINDS],
            "specialty_kinds": [c for c, _ in Specialty.KINDS],
            "imports": [{"code": s.code, "title": s.title} for s in SPECS.values()],
        })


IMPORT_PERMS = {"occupations": "dictionaries.create", "specialties": "dictionaries.create",
                "subdivisions": "org.create", "staff_lines": "org.edit"}


class ImportView(APIView):
    """GET …/template/ — șablonul Excel; POST (fișier) — încercarea (dry_run=1) sau importul."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _spec(self, code):
        spec = SPECS.get(code)
        if not spec:
            raise ValidationError({"detail": "Import necunoscut."})
        return spec

    def get(self, request, code):
        spec = self._spec(code)
        require(request.user, IMPORT_PERMS[code].split(".")[0] + ".view")
        response = HttpResponse(excel_import.template(spec),
                                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = f'attachment; filename="sablon-{code}.xlsx"'
        return response

    def post(self, request, code):
        spec = self._spec(code)
        require(request.user, IMPORT_PERMS[code])
        upload = request.FILES.get("file")
        if not upload:
            raise ValidationError({"file": "Alegeți fișierul Excel (.xlsx)."})
        if upload.size > 10 * 1024 * 1024:
            raise ValidationError({"file": "Fișierul e prea mare (cel mult 10 MB)."})
        context = {"create_occupations": str(request.data.get("create_occupations")) in ("1", "true", "True")}
        if code == "staff_lines":
            sl = StaffList.objects.filter(pk=request.data.get("staff_list")).first()
            if sl is None:
                raise ValidationError({"staff_list": "Alegeți statul de personal (ciorna) în care se importă."})
            services.check_editable(sl)
            context["staff_list"] = sl
            context["_sort"] = max([0, *sl.lines.values_list("sort", flat=True)])
        dry_run = str(request.data.get("dry_run", "1")) in ("1", "true", "True")
        return Response(excel_import.run(spec, upload.read(), dry_run=dry_run, context=context))
