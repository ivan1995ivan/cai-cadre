# Temele „Clasic de birou” (luminoasă și întunecată) de ales în Profil.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_role_names_company'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='theme',
            field=models.CharField(blank=True, choices=[('desktop', 'Clasic de birou'), ('desktop_dark', 'Clasic de birou, întunecat'), ('green', 'Verde'), ('turquoise', 'Turcoaz'), ('blue', 'Albastru'), ('dark', 'Întunecată'), ('onec', 'Ca în 1C (galben)'), ('auto', 'Automat')], default='', max_length=12),
        ),
    ]
