"""S1 (fără stat): migrațiile care trec o instalare veche (de spital) pe clasificatoarele pentru întreprinderi private."""
import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

ORG_BEFORE, ORG_AFTER = ("org", "0006_ordertype_legal_bases"), ("org", "0008_srl_labels")
WT_BEFORE, WT_AFTER = ("worktime", "0002_roster_deletion_mark_shifttype_deletion_mark_and_more"), ("worktime", "0003_shifts_without_duty")


def migrate(targets):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(targets)
    core = [n for n in executor.loader.graph.leaf_nodes() if n[0] == "core"]  # SystemSetting (nu se dă înapoi)
    return executor.loader.project_state([*targets, *core]).apps


@pytest.fixture
def old_install(transactional_db):
    apps = migrate([ORG_BEFORE, WT_BEFORE])
    yield apps
    migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())


def test_org_categories_subdivisions_and_hospital_data(old_install):
    apps = old_install
    Occupation, Subdivision = apps.get_model("org", "Occupation"), apps.get_model("org", "Subdivision")
    StaffList, StaffListLine = apps.get_model("org", "StaffList"), apps.get_model("org", "StaffListLine")
    Specialty, DictItem = apps.get_model("org", "Specialty"), apps.get_model("org", "DictItem")
    OrderType, LegalBasis = apps.get_model("org", "OrderType"), apps.get_model("org", "LegalBasis")

    accountant = Occupation.objects.create(code="241106", name_ro="Contabil", category="admin")  # după cod: grupa 2
    doctor = Occupation.objects.create(code="", name_ro="Medic traumatolog-ortoped", category="physicians")  # fără cod: veche → 2
    cleaner = Occupation.objects.create(code="", name_ro="Îngrijitor încăperi", category="admin")  # fără corespondent → gol
    nurse = Occupation.objects.create(code="", name_ro="Asistent medical de secție", category="nurses")
    ward = Subdivision.objects.create(code="TR1", name_ro="Traumatologie", kind="clinical", beds=40)
    adm = Subdivision.objects.create(code="ADM", name_ro="Administrația", kind="admin")
    sl = StaffList.objects.create(effective_from="2026-01-01")
    over = StaffListLine.objects.create(staff_list=sl, subdivision=ward, occupation=doctor, units=1, category="nurses",
                                        effort_note="cu 50% efort medic de familie", note="din ianuarie")
    plain = StaffListLine.objects.create(staff_list=sl, subdivision=adm, occupation=cleaner, units=1, category="other")
    spec = Specialty.objects.create(name_ro="Chirurgie", kind="medical")
    own_spec = Specialty.objects.create(name_ro="Contabilitate", kind="other")
    DictItem.objects.create(kind="qualification", code="superior", name_ro="Categoria superioară")
    DictItem.objects.create(kind="degree", code="dr", name_ro="Doctor în științe medicale")
    DictItem.objects.create(kind="degree", code="dr_hab", name_ro="Doctor habilitat (scris de client)")
    hg = LegalBasis.objects.create(code="HG-837", act="HG nr. 837/2016", name_ro="Salarizarea IMSP")
    cm = LegalBasis.objects.create(code="CM-206", article="206", name_ro="Sancțiunile")
    salary = OrderType.objects.create(code="salary_set", name_ro="Salariul")
    salary.legal_bases.set([hg])
    bonus = OrderType.objects.create(code="allowance", name_ro="Sporuri")
    bonus.legal_bases.set([hg, cm])
    award = OrderType.objects.create(code="category_award", name_ro="Conferirea categoriei")

    apps = migrate([ORG_AFTER, WT_BEFORE])
    Occupation, StaffListLine = apps.get_model("org", "Occupation"), apps.get_model("org", "StaffListLine")
    Subdivision, Specialty = apps.get_model("org", "Subdivision"), apps.get_model("org", "Specialty")
    DictItem, OrderType, LegalBasis = apps.get_model("org", "DictItem"), apps.get_model("org", "OrderType"), apps.get_model("org", "LegalBasis")

    groups = list(DictItem.objects.filter(kind="staff_category").order_by("sort").values_list("code", flat=True))
    assert groups == [str(i) for i in range(1, 10)]

    def group(occ):
        o = Occupation.objects.get(pk=occ.pk)
        return o.category.code if o.category_id else None

    assert (group(accountant), group(doctor), group(cleaner), group(nurse)) == ("2", "2", None, "3")
    over = StaffListLine.objects.get(pk=over.pk)
    assert over.category.code == "3" and over.note == "din ianuarie; cu 50% efort medic de familie"
    assert StaffListLine.objects.get(pk=plain.pk).category_id is None  # „alt personal” → categoria funcției
    assert Subdivision.objects.get(pk=ward.pk).kind == "section" and Subdivision.objects.get(pk=adm.pk).kind == "department"
    assert Specialty.objects.get(pk=spec.pk).kind == "higher" and Specialty.objects.get(pk=spec.pk).deletion_mark
    assert not Specialty.objects.get(pk=own_spec.pk).deletion_mark
    assert Occupation.objects.get(pk=doctor.pk).deletion_mark and not Occupation.objects.get(pk=accountant.pk).deletion_mark
    assert DictItem.objects.get(kind="qualification", code="superior").deletion_mark
    assert DictItem.objects.get(kind="degree", code="dr").name_ro == "Doctor"
    assert DictItem.objects.get(kind="degree", code="dr_hab").name_ro == "Doctor habilitat (scris de client)"  # corectat — rămâne
    assert LegalBasis.objects.get(code="HG-837").deletion_mark
    assert {b.code for b in OrderType.objects.get(pk=salary.pk).legal_bases.all()} == {"CM-PAY", "REG-PAY"}
    assert {b.code for b in OrderType.objects.get(pk=bonus.pk).legal_bases.all()} == {"CM-206"}  # avea și alt temei — rămâne
    award = OrderType.objects.get(pk=award.pk)
    assert award.deletion_mark and not award.is_active


def test_worktime_without_duty_shifts(old_install):
    apps = old_install
    ShiftType, WorkSchedule = apps.get_model("worktime", "ShiftType"), apps.get_model("worktime", "WorkSchedule")
    SystemSetting = apps.get_model("core", "SystemSetting")
    ShiftType.objects.create(code="G24", name="Gardă", hours=24, night_hours=8, is_duty=True)
    ShiftType.objects.create(code="N12", name="Noapte", hours=12, night_hours=8)
    WorkSchedule.objects.create(code="G24", name="Gărzi", kind="cycle")
    SystemSetting.objects.create(key="worktime_settings", value={"min_rest_hours": 11, "max_duties": 8})

    apps = migrate([ORG_AFTER, WT_AFTER])
    ShiftType, WorkSchedule = apps.get_model("worktime", "ShiftType"), apps.get_model("worktime", "WorkSchedule")
    SystemSetting = apps.get_model("core", "SystemSetting")
    assert ShiftType.objects.get(code="G24").deletion_mark and not ShiftType.objects.get(code="N12").deletion_mark
    assert WorkSchedule.objects.get(code="G24").deletion_mark
    assert SystemSetting.objects.get(key="worktime_settings").value == {"min_rest_hours": 11}
