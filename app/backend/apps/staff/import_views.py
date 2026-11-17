from django.http import HttpResponse
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core import excel_import
from apps.users.permissions import require

from .imports import SPECS


class ImportView(APIView):
    """Importul dosarelor din Excel: GET …/template/ — șablonul; POST (fișier) — încercarea (dry_run=1) sau importul."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _spec(self, code):
        spec = SPECS.get(code)
        if not spec:
            raise ValidationError({"detail": "Import necunoscut."})
        return spec

    def get(self, request, code):
        spec = self._spec(code)
        require(request.user, "imports.view")
        response = HttpResponse(excel_import.template(spec),
                                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = f'attachment; filename="sablon-{code}.xlsx"'
        return response

    def post(self, request, code):
        spec = self._spec(code)
        require(request.user, "imports.create")
        require(request.user, "employees.create" if code == "employees" else "employees.edit")
        upload = request.FILES.get("file")
        if not upload:
            raise ValidationError({"file": "Alegeți fișierul Excel (.xlsx)."})
        if upload.size > 10 * 1024 * 1024:
            raise ValidationError({"file": "Fișierul e prea mare (cel mult 10 MB)."})
        context = {"user": request.user,
                   "create_occupations": str(request.data.get("create_occupations")) in ("1", "true", "True")}
        dry_run = str(request.data.get("dry_run", "1")) in ("1", "true", "True")
        return Response(excel_import.run(spec, upload.read(), dry_run=dry_run, context=context))
