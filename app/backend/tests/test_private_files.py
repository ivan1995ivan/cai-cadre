"""Fișierele cu date personale (fotografia, scanările actelor, certificatele medicale, semnătura și ștampila) stau în partea
privată și se dau doar prin API, cu autentificarea și drepturile endpoint-ului; prin /media/ — doar logo-urile."""
import base64
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.models import Company
from apps.core.private_files import relocate
from apps.leave.models import SickLeave
from apps.staff.models import Employee, EmployeeDocument

from .test_staff import hire, make_emp, org  # noqa: F401 — fixtura și ajutoarele comune

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
PDF = b"%PDF-1.4\n%\xe2\xe3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'


@pytest.fixture
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def body(response):
    return b"".join(response.streaming_content)


def test_photo_and_scans_only_through_the_api(admin_client, make_user, client_for, org, media):  # noqa: F811
    a, b = make_emp(), make_emp("Rusu", "Ana")
    hire(a, org, sub="tr1")
    hire(b, org, occ="anest", sub="bo")
    r = admin_client.patch(f"/api/staff/employees/{a.id}/", {"photo": SimpleUploadedFile("eu.png", PNG, "image/png")},
                           format="multipart")
    assert r.status_code == 200 and r.data["photo"].startswith(f"/staff/employees/{a.id}/photo/?v=")
    a.refresh_from_db()
    assert a.photo.name.startswith("private/staff/photos/") and (media / a.photo.name).is_file()
    # prin /media/ — nimic; prin API — fotografia
    assert admin_client.get(f"/media/{a.photo.name}").status_code == 404
    got = admin_client.get(f"/api{r.data['photo']}")
    assert got.status_code == 200 and got["Content-Type"] == "image/png" and body(got) == PNG
    assert got["X-Content-Type-Options"] == "nosniff" and "private" in got["Cache-Control"]
    # fără autentificare / fără drept / alt angajat decât cei văzuți
    from rest_framework.test import APIClient

    assert APIClient().get(f"/api/staff/employees/{a.id}/photo/").status_code == 401
    head = make_user("sef", ["department_head"])
    org["ati"].users.add(head)
    role = head.roles.first()
    role.data_scopes = {**role.data_scopes, "employees": "team"}
    role.save()
    api = client_for(type(head).objects.get(pk=head.pk))
    assert api.get(f"/api/staff/employees/{a.id}/photo/").status_code == 404
    assert api.get(f"/api/staff/employees/{b.id}/photo/").status_code == 404  # n-are fotografie
    # scanarea actului: PDF în browser, SVG doar ca descărcare; cere și dreptul la datele sensibile
    doc = EmployeeDocument.objects.create(employee=a, title="Buletin")
    r = admin_client.patch(f"/api/staff/documents/{doc.id}/", {"file": SimpleUploadedFile("buletin.pdf", PDF, "application/pdf")},
                           format="multipart")
    assert r.status_code == 200 and r.data["file"].startswith(f"/staff/documents/{doc.id}/file/?v=")
    doc.refresh_from_db()
    assert doc.file.name.startswith(f"private/staff/{a.id}/") and admin_client.get(f"/media/{doc.file.name}").status_code == 404
    got = admin_client.get(f"/api/staff/documents/{doc.id}/file/")
    assert got["Content-Type"] == "application/pdf" and got["Content-Disposition"].startswith("inline") and body(got) == PDF
    admin_client.patch(f"/api/staff/documents/{doc.id}/", {"file": SimpleUploadedFile("x.svg", SVG, "image/svg+xml")}, format="multipart")
    got = admin_client.get(f"/api/staff/documents/{doc.id}/file/")
    assert got["Content-Type"] == "application/octet-stream" and got["Content-Disposition"].startswith("attachment")
    assert api.get(f"/api/staff/documents/{doc.id}/file/").status_code == 403  # fără „date sensibile”
    # fișa scurtă: adresa API, nu /media/
    assert admin_client.get(f"/api/staff/employees/{a.id}/summary/").data["photo"].startswith(f"/staff/employees/{a.id}/photo/")


def test_sick_leave_scan_company_signature_and_public_logo(admin_client, org, media):  # noqa: F811
    e = make_emp()
    hire(e, org)
    r = admin_client.post("/api/leave/sick-leaves/", {"employee": e.id, "number": "1", "kind": "illness", "date_from": "2026-08-10",
                                                      "date_to": "2026-08-12"}, format="json")
    sick = SickLeave.objects.get(pk=r.data["id"])
    r = admin_client.patch(f"/api/leave/sick-leaves/{sick.id}/", {"file": SimpleUploadedFile("cm.pdf", PDF, "application/pdf")},
                           format="multipart")
    assert r.status_code == 200, r.data
    sick.refresh_from_db()
    assert sick.file.name.startswith("private/sick/") and admin_client.get(f"/media/{sick.file.name}").status_code == 404
    assert body(admin_client.get(f"/api/leave/sick-leaves/{sick.id}/file/")) == PDF
    for field in ("signature", "stamp", "logo"):
        assert admin_client.patch("/api/company/", {field: SimpleUploadedFile(f"{field}.png", PNG, "image/png")},
                                  format="multipart").status_code == 200
    c = Company.get()
    assert c.signature.name.startswith("private/company/") and c.stamp.name.startswith("private/company/")
    data = admin_client.get("/api/company/").data
    assert data["signature"].startswith("/company/images/signature/?v=") and data["stamp"].startswith("/company/images/stamp/")
    assert admin_client.get(f"/media/{c.signature.name}").status_code == 404
    assert body(admin_client.get("/api/company/images/stamp/")) == PNG
    assert admin_client.get("/api/company/images/logo/").status_code == 404  # doar semnătura și ștampila
    assert admin_client.get(f"/media/{c.logo.name}").status_code == 200  # logo-ul — public (pagina de login)
    # în forme ștampila intră pusă în pagină, nu ca adresă
    from apps.printing.renderer import company_context

    assert company_context(None, "ro")["stamp"].startswith("data:image/png;base64,")


def test_old_files_are_moved_to_the_private_part(org, media):  # noqa: F811
    e = make_emp()
    old = media / "staff" / "photos" / "vechi.png"
    old.parent.mkdir(parents=True)
    old.write_bytes(PNG)
    Employee.objects.filter(pk=e.pk).update(photo="staff/photos/vechi.png")
    missing = EmployeeDocument.objects.create(employee=e, title="x", file="staff/1/lipsa.pdf")
    relocate(Employee, ["photo"], media)
    relocate(EmployeeDocument, ["file"], media)
    relocate(Employee, ["photo"], media)  # a doua oară — nimic
    e.refresh_from_db()
    missing.refresh_from_db()
    assert e.photo.name == "private/staff/photos/vechi.png" and (media / e.photo.name).read_bytes() == PNG and not old.exists()
    assert missing.file.name == "private/staff/1/lipsa.pdf"
    assert Path(media / "private").is_dir()


def test_employee_card_print_embeds_the_photo(admin_client, admin_user, rf, org, media):  # noqa: F811
    e = make_emp()
    hire(e, org)
    admin_client.patch(f"/api/staff/employees/{e.id}/", {"photo": SimpleUploadedFile("eu.png", PNG, "image/png")}, format="multipart")
    from apps.staff.printing import employee_context

    e.refresh_from_db()
    from rest_framework.request import Request

    req = Request(rf.get("/"))
    req.user = admin_user
    ctx = employee_context(req, e, "ro", {"show_photo": True}, "employee_card")
    assert ctx["emp"]["photo"].startswith("data:image/png;base64,")
