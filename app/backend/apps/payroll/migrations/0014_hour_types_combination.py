"""S4b: calculul automat „Ore pe tipuri” (ore plătite × tariful, cu orele garantate) și tipul CUMUL redenumit „Plata pentru
cumularea funcțiilor / suplinire” — se calculează din înregistrările de cumulare de pe raport (CM art. 156), nu din cumul.
Tipul ORE („Ore pe tipuri”) îl pune seed-ul (`payroll.seed.run`, la instalare și la actualizare)."""

from django.db import migrations, models

OLD = ("Plata pentru cumul de funcții", "Доплата за совмещение", "Combination pay")
NEW = ("Plata pentru cumularea funcțiilor / suplinire", "Доплата за совмещение / замещение", "Pay for combining posts / substitution")


def rename(apps, schema_editor, old=OLD, new=NEW):
    PayType = apps.get_model("payroll", "PayType")
    for t in PayType.objects.filter(code="CUMUL", is_system=True):
        changed = []
        for field, before, after in zip(("name_ro", "name_ru", "name_en"), old, new):
            if getattr(t, field) == before:  # doar denumirea livrată; cea schimbată de utilizator rămâne
                setattr(t, field, after)
                changed.append(field)
        if changed:
            t.save(update_fields=changed)


def unrename(apps, schema_editor):
    rename(apps, schema_editor, old=NEW, new=OLD)


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0013_it_park'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paytype',
            name='auto',
            field=models.CharField(choices=[('salary', 'Salariul de funcție (pro-rata la orele lucrate)'), ('allowance', 'Sporurile fixe din raportul de muncă (%)'), ('combination', 'Plata pentru cumularea funcțiilor / suplinire (CM art. 156, din raportul de muncă)'), ('hour_types', 'Ore pe tipuri: ore plătite × tariful (cu orele garantate)'), ('night', 'Munca de noapte (+ % la tariful orar)'), ('holiday', 'Munca în zile de sărbătoare (+ % la tariful orar)'), ('overtime', 'Ore suplimentare (+ % la tariful orar)'), ('leave', 'Indemnizația de concediu de odihnă (media × zile)'), ('leave_comp', 'Compensarea concediului nefolosit'), ('sick', 'Incapacitate temporară: zilele plătite de angajator'), ('sick_accident', 'Accident de muncă / boală profesională: zilele plătite de angajator'), ('min_wage', 'Completare până la salariul minim'), ('bonus', 'Premii din ordine'), ('aid', 'Ajutor material din ordine'), ('advance', 'Avansul plătit (se ia din plăți, pe fluturaș)'), ('income_tax', 'Impozitul pe venit (se reține la plată)'), ('cnam', 'Prima de asigurare medicală (se reține la plată)'), ('cas', 'Contribuția de asigurări sociale (angajator)'), ('cas_min', 'CAS pe diferența până la baza minimă (salariul minim)'), ('none', '—')], default='none', max_length=16, verbose_name='Calculul automat'),
        ),
        migrations.RunPython(rename, unrename),
    ]
