import datetime
import mimetypes

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.http import FileResponse, Http404
from django.utils._os import safe_join
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import require
from apps.users.registry import MODULES

from . import bnm
from .deletion import DeletionMarkMixin
from . import license as license_service
from .models import (AuditLog, BankAccount, Company, Currency, ExchangeRate, Notification, NumberSeries,
                     PaymentMethod, VatRate)
from .serializers import (LOGO_FIELDS, AuditLogSerializer, BankAccountSerializer, BrandingSerializer,
                          CompanySerializer, CurrencySerializer, ExchangeRateSerializer, NotificationSerializer,
                          NumberSeriesSerializer, PaymentMethodSerializer, VatRateSerializer)


class SettingsPermMixin:
    """Nomenclatoarele de sistem: citire cu settings.view, modificare cu settings.edit."""

    perm_module = "settings"
    perm_actions = {"create": "edit", "update": "edit", "partial_update": "edit", "destroy": "edit"}


class BrandingView(APIView):
    public = True
    authentication_classes = []

    def get(self, request):
        data = BrandingSerializer(Company.get(), context={"request": request}).data
        data["version"] = settings.APP_VERSION
        return Response(data)


class RequiredFieldsView(APIView):
    """Câmpurile obligatorii (Administrare → Câmpuri obligatorii): GET catalogul și bifele; PUT {"selected": {...}}."""

    def get(self, request):
        from . import required

        return Response({"docs": required.catalog(), "selected": required.selected()})

    def put(self, request):
        from apps.users.permissions import require

        from . import required

        require(request.user, "settings.edit")
        return Response({"docs": required.catalog(), "selected": required.save(request.data.get("selected") or {})})


class MenuLayoutView(APIView):
    """Meniul principal (ca în 1C): secțiunile cu funcțiile lor, așezate de administrator. Fiecare secțiune are două
    grupe: Registre (items) și Rapoarte (reports); setările nu stau în secțiuni, ci toate la Administrare → Setări.
    {"version": 2, "sections": [{"key", "name_ro", "name_ru", "icon", "items": [...], "reports": [...]}],
     "layout": "top" | "left"}; fără secțiuni = așezarea implicită. Secțiunile salvate înainte de grupe (fără „version”)
    nu se mai folosesc: toți primesc meniul standard nou (așezarea sus / în stânga rămâne). Meniurile cu grupa Setări (până
    la 1.4.0) le-a adus la zi migrația users 0004 (apps/core/moved.py)."""

    KEY = "menu_layout"
    VERSION = 2
    GROUPS = ("items", "reports")

    def _read(self):
        from .models import SystemSetting

        saved = SystemSetting.read(self.KEY, {}) or {}
        if saved.get("version") != self.VERSION:
            return {k: v for k, v in saved.items() if k == "layout"}
        return saved

    def get(self, request):
        return Response(self._read())

    def put(self, request):
        import re

        from apps.users.permissions import require

        from .models import SystemSetting

        require(request.user, "settings.edit")
        current = self._read()
        layout = request.data.get("layout", current.get("layout"))
        extra = {"layout": layout} if layout in ("top", "left") else {}
        if "sections" not in request.data:  # doar așezarea meniului (secțiunile sus / în stânga) pentru toți
            SystemSetting.write(self.KEY, {**{k: v for k, v in current.items() if k != "layout"}, **extra})
            return Response(self._read())
        sections = request.data.get("sections")
        if sections is None:  # revenirea la așezarea implicită
            SystemSetting.write(self.KEY, extra)
            return Response(extra)
        if not isinstance(sections, list) or len(sections) > 40:
            raise ValidationError({"detail": "Secțiunile meniului sunt greșite."})
        from . import moved

        clean, seen = [], set()
        for sec in moved.sections(sections):  # editorul de pe programul vechi trimite și grupa Setări
            if not isinstance(sec, dict):
                raise ValidationError({"detail": "Secțiunile meniului sunt greșite."})
            key = str(sec.get("key", ""))[:40]
            if not re.fullmatch(r"[a-z0-9_-]+", key) or key in seen:
                raise ValidationError({"detail": f"Cheia secțiunii „{key}” e greșită sau se repetă."})
            seen.add(key)
            groups = {g: list(dict.fromkeys(str(x)[:40] for x in (sec.get(g) or []) if isinstance(x, str)))[:80] for g in self.GROUPS}
            clean.append({"key": key, "name_ro": str(sec.get("name_ro", ""))[:60], "name_ru": str(sec.get("name_ru", ""))[:60],
                          "icon": str(sec.get("icon", ""))[:30], **groups})
        saved = {"version": self.VERSION, "sections": clean, **extra}
        SystemSetting.write(self.KEY, saved)
        return Response(saved)


class CompanyView(SettingsPermMixin, APIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        return Response(CompanySerializer(Company.get(), context={"request": request}).data)

    def patch(self, request):
        require(request.user, "settings.edit")
        company = Company.get()
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        # Câmp de fișier trimis gol = ștergerea imaginii.
        for field in LOGO_FIELDS:
            if field in data and data.get(field) in ("", "null"):
                try:
                    getattr(company, field).delete(save=False)
                except OSError:  # fișierul e ocupat (Windows); rămâne pe disc, legătura se șterge
                    pass
                setattr(company, field, "")
                data.pop(field)
        ser = CompanySerializer(company, data=data, partial=True, context={"request": request})
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(CompanySerializer(Company.get(), context={"request": request}).data)


class CompanyImageView(SettingsPermMixin, APIView):
    """Semnătura și ștampila din Constante (partea privată): le vede cine vede setările; în forme intră puse în pagină."""

    def get(self, request, field):
        from .private_files import serve

        if field not in ("signature", "stamp"):
            raise Http404
        return serve(getattr(Company.get(), field))


class BankAccountViewSet(SettingsPermMixin, viewsets.ModelViewSet):
    serializer_class = BankAccountSerializer
    pagination_class = None

    def get_queryset(self):
        return BankAccount.objects.filter(company=Company.get())

    def perform_create(self, serializer):
        self._save(serializer, company=Company.get())

    def perform_update(self, serializer):
        self._save(serializer)

    def _save(self, serializer, **extra):
        obj = serializer.save(**extra)
        if obj.is_default:
            BankAccount.objects.filter(company=obj.company).exclude(pk=obj.pk).update(is_default=False)


class CurrencyViewSet(SettingsPermMixin, viewsets.ModelViewSet):
    serializer_class = CurrencySerializer
    queryset = Currency.objects.all()
    pagination_class = None

    def perform_destroy(self, instance):
        if instance.is_base:
            raise ValidationError({"detail": "Valuta de bază nu se poate șterge."})
        instance.delete()


class ExchangeRateViewSet(SettingsPermMixin, viewsets.ModelViewSet):
    serializer_class = ExchangeRateSerializer
    perm_actions = {**SettingsPermMixin.perm_actions, "fetch_bnm": "edit"}

    def get_queryset(self):
        qs = ExchangeRate.objects.select_related("currency")
        params = self.request.query_params
        if params.get("currency"):
            qs = qs.filter(currency__code=params["currency"].upper())
        if params.get("date_from"):
            qs = qs.filter(date__gte=params["date_from"])
        if params.get("date_to"):
            qs = qs.filter(date__lte=params["date_to"])
        return qs

    def perform_create(self, serializer):
        serializer.save(source="manual")

    @action(detail=False, methods=["post"], url_path="fetch-bnm")
    def fetch_bnm(self, request):
        try:
            day = datetime.date.fromisoformat(request.data.get("date")) if request.data.get("date") else None
        except ValueError as exc:
            raise ValidationError({"date": "Dată incorectă."}) from exc
        try:
            saved = bnm.update_rates(day)
        except bnm.BnmError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response({"saved": saved, "date": (day or datetime.date.today()).isoformat()})


class VatRateViewSet(SettingsPermMixin, viewsets.ModelViewSet):
    serializer_class = VatRateSerializer
    queryset = VatRate.objects.all()
    pagination_class = None

    def perform_create(self, serializer):
        self._save(serializer)

    def perform_update(self, serializer):
        self._save(serializer)

    def _save(self, serializer):
        obj = serializer.save()
        if obj.is_default:
            VatRate.objects.exclude(pk=obj.pk).update(is_default=False)


class PaymentMethodViewSet(SettingsPermMixin, viewsets.ModelViewSet):
    serializer_class = PaymentMethodSerializer
    queryset = PaymentMethod.objects.all()
    pagination_class = None

    def check_permissions(self, request):
        # lista o citește și cine înregistrează plăți / facturi, fără acces la setări
        user = request.user
        if request.method == "GET" and user.is_authenticated and (
                user.has_crm_perm("payments.view") or user.has_crm_perm("invoices.view")):
            return
        super().check_permissions(request)

    def perform_destroy(self, instance):
        instance.is_active = False  # se păstrează pentru plățile vechi
        instance.save(update_fields=["is_active"])


class NumberSeriesViewSet(SettingsPermMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                          mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = NumberSeriesSerializer
    queryset = NumberSeries.objects.all()
    pagination_class = None


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    perm_module = "audit"

    def get_queryset(self):
        qs = AuditLog.objects.all()
        params = self.request.query_params
        for param, lookup in (("user", "user_id"), ("action", "action"), ("model", "model"),
                              ("object_id", "object_id")):
            if params.get(param):
                qs = qs.filter(**{lookup: params[param]})
        if params.get("date_from"):
            qs = qs.filter(timestamp__date__gte=params["date_from"])
        if params.get("date_to"):
            qs = qs.filter(timestamp__date__lte=params["date_to"])
        if params.get("search"):
            qs = qs.filter(object_repr__icontains=params["search"])
        return qs

    @action(detail=False, methods=["get"])
    def models(self, request):
        # fără ordinea implicită (data): altfel DISTINCT se face pe (model, dată) și întoarce tot jurnalul
        return Response(sorted(AuditLog.objects.order_by().values_list("model", flat=True).distinct()))


class HistoryView(APIView):
    """Istoricul unui obiect: GET /history/?model=billing.Invoice&id=5 → modificările lui și ale rândurilor lui."""

    def get(self, request):
        from . import history

        model, object_id = request.query_params.get("model", ""), request.query_params.get("id", "")
        try:
            return Response(history.for_object(request.user, model, object_id))
        except history.HistoryError as exc:
            raise ValidationError({"detail": str(exc)}) from exc


class HistoryRestoreView(APIView):
    """POST /history/<id>/restore/ — revenirea obiectului la versiunea din jurnal (doar administratorul)."""

    def post(self, request, pk):
        from . import history

        try:
            return Response(history.restore(request.user, pk))
        except history.HistoryError as exc:
            raise ValidationError({"detail": str(exc)}) from exc


class CommentsView(APIView):
    """Conversația despre un obiect: GET ?model=&id= (mesajele), POST {"model", "id", "text", "mentions"?, "link"?},
    DELETE ?comment=<id> (mesajul propriu sau administratorul)."""

    def get(self, request):
        from . import conversations, history

        p = request.query_params
        try:
            if p.get("count") == "1":
                return Response({"count": conversations.count(request.user, p.get("model", ""), p.get("id", ""))})
            return Response(conversations.listing(request.user, p.get("model", ""), p.get("id", "")))
        except history.HistoryError as exc:
            raise ValidationError({"detail": str(exc)}) from exc

    def post(self, request):
        from . import conversations, history

        d = request.data
        try:
            conversations.post(request.user, d.get("model", ""), d.get("id", ""), d.get("text", ""), d.get("mentions") or [],
                               d.get("link") or "")
            return Response(conversations.listing(request.user, d.get("model", ""), d.get("id", "")), status=201)
        except history.HistoryError as exc:
            raise ValidationError({"detail": str(exc)}) from exc

    def delete(self, request):
        from . import conversations, history

        try:
            conversations.delete(request.user, request.query_params.get("comment"))
        except history.HistoryError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response(status=204)


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        if self.request.query_params.get("unread") == "1":
            qs = qs.filter(is_read=False)
        return qs

    @action(detail=False, methods=["get"])
    def count(self, request):
        return Response({"unread": Notification.objects.filter(user=request.user, is_read=False).count()})

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        Notification.objects.filter(user=request.user, pk=pk).update(is_read=True)
        return Response({"ok": True})

    @action(detail=False, methods=["post"])
    def send(self, request):
        """Mesaj către colegi: {"users": [id...], "title", "message"?, "link"?}."""
        from . import conversations, history

        try:
            sent = conversations.send_message(request.user, request.data.get("users"), request.data.get("title"),
                                              request.data.get("message") or "", request.data.get("link") or "")
        except history.HistoryError as exc:
            raise ValidationError({"detail": str(exc)}) from exc
        return Response({"sent": sent})

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"ok": True})


class PeriodSettingsView(APIView):
    """Ora documentelor după tip și data interzicerii modificării (general, pe module, pe utilizatori)."""

    def get(self, request):
        from . import periods

        require(request.user, "settings.view")
        return Response({"doc_times": periods.doc_times(), "closing": periods.closing(), "modules": periods.MODULES})

    def put(self, request):
        from . import periods

        require(request.user, "settings.edit")
        try:
            data = periods.write_settings(request.data)
        except (ValueError, TypeError) as exc:
            raise ValidationError({"detail": f"Date sau ore greșite: {exc}"}) from exc
        from . import audit

        audit.write("update", None, changes={"periods": request.data}, model_label="core.periods", object_repr="Perioade",
                    user=request.user)
        return Response({**data, "modules": periods.MODULES})


class LicenseView(APIView):
    def get(self, request):
        require(request.user, "settings.view")
        return Response(license_service.with_usage())

    def post(self, request):
        require(request.user, "settings.edit")
        try:
            return Response(license_service.with_usage(license_service.install(request.data.get("license", ""))))
        except license_service.LicenseError as exc:
            raise ValidationError({"license": str(exc)}) from exc


class SystemInfoView(APIView):
    perm_module = "settings"

    def get(self, request):
        from config.dbconfig import ENGINES
        from config.instance import load_config

        db = load_config().get("db", {})
        return Response({
            "version": settings.APP_VERSION,
            "database": {
                "engine": ENGINES.get(db.get("engine"), {}).get("label", db.get("engine")),
                "host": db.get("host", ""),
                "name": db.get("name", ""),
                "vendor_version": _db_version(),
            },
            "license": license_service.with_usage(),
        })


def _db_version():
    from apps.setup.dbtools import _version

    try:
        connection.ensure_connection()
        return _version(connection)
    except Exception:  # noqa: BLE001
        return ""


class DashboardView(APIView):
    """Panoul de start: ce tab-uri vede utilizatorul și cu ce nivel de acces (doar ale lui / toate).
    Datele tab-urilor se completează pe măsură ce apar modulele (clienți, oferte, comenzi)."""

    TABS = [
        ("employees", "employees"),
        ("orders", "orders"),
        ("leave", "leave"),
    ]
    def get(self, request):
        user = request.user
        tabs = []
        for tab, module in self.TABS:
            if module not in MODULES or not user.has_crm_perm(f"{module}.view"):
                continue
            scope = user.data_scope(module) if MODULES[module][3] else "all"
            tabs.append({"key": tab, "scope": scope, "ready": False, "data": None})
        return Response({"tabs": tabs})


def media(request, path):
    """Logo-urile întreprinderii (company/), servite fără autentificare, cu antete de siguranță (SVG fără scripturi). Orice
    alt fișier încărcat (fotografiile, scanările, semnătura, ștampila, fișierele tahografului — private/) se dă doar prin API,
    cu drepturi (apps.core.private_files): aici — 404."""
    try:
        full = safe_join(str(settings.MEDIA_ROOT), path)
    except Exception as exc:  # noqa: BLE001
        raise Http404 from exc
    import os

    public = os.path.normcase(os.path.join(os.path.realpath(settings.MEDIA_ROOT), "company")) + os.sep
    if not os.path.normcase(os.path.realpath(full)).startswith(public) or not os.path.isfile(full):
        raise Http404
    content_type, _ = mimetypes.guess_type(full)
    response = FileResponse(open(full, "rb"), content_type=content_type or "application/octet-stream")
    response["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; img-src data:"
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "public, max-age=3600"
    return response


class LocalityViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    """Clasificatorul localităților: îl citește oricine (alegerea în client / comandă, cu căutare); îl schimbă cine are
    settings.edit. ?search= (nume, raion / județ, comună), ?country=MD|RO."""

    def get_serializer_class(self):
        from rest_framework import serializers

        from .models import Locality

        class LocalitySerializer(serializers.ModelSerializer):
            label = serializers.CharField(read_only=True)

            class Meta:
                model = Locality
                fields = ["id", "country", "code", "name", "name_ru", "kind", "region", "region_ru", "commune",
                          "postal_code", "custom", "label", "deletion_mark"]
                read_only_fields = ["custom", "deletion_mark"]
                extra_kwargs = {"code": {"required": False}}
                validators = []  # codul e unic doar când e completat (constrângerea din baza de date)

        return LocalitySerializer

    def get_queryset(self):
        from django.db.models import Case, IntegerField, Q, Value, When

        from .models import Locality

        qs = Locality.objects.all()
        p = self.request.query_params
        if p.get("country"):
            qs = qs.filter(country=p["country"])
        text = (p.get("search") or "").strip()
        if text:
            for word in text.replace(",", " ").split()[:4]:
                qs = qs.filter(Q(name__icontains=word) | Q(name_ru__icontains=word) | Q(region__icontains=word)
                               | Q(commune__icontains=word) | Q(postal_code__startswith=word))
            # întâi cele care încep cu textul, apoi orașele înaintea satelor
            first = text.split()[0]
            qs = qs.annotate(_starts=Case(When(name__istartswith=first, then=Value(0)), default=Value(1),
                                          output_field=IntegerField()),
                             _kind=Case(When(kind__in=("municipiu", "oraș"), then=Value(0)), default=Value(1),
                                        output_field=IntegerField())).order_by("_starts", "_kind", "name")
        return qs

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            require(request.user, "settings.edit")

    def perform_create(self, serializer):
        serializer.save(custom=True)


class LocalitiesLoadView(APIView):
    """Constante → Localități: GET câte sunt în liste și câte sunt încărcate; POST {"countries": ["MD", "RO"]} încarcă
    țările bifate și scoate pe cele debifate (localitățile adăugate de mână rămân)."""

    def get(self, request):
        from . import localities

        return Response(localities.status())

    def post(self, request):
        from . import localities

        require(request.user, "settings.edit")
        wanted = {c for c in (request.data.get("countries") or []) if c in localities.FILES}
        for country in localities.FILES:
            if country in wanted:
                localities.load(country)
            else:
                localities.remove(country)
        return Response(localities.status())


class BankViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    """Clasificatorul băncilor: îl citește oricine (alegerea la contul bancar, cu căutare); îl schimbă cine are
    settings.edit. ?search= (denumire, BIC, IDNO / CUI, codul din IBAN), ?country=MD|RO, ?iban= (banca acelui IBAN)."""

    def get_serializer_class(self):
        from rest_framework import serializers

        from .models import Bank

        class BankSerializer(serializers.ModelSerializer):
            class Meta:
                model = Bank
                fields = ["id", "country", "code", "name", "short_name", "bic", "fiscal_code", "address", "phone",
                          "email", "website", "note", "custom", "deletion_mark"]
                read_only_fields = ["custom", "deletion_mark"]
                extra_kwargs = {"code": {"required": False}}
                validators = []  # codul e unic doar când e completat (constrângerea din baza de date)

            def validate(self, attrs):
                for f in ("country", "code", "bic"):
                    if attrs.get(f):
                        attrs[f] = attrs[f].strip().upper()
                return attrs

        return BankSerializer

    def get_queryset(self):
        from django.db.models import Q

        from . import banks
        from .models import Bank

        qs = Bank.objects.all()
        p = self.request.query_params
        if p.get("iban"):
            bank = banks.by_iban(p["iban"])
            return qs.filter(pk=bank.pk if bank else None)
        if p.get("country"):
            qs = qs.filter(country=p["country"])
        text = (p.get("search") or "").strip()
        for word in text.replace(",", " ").split()[:4]:
            qs = qs.filter(Q(name__icontains=word) | Q(short_name__icontains=word) | Q(bic__istartswith=word)
                           | Q(code__iexact=word) | Q(fiscal_code__startswith=word))
        return qs

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            require(request.user, "settings.edit")

    def perform_create(self, serializer):
        serializer.save(custom=True)


class BanksLoadView(APIView):
    """Administrare → Bănci: GET câte sunt în liste și câte sunt încărcate; POST {"countries": ["MD", "RO"]} încarcă
    (actualizează) țările bifate și scoate pe cele debifate (băncile adăugate de mână rămân)."""

    def get(self, request):
        from . import banks

        return Response(banks.status())

    def post(self, request):
        from . import banks

        require(request.user, "settings.edit")
        lists = banks.read()
        wanted = {c for c in (request.data.get("countries") or []) if c in lists}
        for country in lists:
            if country in wanted:
                banks.load(country)
            else:
                banks.remove(country)
        return Response(banks.status())


class OnlineView(APIView):
    """Cine e online (Administrare): oamenii cu programul deschis în ultimele minute, sesiunile intrate fără semn de
    viață, cifrele zilei. Sesiunea = o intrare cu parola (o pereche de jetoane); se închide singură când jetonul de
    reîmprospătare expiră (7 zile fără nicio cerere) sau de aici, cu „Închide”."""

    perm_module = "users"
    ONLINE_MINUTES = 3

    def get(self, request):
        from django.utils import timezone

        from . import console
        from .models import UserSession

        now = timezone.now()
        online_from = now - datetime.timedelta(minutes=self.ONLINE_MINUTES)
        alive_from = now - settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]
        today_start = timezone.make_aware(datetime.datetime.combine(timezone.localdate(), datetime.time.min))
        current = console.current_sid()
        sessions = (UserSession.objects.filter(closed_at__isnull=True, last_seen__gte=alive_from)
                    .select_related("user").prefetch_related("user__roles").order_by("-last_seen")[:500])

        def row(s):
            roles = list(s.user.roles.all())
            return {
                "sid": s.sid, "current": s.sid == current, "ip": s.ip, "device": s.device, "user_agent": s.user_agent,
                "created_at": s.created_at.isoformat(), "last_seen": s.last_seen.isoformat(), "last_path": s.last_path,
                "user": {"id": s.user_id, "name": str(s.user), "username": s.user.username, "email": s.user.email,
                         "role_ro": roles[0].name_ro if roles else "", "role_ru": roles[0].name_ru if roles else "",
                         "is_admin": s.user.is_superuser or any(r.is_admin for r in roles)},
            }

        online = [row(s) for s in sessions if s.last_seen >= online_from]
        idle = [row(s) for s in sessions if s.last_seen < online_from]
        User = get_user_model()
        return Response({
            "now": now.isoformat(), "online_minutes": self.ONLINE_MINUTES,
            "stats": {
                "online": len({r["user"]["id"] for r in online}),
                "worked_today": UserSession.objects.filter(last_seen__gte=today_start).values("user_id").distinct().count(),
                "sessions": len(online) + len(idle),
                "accounts": User.objects.filter(is_active=True).count(),
            },
            "online": online, "idle": idle,
        })

    def post(self, request):
        """Închide o sesiune (telefonul pierdut, calculatorul străin): jetoanele ei nu mai sunt primite."""
        from . import console

        require(request.user, "users.edit")
        sid = str(request.data.get("sid") or "")
        if not sid:
            raise ValidationError({"sid": "Lipsește sesiunea."})
        if sid == console.current_sid():
            raise ValidationError({"sid": "Sesiunea dvs. se închide cu „Deconectare”."})
        who = str(request.user)
        return Response({"closed": console.close_session(sid, f"Închisă din „Cine e online” de {who}")})
