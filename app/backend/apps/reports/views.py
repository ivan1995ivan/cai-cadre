from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from . import output, registry


def _check(user, key):
    rep = registry.REPORTS.get(key)
    if rep is not None and not user.has_crm_perm(rep.perm):
        raise PermissionDenied("Nu aveți acces la acest raport.")


class CatalogView(APIView):
    """Catalogul rapoartelor pe grupe (cele care au pagina lor în modul apar ca legături)."""

    def get(self, request):
        lang = request.query_params.get("lang") if request.query_params.get("lang") in ("ro", "ru", "en") else "ro"
        return Response(registry.catalog(request.user, lang))


class ReportView(APIView):
    """Datele raportului cu filtrele din query string; ?export=xlsx — fișierul Excel."""

    def get(self, request, key):
        _check(request.user, key)
        data = registry.run(key, registry.parse(request))
        if request.query_params.get("export") == "xlsx":
            module = registry.REPORTS[key].perm.split(".")[0]
            if not (request.user.has_crm_perm("reports.export") or request.user.has_crm_perm(f"{module}.export")):
                raise PermissionDenied("Exportul rapoartelor nu vă este permis.")
            return output.xlsx_response(data, f"{key}.xlsx")
        return Response(data)


class ReportPrintView(APIView):
    def get(self, request, key):
        from apps.printing.views import print_document

        _check(request.user, key)
        data = registry.run(key, registry.parse(request))
        return print_document(request, "report", output.print_context(data), template_id=request.query_params.get("template"),
                              title=data["title"])
