# Tema „Clasic de birou” (aspectul de program de birou: bara de meniu, bara de unelte, bara de stare) devine tema
# implicită a întreprinderii. Întreprinderea rămasă pe vechea temă implicită („Verde”) trece pe ea; cine a ales altă temă
# (turcoaz, albastru, 1C, întunecată) o păstrează. Utilizatorii cu tema lor din Profil nu se schimbă.

from django.db import migrations, models


def to_desktop(apps, schema_editor):
    apps.get_model("core", "Company").objects.filter(default_theme="green").update(default_theme="desktop")


def to_green(apps, schema_editor):
    apps.get_model("core", "Company").objects.filter(default_theme__in=["desktop", "desktop_dark"]).update(default_theme="green")


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_company_military_enabled'),
    ]

    operations = [
        migrations.AlterField(
            model_name='company',
            name='default_theme',
            field=models.CharField(choices=[('desktop', 'Clasic de birou'), ('desktop_dark', 'Clasic de birou, întunecat'), ('green', 'Verde'), ('turquoise', 'Turcoaz'), ('blue', 'Albastru'), ('dark', 'Întunecată'), ('onec', 'Ca în 1C (galben)')], default='desktop', max_length=12),
        ),
        migrations.RunPython(to_desktop, to_green),
    ]
