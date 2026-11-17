from django.conf import settings
from django.http import JsonResponse

SAFE = ("GET", "HEAD", "OPTIONS")


class LicenseMiddleware:
    """Licența expirată: sistemul rămâne deschis pentru citire, tipar și export, dar nu primește modificări.
    Modulul neinclus în licență: adresele lui răspund „nu este inclus în licență”."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if settings.SETUP_MODE or not path.startswith("/api/"):
            return self.get_response(request)
        from . import license

        module = license.api_module(path)
        unsafe = request.method not in SAFE and not path.startswith(license.READ_ONLY_ALLOWED)
        if module is None and not unsafe:
            return self.get_response(request)
        status = license.status()
        if module and module not in license.enabled_modules(status):
            return JsonResponse({"detail": "Modulul nu este inclus în licență.", "code": "license_module",
                                 "module": module}, status=403)
        if unsafe and not status["valid"]:
            return JsonResponse({"detail": "Licența nu este valabilă: sistemul este deschis doar pentru citire. "
                                           "Administratorul introduce licența în Administrare → Licență.",
                                 "code": "license_read_only"}, status=403)
        return self.get_response(request)
