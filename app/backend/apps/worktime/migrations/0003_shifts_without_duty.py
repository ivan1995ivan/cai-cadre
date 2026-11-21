"""CAI CADRE pentru întreprinderi private (S1): fără gărzi; notațiile pontajului după Convenția colectivă nr. 17/2020.

- tura nu mai are bifa „Gardă”; turele G24 / G16 și graficul „G24” livrate pentru spital se marchează pentru ștergere;
- codurile vechi din tabelele de pontaj (CO, CFP, CM, S …) se rescriu cu notațiile modelului oficial (C, Cn, Cm, Sp …);
- setarea „gărzi pe lună” nu mai există (în locul ei — „ture de noapte pe lună”, implicit fără limită).
"""
from django.db import migrations

OLD_CODES = {"CO": "C", "CA": "C", "CFP": "Cn", "CMT": "Cc", "CP": "Cc", "CIC": "Cc", "CICN": "Cc", "CS": "Cs", "ZL": "Ls",
             "CM": "Cm", "S": "Sp"}


def forwards(apps, schema_editor):
    ShiftType = apps.get_model("worktime", "ShiftType")
    WorkSchedule = apps.get_model("worktime", "WorkSchedule")
    TimesheetLine = apps.get_model("worktime", "TimesheetLine")
    SystemSetting = apps.get_model("core", "SystemSetting")

    ShiftType.objects.filter(code__in=("G24", "G16"), is_duty=True).update(deletion_mark=True, is_active=False)
    WorkSchedule.objects.filter(code="G24").update(deletion_mark=True, is_active=False)
    for line in TimesheetLine.objects.all():
        days = {}
        for day, cell in (line.days or {}).items():
            if isinstance(cell, dict) and cell.get("c") in OLD_CODES:
                cell = {**cell, "c": OLD_CODES[cell["c"]]}
            days[day] = cell
        totals = dict(line.totals or {})
        if totals.get("codes"):
            codes = {}
            for code, count in totals["codes"].items():
                new = OLD_CODES.get(code, code)
                codes[new] = codes.get(new, 0) + count
            totals["codes"] = dict(sorted(codes.items()))
        if days != (line.days or {}) or totals != (line.totals or {}):
            line.days, line.totals = days, totals
            line.save(update_fields=["days", "totals"])
    setting = SystemSetting.objects.filter(key="worktime_settings").first()
    if setting is not None and isinstance(setting.value, dict) and "max_duties" in setting.value:
        value = dict(setting.value)
        value.pop("max_duties")
        setting.value = value
        setting.save(update_fields=["value"])


class Migration(migrations.Migration):

    dependencies = [
        ("worktime", "0002_roster_deletion_mark_shifttype_deletion_mark_and_more"),
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.RemoveField(model_name="shifttype", name="is_duty"),
        migrations.AlterModelOptions(name="roster", options={
            "ordering": ["-year", "-month", "subdivision__sort", "subdivision__name_ro"], "verbose_name": "Graficul de ture"}),
    ]
