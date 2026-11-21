"""CAI CADRE pentru întreprinderi private (S1): clasificatoarele fără nimic de spital.

- categoriile de personal (fixe, după Ordinul MS 100/2008) → clasificator editabil (DictItem „staff_category”), cu grupele
  majore CORM 006-2021; funcțiile primesc categoria după prima cifră a codului CORM, iar fără cod — după categoria veche
  (cea fără corespondent — „personal administrativ-gospodăresc”, „alt personal” — rămâne goală);
- subdiviziunile: fără paturi, feluri generale (departament, secție, atelier, filială, depozit) în locul celor clinice;
- specialitățile: nivelul studiilor în locul felului medical / farmaceutic / nursing;
- statele de personal: fără „mențiunea de efort” (textul trece în observații), aprobarea prin ordinul conducătorului;
- la instalările existente se marchează pentru ștergere (nu se șterg) tipurile de ordin, temeiurile și elementele de
  clasificator livrate doar pentru spital; utilizatorul le șterge din „Obiecte marcate” dacă nu sunt folosite.
"""
import django.db.models.deletion
from django.db import migrations, models

STAFF_CATEGORIES = [
    ("1", "Conducători și funcționari superiori", "Руководители и высшие должностные лица", "Managers"),
    ("2", "Specialiști în diverse domenii de activitate", "Специалисты в различных областях деятельности", "Professionals"),
    ("3", "Tehnicieni, maiștri și alți specialiști asimilați", "Техники, мастера и приравненные к ним специалисты",
     "Technicians and associate professionals"),
    ("4", "Funcționari administrativi", "Административные служащие", "Clerical support workers"),
    ("5", "Lucrători din domeniul serviciilor și comerțului", "Работники сферы обслуживания и торговли",
     "Service and sales workers"),
    ("6", "Lucrători calificați în agricultură, silvicultură, acvacultură și pescuit",
     "Квалифицированные работники сельского, лесного, рыбного хозяйства", "Skilled agricultural, forestry and fishery workers"),
    ("7", "Muncitori calificați și lucrători din domeniul artizanal", "Квалифицированные рабочие и ремесленники",
     "Craft and related trades workers"),
    ("8", "Operatori și asamblori de mașini și instalații", "Операторы и сборщики машин и установок",
     "Plant and machine operators, and assemblers"),
    ("9", "Muncitori necalificați", "Неквалифицированные рабочие", "Elementary occupations"),
]
# categoria veche → grupa CORM (doar unde corespondența e sigură)
OLD_TO_GROUP = {"leadership": "1", "physicians": "2", "pharmacists": "2", "nurses": "3", "junior": "5"}
SUBDIVISION_KINDS = {"clinical": "section", "paraclinical": "section", "ambulatory": "section", "admin": "department",
                     "other": "other"}
SPECIALTY_KINDS = {"medical": "higher", "pharmacy": "higher", "nursing": "postsecondary", "other": "other"}

HOSPITAL_ORDER_TYPES = ["attestation", "category_award", "on_call"]
HOSPITAL_BASES = ["HG-837", "OMS-386", "OMS-100"]
HOSPITAL_DICT_ITEMS = {
    "qualification": ["none", "second", "first", "superior"],
    "education": ["residency"],
    "document": ["residency_cert", "category_cert", "cme_cert", "medical_book"],
    "employment": ["resident"],
    "checklist": ["medical_book", "uniform"],
}
# denumirile livrate care se schimbă doar dacă clientul nu le-a corectat
RENAMES = {
    ("degree", "dr"): ("Doctor în științe medicale", "Doctor", "Доктор наук", "Doctor (PhD)"),
    ("degree", "dr_hab"): ("Doctor habilitat în științe medicale", "Doctor habilitat", "Доктор хабилитат", "Habilitated doctor"),
    ("checklist", "system_access"): ("Acces în sistemul informațional (SIA AMP)", "Accesul la sistemele informatice",
                                     "Доступ к информационным системам", "Information system access"),
}
HOSPITAL_OCCUPATIONS = [
    "Medic de familie", "Asistent medical de familie", "Asistent medical superior", "Felcer laborant", "Laborant",
    "Asistent medical fizioterapie", "Infermieră", "Director adjunct medical", "Șef secție — medic", "Medic traumatolog-ortoped",
    "Medic anesteziolog-reanimatolog", "Medic chirurg", "Medic neurochirurg", "Medic combustiolog", "Medic radiolog-imagist",
    "Medic de laborator", "Medic reabilitolog", "Medic de gardă", "Medic rezident", "Farmacist", "Asistent medical de secție",
    "Asistent medical anestezist", "Asistent medical de operație", "Asistent medical de proceduri", "Laborant radiolog",
    "Infermieră de operație",
]
HOSPITAL_SPECIALTIES = [
    "Ortopedie și traumatologie", "Anesteziologie și reanimatologie", "Chirurgie", "Neurochirurgie", "Combustiologie",
    "Radiologie și imagistică", "Medicină de laborator", "Reabilitare medicală și medicină fizică", "Medicină internă",
    "Neurologie", "Cardiologie", "Medicină de urgență", "Medicină de familie", "Sănătate publică și management", "Farmacie",
    "Asistent medical generalist", "Asistent medical în anestezie", "Laborant", "Fizioterapie", "Radiologie (studii medii)",
]
# temeiurile noi pentru salarizare, în locul HG 837/2016 (aceleași valori ca în apps.org.seed)
PAY_BASES = [
    ("CM-PAY", "Codul muncii nr. 154/2003", "128–139", "Salarizarea (salariul de bază, sporurile, sistemele de salarizare)",
     "Оплата труда (оклад, надбавки, системы оплаты)", "Pay (base salary, allowances, pay systems)"),
    ("REG-PAY", "Regulamentul de salarizare al întreprinderii", "", "Regulamentul de salarizare / contractul colectiv de muncă",
     "Положение об оплате труда / коллективный договор", "Pay regulation / collective agreement"),
]
PAY_ORDER_TYPES = ["salary_set", "allowance", "indexation"]


def forwards(apps, schema_editor):
    DictItem = apps.get_model("org", "DictItem")
    Occupation = apps.get_model("org", "Occupation")
    StaffListLine = apps.get_model("org", "StaffListLine")
    Subdivision = apps.get_model("org", "Subdivision")
    Specialty = apps.get_model("org", "Specialty")
    OrderType = apps.get_model("org", "OrderType")
    LegalBasis = apps.get_model("org", "LegalBasis")

    groups = {}
    for i, (code, ro, ru, en) in enumerate(STAFF_CATEGORIES, start=1):
        groups[code], _ = DictItem.objects.get_or_create(kind="staff_category", code=code, defaults={
            "name_ro": ro, "name_ru": ru, "name_en": en, "extra": {"corm_group": code}, "sort": i * 10})

    def group_of(code, old):
        first = (code or "").strip()[:1]
        if first in groups:
            return groups[first]
        return groups.get(OLD_TO_GROUP.get(old or ""))

    for occ in Occupation.objects.all():
        occ.staff_category = group_of(occ.code, occ.category)
        occ.save(update_fields=["staff_category"])
    for line in StaffListLine.objects.exclude(category=""):
        line.staff_category = groups.get(OLD_TO_GROUP.get(line.category))
        line.save(update_fields=["staff_category"])
    for line in StaffListLine.objects.exclude(effort_note=""):
        line.note = "; ".join(x for x in (line.note, line.effort_note) if x)[:300]
        line.save(update_fields=["note"])
    for old, new in SUBDIVISION_KINDS.items():
        Subdivision.objects.filter(kind=old).update(kind=new)
    for old, new in SPECIALTY_KINDS.items():
        Specialty.objects.filter(kind=old).update(kind=new)

    # la instalările existente: ce era doar de spital — marcat pentru ștergere
    OrderType.objects.filter(code__in=HOSPITAL_ORDER_TYPES).update(deletion_mark=True, is_active=False)
    hospital_bases = list(LegalBasis.objects.filter(code__in=HOSPITAL_BASES))
    if hospital_bases:
        pay = {}
        for i, (code, act, article, ro, ru, en) in enumerate(PAY_BASES):
            pay[code], _ = LegalBasis.objects.get_or_create(code=code, defaults={
                "act": act, "article": article, "name_ro": ro, "name_ru": ru, "name_en": en, "sort": 900 + i * 10})
        for ot in OrderType.objects.filter(legal_bases__in=hospital_bases).distinct():
            ot.legal_bases.remove(*hospital_bases)
            if ot.code in PAY_ORDER_TYPES and not ot.legal_bases.exists():
                ot.legal_bases.add(*pay.values())
        LegalBasis.objects.filter(pk__in=[b.pk for b in hospital_bases]).update(deletion_mark=True, is_active=False)
    for kind, codes in HOSPITAL_DICT_ITEMS.items():
        DictItem.objects.filter(kind=kind, code__in=codes).update(deletion_mark=True)
    for (kind, code), (old, ro, ru, en) in RENAMES.items():
        DictItem.objects.filter(kind=kind, code=code, name_ro=old).update(name_ro=ro, name_ru=ru, name_en=en)
    Occupation.objects.filter(name_ro__in=HOSPITAL_OCCUPATIONS).update(deletion_mark=True)
    Specialty.objects.filter(name_ro__in=HOSPITAL_SPECIALTIES).update(deletion_mark=True)


def backwards(apps, schema_editor):
    """Înapoi doar schema: categoria veche se reface din grupa CORM, cât se poate."""
    Occupation = apps.get_model("org", "Occupation")
    StaffListLine = apps.get_model("org", "StaffListLine")
    back = {"1": "leadership", "2": "physicians", "3": "nurses", "5": "junior"}
    for occ in Occupation.objects.select_related("staff_category"):
        occ.category = back.get(occ.staff_category.code if occ.staff_category_id else "", "other")
        occ.save(update_fields=["category"])
    for line in StaffListLine.objects.exclude(staff_category=None).select_related("staff_category"):
        line.category = back.get(line.staff_category.code, "")
        line.save(update_fields=["category"])


class Migration(migrations.Migration):

    dependencies = [
        ("org", "0006_ordertype_legal_bases"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dictitem",
            name="kind",
            field=models.CharField(choices=[
                ("staff_category", "Categoriile de personal (grupele CORM)"), ("qualification", "Categorii de calificare"),
                ("degree", "Grade științifice"), ("title", "Titluri științifico-didactice"), ("education", "Nivelul studiilor"),
                ("education_form", "Forma de învățământ"), ("document", "Tipuri de acte (identitate, diplome, certificate)"),
                ("family", "Gradul de rudenie"), ("marital", "Starea familială"), ("nationality", "Naționalitatea"),
                ("termination", "Motivele încetării CIM"), ("sanction", "Sancțiuni disciplinare"),
                ("incentive", "Tipuri de stimulare"), ("employment", "Tipul angajării"),
                ("military_group", "Evidența militară: grupa"), ("military_rank", "Evidența militară: grade"),
                ("military_center", "Centre militare teritoriale"),
                ("checklist", "Lista de verificare la angajare / eliberare"), ("vaccine", "Vaccinuri (sănătatea în muncă)")],
                db_index=True, max_length=20),
        ),
        migrations.AddField(
            model_name="occupation",
            name="staff_category",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+",
                                    to="org.dictitem"),
        ),
        migrations.AddField(
            model_name="stafflistline",
            name="staff_category",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+",
                                    to="org.dictitem"),
        ),
        migrations.AlterField(
            model_name="subdivision",
            name="kind",
            field=models.CharField(choices=[
                ("department", "Departament / direcție"), ("section", "Secție / serviciu / birou"),
                ("workshop", "Atelier / sector de producție"), ("branch", "Filială / subdiviziune separată (punct de lucru)"),
                ("warehouse", "Depozit"), ("other", "Alta"),
                ("clinical", "Clinică (cu paturi)"), ("paraclinical", "Paraclinică / diagnostic"),
                ("ambulatory", "Ambulatorie / consultativă"), ("admin", "Administrativă / gospodărească")],
                default="section", max_length=12, verbose_name="Tipul"),
        ),
        migrations.AlterField(
            model_name="specialty",
            name="kind",
            field=models.CharField(choices=[
                ("higher", "Învățământ superior"), ("postsecondary", "Învățământ profesional tehnic postsecundar"),
                ("secondary", "Învățământ profesional tehnic secundar (meserie)"), ("other", "Alta"),
                ("medical", "Medicală"), ("pharmacy", "Farmaceutică"), ("nursing", "Nursing / studii medii")],
                default="other", max_length=14),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.RemoveField(model_name="occupation", name="category"),
        migrations.RemoveField(model_name="stafflistline", name="category"),
        migrations.RemoveField(model_name="stafflistline", name="effort_note"),
        migrations.RemoveField(model_name="subdivision", name="beds"),
        migrations.RenameField(model_name="occupation", old_name="staff_category", new_name="category"),
        migrations.RenameField(model_name="stafflistline", old_name="staff_category", new_name="category"),
        migrations.AlterField(
            model_name="occupation",
            name="category",
            field=models.ForeignKey(blank=True, help_text="Goală — se ia după prima cifră a codului CORM (grupa majoră).",
                                    limit_choices_to={"kind": "staff_category"}, null=True,
                                    on_delete=django.db.models.deletion.PROTECT, related_name="+", to="org.dictitem",
                                    verbose_name="Categoria de personal"),
        ),
        migrations.AlterField(
            model_name="stafflistline",
            name="category",
            field=models.ForeignKey(blank=True, help_text="Goală — categoria funcției.", limit_choices_to={"kind": "staff_category"},
                                    null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="org.dictitem",
                                    verbose_name="Categoria de personal"),
        ),
        migrations.AlterField(
            model_name="subdivision",
            name="kind",
            field=models.CharField(choices=[
                ("department", "Departament / direcție"), ("section", "Secție / serviciu / birou"),
                ("workshop", "Atelier / sector de producție"), ("branch", "Filială / subdiviziune separată (punct de lucru)"),
                ("warehouse", "Depozit"), ("other", "Alta")], default="section", max_length=12, verbose_name="Tipul"),
        ),
        migrations.AlterField(
            model_name="specialty",
            name="kind",
            field=models.CharField(choices=[
                ("higher", "Învățământ superior"), ("postsecondary", "Învățământ profesional tehnic postsecundar"),
                ("secondary", "Învățământ profesional tehnic secundar (meserie)"), ("other", "Alta")],
                default="other", max_length=14),
        ),
    ]
