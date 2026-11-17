"""Fluturașii se trimit din îndreptarea spre plată pe salariu: trimiterea ține îndreptarea; cele de dinainte — calculul."""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0007_settle_at_payment'),
    ]

    operations = [
        migrations.AddField(
            model_name='payslipdispatch',
            name='payment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='dispatches', to='payroll.payment'),
        ),
        migrations.AlterField(
            model_name='payslipdispatch',
            name='payroll',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='dispatches', to='payroll.payroll'),
        ),
    ]
