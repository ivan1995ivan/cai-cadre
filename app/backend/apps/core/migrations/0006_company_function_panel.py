from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_bank_deletion_mark_locality_deletion_mark'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='function_panel',
            field=models.BooleanField(default=False, help_text='Secțiunile sus ca file; secțiunea deschide panoul ei: schema de lucru, registrele, clasificatoarele, rapoartele. Oprit — meniul în stânga, ca până acum.', verbose_name='Panoul funcțiilor (ca în 1C)'),
        ),
    ]
