"""Tipul ordinului: mai multe temeiuri legale implicite (în locul unuia); temeiul de până acum trece în listă."""
from django.db import migrations, models


def copy(apps, schema_editor):
    OrderType = apps.get_model("org", "OrderType")
    for ot in OrderType.objects.exclude(legal_basis=None):
        ot.legal_bases.add(ot.legal_basis_id)


class Migration(migrations.Migration):

    dependencies = [
        ('org', '0005_dictitem_deletion_mark_legalbasis_deletion_mark_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='ordertype',
            name='legal_bases',
            field=models.ManyToManyField(blank=True, related_name='order_types', to='org.legalbasis', verbose_name='Temeiurile legale implicite'),
        ),
        migrations.RunPython(copy, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='ordertype',
            name='legal_basis',
        ),
    ]
