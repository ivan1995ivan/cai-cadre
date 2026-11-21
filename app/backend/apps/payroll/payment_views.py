"""API-ul îndreptărilor spre plată (impozitele reținute la plată, achitarea, banca), al datoriilor și al raportărilor (anexa 8, IPC21, IALS21, IRM19)."""
from datetime import date

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.deletion import DeletionMarkMixin, ensure_not_marked
from apps.core.models import NumberSeries, SystemSetting
from apps.staff import services as staff
from apps.staff.models import Employee

from . import it_park_views, payment_printing, payments, payslip_mail, payslip_pdf, printing, reports, xml_export
from .models import Payment, PaymentLine
from .serializers import PaymentLineSerializer, PaymentSerializer


class PaymentViewSet(DeletionMarkMixin, viewsets.ModelViewSet):
    perm_module = "payroll"
    serializer_class = PaymentSerializer
    perm_actions = {"fill": "edit", "approve": "approve", "pay": "approve", "reopen": "approve", "lines": "view",
                    "print": "view", "bank_list": "view", "bank_file": "export", "payslip": "view", "payslip_pdf": "view",
                    "payslip_mail": "edit"}

    def get_queryset(self):
        qs = Payment.objects.select_related("payroll").prefetch_related("lines")
        p = self.request.query_params
        for key in ("year", "month", "kind", "status", "payroll"):
            if p.get(key):
                qs = qs.filter(**{key: p[key]})
        return qs

    def perform_create(self, serializer):
        doc = serializer.save(created_by=self.request.user, number=NumberSeries.next_number("payroll_payment"))
        payments.fill(doc)

    REFILL = ("kind", "method", "payroll", "year", "month")

    def perform_update(self, serializer):
        """Antetul ciornei; altă bază (calculul, felul, modalitatea, luna) completează rândurile din nou."""
        doc = serializer.instance
        ensure_not_marked(doc)
        if doc.status != "draft":
            raise ValidationError({"detail": "Se schimbă doar ciorna."})
        before = {f: getattr(doc, f) for f in self.REFILL}
        doc = serializer.save()
        if any(getattr(doc, f) != v for f, v in before.items()):
            payments.fill(doc)

    def check_delete(self, instance):
        if instance.status == "paid":
            raise ValidationError({"detail": "Plata achitată nu se șterge; redeschideți-o întâi."})

    @action(detail=True, methods=["get"])
    def lines(self, request, pk=None):
        doc = self.get_object()
        return Response(PaymentLineSerializer(doc.lines.select_related("employee").order_by("sort", "id"), many=True).data)

    @action(detail=True, methods=["post"])
    def fill(self, request, pk=None):
        doc = self.get_object()
        n = payments.fill(doc)
        return Response({"lines": n, **PaymentSerializer(doc).data})

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        doc = self.get_object()
        if doc.status != "draft":
            raise ValidationError({"detail": "Se aprobă doar ciorna."})
        if not doc.lines.exists():
            raise ValidationError({"detail": "Îndreptarea spre plată nu are rânduri."})
        doc.status = "approved"
        doc.save(update_fields=["status"])
        return Response(PaymentSerializer(doc).data)

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        """Achitarea: data și documentul de plată (ordinul de plată pentru bancă / dispoziția de casă)."""
        doc = self.get_object()
        if doc.status != "approved":
            raise ValidationError({"detail": "Se achită îndreptarea spre plată aprobată."})
        try:
            doc.paid_on = date.fromisoformat(str(request.data.get("paid_on") or timezone.localdate())[:10])
        except ValueError:
            raise ValidationError({"paid_on": "Data se scrie AAAA-LL-ZZ."}) from None
        doc.reference = str(request.data.get("reference") or doc.reference)[:120]
        doc.status = "paid"
        doc.save(update_fields=["status", "paid_on", "reference"])
        return Response(PaymentSerializer(doc).data)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        doc = self.get_object()
        doc.status, doc.paid_on = "draft", None
        doc.save(update_fields=["status", "paid_on"])
        return Response(PaymentSerializer(doc).data)

    @action(detail=True, methods=["get"])
    def print(self, request, pk=None):
        return payment_printing.print_payment(request, self.get_object())

    @action(detail=True, methods=["get"], url_path="bank-list")
    def bank_list(self, request, pk=None):
        return payment_printing.print_bank_list(request, self.get_object())

    @action(detail=True, methods=["get"], url_path="bank-file")
    def bank_file(self, request, pk=None):
        return payments.bank_file(self.get_object())

    # --- fluturașii: din îndreptarea pe salariu, pentru angajații ei, cu toată luna lor ---------------------------------
    def _salary(self) -> Payment:
        doc = self.get_object()
        if doc.kind != "salary":
            raise ValidationError({"detail": "Fluturașii se fac din îndreptarea spre plată pe salariu."})
        return doc

    @staticmethod
    def _employee(request):
        emp = request.query_params.get("employee")
        return [int(emp)] if emp and emp.isdigit() else None

    @action(detail=True, methods=["get"])
    def payslip(self, request, pk=None):
        """Tiparul fluturașilor (toți sau ?employee=…)."""
        doc = self._salary()
        return printing.print_payslips(request, doc.year, doc.month, printing.payment_slip_lines(doc, self._employee(request)))

    @action(detail=True, methods=["get"], url_path="payslip-pdf")
    def payslip_pdf(self, request, pk=None):
        """Fluturașii în PDF (toți sau ?employee=…), fiecare angajat pe pagina lui."""
        doc = self._salary()
        response = HttpResponse(payslip_pdf.build(doc, self._employee(request)), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="fluturasi-{doc.year}-{doc.month:02d}-{doc.number or doc.pk}.pdf"'
        return response

    @action(detail=True, methods=["get", "post"], url_path="payslip-mail")
    def payslip_mail(self, request, pk=None):
        """GET — cine poate primi fluturașul pe e-mail; POST {employees: [...]} — trimite (câte cel mult 25 o dată)."""
        doc = self._salary()
        if request.method == "GET":
            return Response(payslip_mail.summary(doc))
        ids = [int(x) for x in (request.data.get("employees") or []) if str(x).isdigit()]
        return Response({"results": payslip_mail.send(doc, ids, request.user)})


class PaymentLineViewSet(viewsets.ModelViewSet):
    perm_module = "payroll"
    serializer_class = PaymentLineSerializer
    pagination_class = None
    http_method_names = ["get", "patch", "delete", "head", "options"]
    perm_actions = {"partial_update": "edit", "destroy": "edit"}

    def get_queryset(self):
        qs = PaymentLine.objects.select_related("payment", "employee")
        if self.request.query_params.get("payment"):
            return qs.filter(payment_id=self.request.query_params["payment"])
        return qs.none() if self.action == "list" else qs

    def _draft(self, line):
        ensure_not_marked(line.payment)
        if line.payment.status != "draft":
            raise ValidationError({"detail": "Se schimbă doar ciorna."})

    def perform_update(self, serializer):
        """Brutul, netul, impozitele, reținerile, modalitatea: corectarea se face în payments.update_line, care reface sumele."""
        self._draft(serializer.instance)
        payments.update_line(serializer.instance, self.request.data)

    def perform_destroy(self, instance):
        self._draft(instance)
        instance.delete()


def _ym(request):
    p = request.query_params
    today = timezone.localdate()
    try:
        return int(p.get("year") or today.year), int(p.get("month") or today.month)
    except ValueError:
        raise ValidationError({"month": "Luna sau anul nu sunt valide."}) from None


class DebtsView(APIView):
    """Datoriile salariale pe angajat la sfârșitul lunii (calculat și aprobat minus achitat)."""

    perm_module = "payroll"

    def get(self, request):
        year, month = _ym(request)
        rows = payments.debts(year, month)
        return Response({"year": year, "month": month, "rows": rows, "total": round(sum(r["debt"] for r in rows), 2)})


class AnnualCardView(APIView):
    """Fișa personală anuală a veniturilor (anexa 8): JSON sau tipar (?print=1)."""

    perm_module = ("payroll", "tax_reports")

    def get(self, request, employee):
        emp = Employee.objects.filter(pk=employee).first()
        if emp is None or not staff.can_see(emp, request.user, "payroll"):
            raise NotFound()
        year = int(request.query_params.get("year") or timezone.localdate().year)
        if request.query_params.get("print"):
            return payment_printing.print_annual_card(request, emp, year)
        return Response(reports.annual_card(emp, year))


class TaxReportView(APIView):
    """IPC21 (lunar), IALS21 (anual), IRM19 (pe perioadă), IU17 și ISAPTI17 (IT Park): previzualizare (JSON), Excel (?export=xlsx) sau declarația
    electronică XML după schema SFS (?export=xml)."""

    perm_module = "tax_reports"

    def get(self, request, report):
        p = request.query_params
        kind = p.get("export")
        xlsx, xml = kind == "xlsx", kind == "xml"
        if (xlsx or xml) and not request.user.has_crm_perm("tax_reports.export"):
            raise PermissionDenied("Nu aveți drept de export.")
        if report == "ipc21":
            year, month = _ym(request)
            if xml:
                return xml_export.ipc21_xml(year, month)
            data = reports.ipc21(year, month)
            return reports.ipc21_xlsx(data) if xlsx else Response(data)
        if report == "ials21":
            year, _month = _ym(request)
            if xml:
                return xml_export.ials21_xml(year)
            data = reports.ials21(year)
            return reports.ials21_xlsx(data) if xlsx else Response(data)
        if report == "iu17":
            year, month = _ym(request)
            return it_park_views.iu17_report(request, year, month)
        if report == "isapti17":
            year, _month = _ym(request)
            return it_park_views.annual_report(request, year)
        if report == "irm19":
            try:
                start = date.fromisoformat(p.get("date_from") or timezone.localdate().replace(day=1).isoformat())
                end = date.fromisoformat(p.get("date_to") or timezone.localdate().isoformat())
            except ValueError:
                raise ValidationError({"date_from": "Data se scrie AAAA-LL-ZZ."}) from None
            if xml:
                return xml_export.irm19_xml(start, end)
            data = reports.irm19(start, end)
            return reports.irm19_xlsx(data) if xlsx else Response(data)
        raise NotFound()


class TaxSettingsView(APIView):
    perm_module = ("tax_reports", "payroll_settings")

    def get(self, request):
        return Response(reports.get_settings())

    def put(self, request):
        if not request.user.has_crm_perm("payroll_settings.edit"):
            raise PermissionDenied("Setările le schimbă cine are dreptul la setările salariului.")
        cfg = reports.get_settings()
        limits = {"email": 120, "phone": 40}
        for key in reports.SETTINGS_FIELDS:
            if key in request.data:
                cfg[key] = str(request.data.get(key) or "").strip()[:limits.get(key, 10)]
        SystemSetting.write(reports.SETTINGS_KEY, cfg)
        return Response(cfg)
