"""S4b: modalitatea de remunerare pe raportul de muncă (cu istoric „din data”) și cumularea funcțiilor / suplinirea pe același
contract (CM art. 156) ca înregistrare pe raport. „Plata pentru cumul (%)” se mută în înregistrări în 0007."""

import django.db.models.deletion
import django.utils.timezone
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('staff', '0005_srl_without_medical'),
    ]

    operations = [
        migrations.AddField(
            model_name='employment',
            name='hourly_rate',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10, verbose_name='Tariful orar de bază (lei pe oră)'),
        ),
        migrations.AddField(
            model_name='employment',
            name='pay_mode',
            field=models.CharField(choices=[('salary', 'Salariu lunar'), ('hourly', 'Tarif orar'), ('hour_types', 'Pe tipuri de ore'), ('mixed', 'Mixt: salariu lunar + tarife pe tipuri de ore')], default='salary', max_length=10, verbose_name='Modalitatea de remunerare'),
        ),
        migrations.AddField(
            model_name='employmenthistory',
            name='hourly_rate',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10),
        ),
        migrations.AddField(
            model_name='employmenthistory',
            name='pay_mode',
            field=models.CharField(choices=[('salary', 'Salariu lunar'), ('hourly', 'Tarif orar'), ('hour_types', 'Pe tipuri de ore'), ('mixed', 'Mixt: salariu lunar + tarife pe tipuri de ore')], default='salary', max_length=10),
        ),
        migrations.CreateModel(
            name='FunctionCombination',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('combination', 'Cumularea funcțiilor (profesiilor)'), ('substitution', 'Suplinirea salariatului temporar absent'), ('acting', 'Interimatul funcției')], default='combination', max_length=12, verbose_name='Felul')),
                ('substituted_name', models.CharField(blank=True, max_length=160, verbose_name='Pe cine suplinește (numele)')),
                ('pay_mode', models.CharField(choices=[('pct_own', '% din salariul funcției proprii'), ('pct_other', '% din salariul funcției cumulate / suplinite'), ('fixed', 'Sumă fixă pe lună'), ('hourly', 'Pe ore, cu tarif')], default='pct_own', max_length=10, verbose_name='Modalitatea plății')),
                ('value', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Valoarea (%, lei sau lei pe oră)')),
                ('other_salary', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Salariul funcției cumulate / suplinite (la „% din salariul ei”)')),
                ('date_from', models.DateField(verbose_name='De la')),
                ('date_to', models.DateField(blank=True, null=True, verbose_name='Până la')),
                ('order', models.CharField(blank=True, max_length=80, verbose_name='Ordinul (nr., data)')),
                ('note', models.CharField(blank=True, max_length=300, verbose_name='Observații')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('employment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='combinations', to='staff.employment', verbose_name='Raportul de muncă (de bază)')),
            ],
            options={
                'verbose_name': 'Cumularea funcțiilor / suplinirea',
                'ordering': ['employment', 'date_from', 'id'],
            },
        ),
    ]
