from django.conf import settings
from django.http import FileResponse, Http404, JsonResponse
from django.urls import include, path, re_path

from apps.core import console
from apps.core.views import media


def spa(request, *args, **kwargs):
    """Interfața web (React): orice rută necunoscută primește index.html.

    Un fișier al interfeței (are extensie: /assets/index-abc.js) nu primește niciodată index.html: dacă WhiteNoise nu-l
    cunoaște (interfața s-a construit după pornirea serverului), se servește direct din frontend/dist; dacă lipsește — 404.
    Altfel browserul primea HTML în loc de JavaScript și pagina rămânea albă."""
    import mimetypes
    import posixpath

    from django.utils._os import safe_join

    name = request.path.lstrip("/")
    if posixpath.splitext(name)[1]:
        try:
            path = safe_join(str(settings.FRONTEND_DIST), name)
        except Exception:  # noqa: BLE001 — cale în afara folderului interfeței
            raise Http404 from None
        from pathlib import Path

        file = Path(path)
        if not file.is_file():
            raise Http404
        content_type = settings.WHITENOISE_MIMETYPES.get(file.suffix) or mimetypes.guess_type(file.name)[0]             or "application/octet-stream"
        if file.suffix in (".js", ".mjs"):
            content_type = "text/javascript"
        return FileResponse(open(file, "rb"), content_type=content_type)
    index = settings.FRONTEND_DIST / "index.html"
    if not index.exists():
        return JsonResponse(
            {"detail": "Interfața web nu este compilată. Rulați `npm run build` în frontend/ "
                       "sau porniți `npm run dev` pentru dezvoltare."},
            status=503,
        )
    return FileResponse(open(index, "rb"), content_type="text/html")


def api_not_found(request, *args, **kwargs):
    raise Http404


def health(request):
    """Verificarea containerului și a nginx-ului (GET /health → 200), și în modul instalare."""
    return JsonResponse({"status": "ok", "version": settings.APP_VERSION, "installed": not settings.SETUP_MODE})


urlpatterns = [
    path("health", health),
    path(console.INTERNAL_PATH.lstrip("/"), console.internal),
    path("api/setup/", include("apps.setup.urls")),
    path("api/help/", include("apps.help.urls")),
    path("api/", include("apps.users.urls")),
    path("api/", include("apps.core.urls")),
    path("api/", include("apps.printing.urls")),
    path("api/org/", include("apps.org.urls")),
    path("api/staff/", include("apps.staff.urls")),
    path("api/orders/", include("apps.orders.urls")),
    path("api/leave/", include("apps.leave.urls")),
    path("api/worktime/", include("apps.worktime.urls")),
    path("api/payroll/", include("apps.payroll.urls")),
    path("api/production/", include("apps.production.urls")),
    path("api/alerts/", include("apps.alerts.urls")),
    path("api/reports/", include("apps.reports.urls")),
    path("api/training/", include("apps.training.urls")),
    path("api/health/", include("apps.health.urls")),
    path("api/portal/", include("apps.portal.urls")),
    path("api/system/", include("apps.setup.maintenance")),
    re_path(r"^api/", api_not_found),
    re_path(r"^media/(?P<path>.+)$", media),
    re_path(r"^.*$", spa),
]
