from django.http import HttpResponse
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import require

from .models import DOC_TYPES, PrintTemplate
from .renderer import CSP, PrintError, render

# Constructorii de previzualizare: tip document → funcție(request, lang, options) -> context. Modulele (ordine, state,
# salariu) se înscriu aici la pornire, ca editorul de forme să arate șablonul cu date reale.
SAMPLE_BUILDERS: dict = {}
DEFAULT_OPTIONS: dict = {}


class PrintTemplateSerializer(serializers.ModelSerializer):
    modified = serializers.SerializerMethodField()
    text_fields = serializers.SerializerMethodField()
    placeholders = serializers.SerializerMethodField()

    class Meta:
        model = PrintTemplate
        fields = ["id", "doc_type", "code", "name", "body", "css", "orientation", "default_options", "texts", "style",
                  "columns", "is_default", "is_active", "is_system", "modified", "updated_at", "text_fields", "placeholders"]
        read_only_fields = ["is_system", "updated_at"]

    def get_placeholders(self, obj):
        from . import texts

        return texts.PLACEHOLDERS.get(obj.doc_type, [])

    def get_text_fields(self, obj):
        from . import texts

        return texts.fields_for(obj.doc_type)

    def get_modified(self, obj):
        return obj.is_system and (obj.body != obj.original_body or obj.css != obj.original_css)


class PrintTemplateViewSet(viewsets.ModelViewSet):
    """Șabloanele: le văd toți (pentru alegere la tipărire), le modifică cine are settings.edit."""

    serializer_class = PrintTemplateSerializer
    pagination_class = None

    def get_queryset(self):
        qs = PrintTemplate.objects.all()
        if self.request.query_params.get("doc_type"):
            qs = qs.filter(doc_type=self.request.query_params["doc_type"])
        return qs

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            require(request.user, "settings.edit")

    def _validate_body(self, serializer):
        body = serializer.validated_data.get("body")
        if body is not None:
            try:
                from .renderer import ENGINE

                ENGINE.from_string(body)
            except Exception as exc:  # noqa: BLE001
                raise ValidationError({"body": f"Eroare în șablon: {exc}"}) from exc

    def perform_create(self, serializer):
        self._validate_body(serializer)
        self._single_default(serializer.save(is_system=False, updated_at=timezone.now()))

    def perform_update(self, serializer):
        self._validate_body(serializer)
        self._single_default(serializer.save(updated_at=timezone.now()))

    def _single_default(self, obj):
        if obj.is_default:
            PrintTemplate.objects.filter(doc_type=obj.doc_type).exclude(pk=obj.pk).update(is_default=False)

    def perform_destroy(self, instance):
        if instance.is_system:
            raise ValidationError({"detail": "Șablonul livrat cu sistemul nu se șterge; îl puteți restaura sau dezactiva."})
        instance.delete()

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        tpl = self.get_object()
        if not tpl.is_system:
            raise ValidationError({"detail": "Doar șabloanele livrate cu sistemul se pot restaura."})
        tpl.body, tpl.css, tpl.updated_at = tpl.original_body, tpl.original_css, timezone.now()
        tpl.save(update_fields=["body", "css", "updated_at"])
        return Response(self.get_serializer(tpl).data)

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        tpl = self.get_object()
        copy = PrintTemplate.objects.create(
            doc_type=tpl.doc_type, code=f"{tpl.code}-copie-{timezone.now():%H%M%S}"[:40], name=f"{tpl.name} (copie)",
            body=tpl.body, css=tpl.css, orientation=tpl.orientation, default_options=tpl.default_options,
            texts=tpl.texts, style=tpl.style, columns=tpl.columns,
        )
        return Response(self.get_serializer(copy).data, status=201)

    @action(detail=False, methods=["get"])
    def fields(self, request):
        """Coloanele alese în editor — formele de cadre nu au (deocamdată) tabele cu coloane configurabile."""
        return Response({"groups": [], "defaults": [], "supports_columns": False})

    @action(detail=False, methods=["get"], url_path="doc-types")
    def doc_types(self, request):
        return Response([{"code": c, "name": n, "ready": c in SAMPLE_BUILDERS} for c, n in DOC_TYPES])


def html_response(html: str) -> HttpResponse:
    response = HttpResponse(html, content_type="text/html; charset=utf-8")
    response["Content-Security-Policy"] = CSP
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "no-store"
    return response


def _ctx(context, tpl, lang):
    """Textele editabile ale șablonului (titlu, textul de la sfârșit...) și stilul lui, puse în context."""
    from . import texts

    return texts.apply(context, tpl.doc_type, tpl.texts, tpl.style, lang)


def template_for(doc_type, template_id=None):
    qs = PrintTemplate.objects.filter(doc_type=doc_type, is_active=True)
    tpl = qs.filter(pk=template_id).first() if template_id else None
    tpl = tpl or qs.filter(is_default=True).first() or qs.first()
    if tpl is None:
        raise ValidationError({"detail": "Nu există niciun șablon activ pentru acest document."})
    return tpl


def print_document(request, doc_type, context, *, template_id=None, title="", lang=None):
    """Tipărește un document cu șablonul ales (sau cel implicit): modulele cheamă funcția asta din vederile lor."""
    lang = lang or (request.query_params.get("lang") if request.query_params.get("lang") in ("ro", "ru", "en") else "ro")
    tpl = template_for(doc_type, template_id)
    try:
        html = render(tpl.body, tpl.css, _ctx(context, tpl, lang), orientation=tpl.orientation, lang=lang, title=title)
    except PrintError as exc:
        raise ValidationError({"detail": str(exc)}) from exc
    return html_response(html)


class PreviewView(APIView):
    """Previzualizarea unui șablon în editor, cu date reale (primele rânduri)."""

    def post(self, request):
        require(request.user, "settings.edit")
        doc_type = request.data.get("doc_type")
        builder = SAMPLE_BUILDERS.get(doc_type)
        if not builder:
            raise ValidationError({"detail": "Previzualizarea pentru acest document apare odată cu modulul lui."})
        lang = request.data.get("lang") if request.data.get("lang") in ("ro", "ru", "en") else "ro"
        defaults = {**DEFAULT_OPTIONS.get(doc_type, {}), **(request.data.get("options") or {})}
        try:
            context = builder(request, lang, defaults)
            from . import texts

            context = texts.apply(context, doc_type, request.data.get("texts"), request.data.get("style"), lang)
            html = render(request.data.get("body", ""), request.data.get("css", ""), context,
                          orientation=request.data.get("orientation", "portrait"), lang=lang, title="Preview")
        except (PrintError, ValueError) as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return html_response(html)
