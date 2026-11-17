from django.db.models import Count, Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.core import audit, console

from .auth import SessionTokenSerializer
from .models import Role, User
from .registry import ACTIONS, MODULES, SCOPES, SENSITIVE_FIELDS
from .serializers import ChangePasswordSerializer, MeSerializer, RoleSerializer, UserSerializer


class LoginView(TokenObtainPairView):
    """Intrarea în sistem; reușitele și eșecurile se scriu în jurnalul de audit."""

    serializer_class = SessionTokenSerializer
    public = True

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        username = str(request.data.get("username", ""))[:150]
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            audit.write("login_failed", model_label="users.User", object_repr=username, user=None)
            return Response({"detail": "Utilizator sau parolă greșită."}, status=status.HTTP_401_UNAUTHORIZED)
        user = serializer.user
        if console.blocked() and not user.is_crm_admin:
            return Response({"detail": console.block_message(), "code": "maintenance"},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        audit.write("login", user, user=user)
        console.open_session(RefreshToken(serializer.validated_data["refresh"])["sid"], user, request)
        return Response(serializer.validated_data)


def _active_admins(exclude_pk=None):
    qs = User.objects.filter(is_active=True).filter(Q(is_superuser=True) | Q(roles__is_admin=True)).distinct()
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs


class MeView(APIView):
    def get(self, request):
        return Response(MeSerializer(request.user).data)

    def patch(self, request):
        ser = MeSerializer(request.user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(MeSerializer(request.user).data)


class UiPrefsView(APIView):
    """Aranjarea interfeței utilizatorului curent (coloanele listelor, grupele formelor).
    GET → toate; PUT /ui-prefs/<cheie>/ {value} → salvează; DELETE /ui-prefs/<cheie>/ → revine la aranjarea implicită."""

    MAX_BYTES = 20000  # o aranjare are câteva sute de octeți; limita oprește datele greșite

    def get(self, request, key=None):
        prefs = request.user.ui_prefs or {}
        return Response(prefs.get(key) if key else prefs)

    def put(self, request, key):
        import json

        value = request.data.get("value")
        if len(key) > 200 or len(json.dumps(value)) > self.MAX_BYTES:
            raise ValidationError({"detail": "Aranjarea este prea mare."})
        prefs = dict(request.user.ui_prefs or {})
        prefs[key] = value
        request.user.ui_prefs = prefs
        request.user.save(update_fields=["ui_prefs"])
        return Response(value)

    def delete(self, request, key):
        prefs = dict(request.user.ui_prefs or {})
        if prefs.pop(key, None) is not None:
            request.user.ui_prefs = prefs
            request.user.save(update_fields=["ui_prefs"])
        return Response(status=204)


class UiDefaultsView(APIView):
    """Aranjarea implicită pentru toți (de ex. așezarea unei forme pusă de administrator): o folosește oricine nu și-a
    făcut-o pe a lui. GET → toate; PUT / DELETE /ui-defaults/<cheie>/ — cu dreptul de a modifica setările."""

    KEY = "ui_defaults"

    def get(self, request, key=None):
        from apps.core.models import SystemSetting

        data = SystemSetting.read(self.KEY, {}) or {}
        return Response(data.get(key) if key else data)

    def put(self, request, key):
        import json

        from apps.core.models import SystemSetting
        from apps.users.permissions import require

        require(request.user, "settings.edit")
        value = request.data.get("value")
        if len(key) > 200 or len(json.dumps(value)) > UiPrefsView.MAX_BYTES:
            raise ValidationError({"detail": "Aranjarea este prea mare."})
        data = dict(SystemSetting.read(self.KEY, {}) or {})
        data[key] = value
        SystemSetting.write(self.KEY, data)
        return Response(value)

    def delete(self, request, key):
        from apps.core.models import SystemSetting
        from apps.users.permissions import require

        require(request.user, "settings.edit")
        data = dict(SystemSetting.read(self.KEY, {}) or {})
        if data.pop(key, None) is not None:
            SystemSetting.write(self.KEY, data)
        return Response(status=204)


class XlsxExportView(APIView):
    """Lista așa cum se vede (coloanele vizibile, textul celulelor) → fișier Excel.
    POST {"title", "columns": [{"title", "width"}], "rows": [[...], ...]} → .xlsx"""

    MAX_ROWS = 100000

    def post(self, request):
        import io
        import re
        from decimal import Decimal, InvalidOperation

        from django.http import HttpResponse
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        from openpyxl.utils import get_column_letter

        columns = request.data.get("columns") or []
        rows = request.data.get("rows") or []
        if not columns or len(rows) > self.MAX_ROWS:
            raise ValidationError({"detail": "Nimic de exportat sau prea multe rânduri."})
        title = str(request.data.get("title") or "Lista")[:120]
        wb = Workbook()
        ws = wb.active
        ws.title = re.sub(r"[\\/*?:\[\]]", " ", title)[:31] or "Lista"
        ws.append([str(c.get("title") or "") for c in columns])
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="E8EEF5")
        number = re.compile(r"^-?\d[\d\s\u00a0]*([.,]\d+)?$")

        def value(v):
            if v is None:
                return ""
            text = str(v).strip()
            digits = re.sub(r"[\s\u00a0]", "", text)
            code = (len(digits) > 1 and digits.startswith("0") and digits[1] not in ".,") or (digits.isdigit() and len(digits) > 8)
            if number.match(text) and not code:
                try:  # sumele / cantitățile rămân numere (se pot aduna); IDNO, coduri de bare, coduri cu 0 în față — text
                    return Decimal(digits.replace(",", "."))
                except InvalidOperation:
                    return text
            return text[:32000]

        for row in rows:
            ws.append([value(v) for v in list(row)[:len(columns)]])
        for i, c in enumerate(columns, 1):
            width = c.get("width")
            ws.column_dimensions[get_column_letter(i)].width = max(8, min(60, (int(width) / 7) if width else 18))
        ws.freeze_panes = "A2"
        buffer = io.BytesIO()
        wb.save(buffer)
        safe = re.sub(r'[\\/:*?"<>|]+', "-", title)
        response = HttpResponse(buffer.getvalue(),
                                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = f'attachment; filename="{safe}.xlsx"'
        return response


class ChangePasswordView(APIView):
    def post(self, request):
        ser = ChangePasswordSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        request.user.set_password(ser.validated_data["new_password"])
        request.user.must_change_password = False
        request.user.save(update_fields=["password", "must_change_password"])
        return Response({"ok": True})


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    perm_module = "users"

    def get_queryset(self):
        qs = User.objects.prefetch_related("roles", "subdivisions")
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(username__icontains=search) | Q(first_name__icontains=search)
                           | Q(last_name__icontains=search) | Q(email__icontains=search)
                           | Q(phone__icontains=search))
        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(roles__id=role)
        active = self.request.query_params.get("active")
        if active in ("0", "1"):
            qs = qs.filter(is_active=active == "1")
        return qs

    def perform_update(self, serializer):
        user = serializer.instance
        was_admin = user.is_active and user.is_crm_admin
        data = serializer.validated_data
        if user.pk == self.request.user.pk and data.get("is_active") is False:
            raise ValidationError({"is_active": "Nu vă puteți dezactiva propriul cont."})
        new_roles = data.get("roles")
        stays_admin = (data.get("is_active", user.is_active)
                       and (user.is_superuser or any(r.is_admin for r in (new_roles if new_roles is not None
                                                                           else user.roles.all()))))
        if was_admin and not stays_admin and not _active_admins(exclude_pk=user.pk).exists():
            raise ValidationError({"detail": "Acesta este ultimul administrator activ. Numiți întâi alt administrator."})
        serializer.save()

    def perform_destroy(self, instance):
        if instance.pk == self.request.user.pk:
            raise ValidationError({"detail": "Nu vă puteți șterge propriul cont."})
        if instance.is_crm_admin and not _active_admins(exclude_pk=instance.pk).exists():
            raise ValidationError({"detail": "Nu se poate șterge ultimul administrator."})
        instance.delete()


class RoleViewSet(viewsets.ModelViewSet):
    serializer_class = RoleSerializer
    perm_module = "roles"

    def get_queryset(self):
        return Role.objects.prefetch_related("permissions").annotate(user_count=Count("users"))

    def perform_destroy(self, instance):
        if instance.is_system:
            raise ValidationError({"detail": "Un rol predefinit nu se poate șterge (îl puteți modifica)."})
        if instance.users.exists():
            raise ValidationError({"detail": "Rolul este atribuit unor utilizatori. Scoateți-l întâi de la ei."})
        instance.delete()

    @action(detail=False, methods=["get"])
    def catalog(self, request):
        """Modulele, acțiunile, nivelurile de acces și câmpurile sensibile, pentru matricea de drepturi."""
        return Response({
            "modules": [
                {"code": code, "name_ro": ro, "name_ru": ru, "actions": actions, "scoped": scoped}
                for code, (ro, ru, actions, scoped) in MODULES.items()
            ],
            "actions": {k: {"ro": v[0], "ru": v[1]} for k, v in ACTIONS.items()},
            "scopes": {k: {"ro": v[0], "ru": v[1]} for k, v in SCOPES.items()},
            "sensitive_fields": {k: {"ro": v[0], "ru": v[1]} for k, v in SENSITIVE_FIELDS.items()},
        })


class UserLookupViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Listă scurtă de utilizatori activi (pentru alegerea managerului etc.), fără drept special."""

    pagination_class = None

    def get_queryset(self):
        return User.objects.filter(is_active=True)

    def list(self, request, *args, **kwargs):
        return Response([{"id": u.id, "name": str(u), "username": u.username, "is_manager": u.is_manager}
                         for u in self.get_queryset()])
