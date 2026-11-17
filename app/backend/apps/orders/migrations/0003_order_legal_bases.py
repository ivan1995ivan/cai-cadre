"""Ordinul: unul sau mai multe temeiuri legale (în locul unuia); temeiul de până acum trece în listă."""
from django.db import migrations, models


def copy(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    for o in Order.objects.exclude(legal_basis=None):
        o.legal_bases.add(o.legal_basis_id)


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_order_deletion_mark'),
        ('org', '0006_ordertype_legal_bases'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='legal_bases',
            field=models.ManyToManyField(blank=True, related_name='orders', to='org.legalbasis', verbose_name='Temeiurile legale'),
        ),
        migrations.RunPython(copy, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='order',
            name='legal_basis',
        ),
    ]
