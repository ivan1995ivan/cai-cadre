"""Antetul întreprinderii în locul celui de stat: în formele salvate în bază (și cele modificate de administrator)
{% gov_header %} (Stema, „REPUBLICA MOLDOVA”, fondatorul) devine {% company_header %}; formele livrate nemodificate le
aduce apoi la versiunea nouă seed-ul (`printing.seed.run`, la instalare și la actualizare)."""
from django.db import migrations, models

OLD, NEW = "{% gov_header %}", "{% company_header %}"


def _swap(apps, old, new):
    PrintTemplate = apps.get_model("printing", "PrintTemplate")
    for tpl in PrintTemplate.objects.all():
        changed = [f for f in ("body", "original_body") if old in (getattr(tpl, f) or "")]
        for field in changed:
            setattr(tpl, field, getattr(tpl, field).replace(old, new))
        if changed:
            tpl.save(update_fields=changed)


def forwards(apps, schema_editor):
    _swap(apps, OLD, NEW)


def backwards(apps, schema_editor):
    _swap(apps, NEW, OLD)


class Migration(migrations.Migration):

    dependencies = [
        ('printing', '0004_certificate_salary'),
    ]

    operations = [
        migrations.AlterField(
            model_name='printtemplate',
            name='doc_type',
            field=models.CharField(choices=[('order', 'Ordin (un angajat)'), ('order_collective', 'Ordin colectiv (mai mulți angajați)'), ('order_extract', 'Extras din ordin'), ('staff_list', 'State de personal'), ('employee_card', 'Fișa personală (MR-2)'), ('certificate_work', 'Adeverință de la locul de muncă'), ('certificate_seniority', 'Adeverință de vechime'), ('certificate_salary', 'Adeverință privind salariul (pentru bancă)'), ('contract', 'Contract individual de muncă'), ('timesheet', 'Tabel de pontaj'), ('roster', 'Graficul lunar de lucru (ture)'), ('leave_schedule', 'Graficul concediilor'), ('orders_register', 'Registrul ordinelor'), ('employee_list', 'Lista angajaților'), ('payslip', 'Fișa de calcul (salariu)'), ('payroll_sheet', 'Stat de calcul / de plată'), ('payment_sheet', 'Stat de plată'), ('bank_list', 'Lista pentru bancă'), ('annual_card', 'Fișa personală anuală a veniturilor'), ('report', 'Raport (din catalogul de rapoarte)')], db_index=True, max_length=24),
        ),
        migrations.RunPython(forwards, backwards),
    ]
