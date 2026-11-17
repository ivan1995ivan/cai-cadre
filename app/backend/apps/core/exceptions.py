import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_handler


def exception_handler(exc, context):
    """Erori uniforme: {"detail": "..."} sau {"câmp": ["..."]}, inclusiv pentru erorile Django."""
    if isinstance(exc, DjangoValidationError):
        data = exc.message_dict if hasattr(exc, "error_dict") else {"detail": " ".join(exc.messages)}
        return Response(data, status=status.HTTP_400_BAD_REQUEST)
    if isinstance(exc, IntegrityError):
        return Response(
            {"detail": "Înregistrarea intră în conflict cu datele existente (duplicat sau legătură)."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    response = drf_handler(exc, context)
    if response is None:
        # eroare neprevăzută: în server.log cu toată urma, iar interfața arată un mesaj, nu doar „Eroare”
        request = context.get("request")
        logging.getLogger("django.request").error("Internal Server Error: %s", getattr(request, "path", ""), exc_info=exc)
        return Response({"detail": f"Eroare internă pe server ({type(exc).__name__}). Detaliile sunt în jurnalul serverului "
                                   f"(server.log); trimiteți-le administratorului."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    # textul Django „No X matches the given query.” (get_object_or_404), netradus
    if response.status_code == 404 and isinstance(response.data, dict) \
            and str(response.data.get("detail", "")).startswith("No "):
        response.data["detail"] = "Înregistrarea nu există (poate a fost ștearsă). Reîncărcați pagina."
    code = exc.get_codes() if hasattr(exc, "get_codes") else None
    if response is not None and code in ("session_closed", "maintenance") and isinstance(response.data, dict):
        response.data["code"] = code  # interfața iese la pagina de intrare cu mesajul administratorului
    return response
