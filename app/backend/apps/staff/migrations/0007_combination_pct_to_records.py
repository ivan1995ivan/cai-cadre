"""S4b: „Plata pentru cumul (%)” (`combination_pct` pe raport și în istoric) devine înregistrarea „Cumularea funcțiilor /
suplinirea” pe același raport, câte una pe fiecare perioadă cu procent din istoric, cu plata „% din salariul funcției proprii”
(ca până acum: salariul raportului × partea lucrată × %). Apoi câmpul vechi se scoate — un singur mecanism."""

import django.db.models.deletion
from datetime import timedelta

from django.db import migrations, models

NOTE = "Convertit din „Plata pentru cumul (%)” al raportului de muncă"


def forward(apps, schema_editor):
    Employment = apps.get_model("staff", "Employment")
    Combination = apps.get_model("staff", "FunctionCombination")
    for emp in Employment.objects.all().order_by("id"):
        history = sorted(emp.history.all(), key=lambda h: (h.date, h.id))
        periods = []  # [(de la, până la, procent, ordinul, funcția)]
        if history:
            for rec in history:
                value = rec.combination_pct or 0
                last = periods[-1] if periods else None
                if last is not None and last[2] == value:
                    continue
                if last is not None:
                    periods[-1] = (last[0], max(rec.date - timedelta(days=1), last[0]), last[2], last[3], last[4])
                periods.append((rec.date, None, value, rec.order, rec.occupation_id))
        elif emp.combination_pct:
            periods.append((emp.date_from, None, emp.combination_pct, emp.hire_order, emp.occupation_id))
        end = emp.end_date or emp.date_to
        for start, stop, value, order, occupation in periods:
            if not value or value <= 0:
                continue
            stop = stop or end
            Combination.objects.create(
                employment=emp, kind="substitution" if emp.kind == "substitute" else "combination", occupation_id=occupation,
                pay_mode="pct_own", value=value, date_from=start, date_to=stop, order=order or "", note=NOTE)


def backward(apps, schema_editor):
    Combination = apps.get_model("staff", "FunctionCombination")
    for rec in Combination.objects.filter(note=NOTE, pay_mode="pct_own").select_related("employment"):
        emp = rec.employment
        emp.combination_pct = rec.value if rec.date_to is None or (emp.end_date and rec.date_to >= emp.end_date) else emp.combination_pct
        emp.save(update_fields=["combination_pct"])
        emp.history.filter(date__gte=rec.date_from, **({"date__lte": rec.date_to} if rec.date_to else {})).update(
            combination_pct=rec.value)
    Combination.objects.filter(note=NOTE).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_order_legal_bases'),
        ('org', '0009_without_medical_dicts'),
        ('staff', '0006_pay_mode_function_combination'),
        ('worktime', '0004_hour_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='functioncombination',
            name='hour_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='worktime.hourtype', verbose_name='Tipul de ore (la plata pe ore)'),
        ),
        migrations.AddField(
            model_name='functioncombination',
            name='occupation',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to='org.occupation', verbose_name='Funcția cumulată / suplinită'),
        ),
        migrations.AddField(
            model_name='functioncombination',
            name='order_item',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='combinations', to='orders.orderitem', verbose_name='Din punctul ordinului'),
        ),
        migrations.AddField(
            model_name='functioncombination',
            name='subdivision',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='org.subdivision', verbose_name='Subdiviziunea funcției'),
        ),
        migrations.AddField(
            model_name='functioncombination',
            name='substitutes',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='substituted_in', to='staff.employment', verbose_name='Pe cine suplinește (raportul)'),
        ),
        migrations.RunPython(forward, backward),
        migrations.RemoveField(
            model_name='employment',
            name='combination_pct',
        ),
        migrations.RemoveField(
            model_name='employmenthistory',
            name='combination_pct',
        ),
    ]
