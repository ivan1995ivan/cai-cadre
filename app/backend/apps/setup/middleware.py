from django.conf import settings
from django.http import JsonResponse

ALLOWED_IN_SETUP = ("/api/setup/", "/api/help/")


class SetupModeMiddleware:
    """Cât timp sistemul nu e instalat, API-ul răspunde doar asistentului de instalare."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if settings.SETUP_MODE and path.startswith("/api/") and not path.startswith(ALLOWED_IN_SETUP):
            return JsonResponse(
                {"detail": "Sistemul nu este instalat.", "setup_required": True}, status=503
            )
        return self.get_response(request)
