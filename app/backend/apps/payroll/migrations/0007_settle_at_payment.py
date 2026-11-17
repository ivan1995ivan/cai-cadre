"""Impozitul pe venit și CNAM se rețin la plată (îndreptarea spre plată), nu în calcul.

Calculele de dinainte primesc bazele (impozitul — din părțile impozabile ale acumulărilor, CNAM — din baza rândului CNAM),
pierd rândurile IMPOZIT / CNAM / AVANS (impozitele reținute stau în plăți, avansul e o plată), iar reținerile și restul
se refac fără ele. Numerotarea plăților primește denumirea nouă (dacă n-a fost schimbată de mână)."""
import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models

AT_PAYMENT = ("income_tax", "cnam", "advance")


def to_bases(apps, schema_editor):
    PayrollLine = apps.get_model("payroll", "PayrollLine")
    Payroll = apps.get_model("payroll", "Payroll")
    zero = Decimal("0")
    for ln in PayrollLine.objects.prefetch_related("items__pay_type"):
        items = list(ln.items.all())
        accruals = [i for i in items if i.pay_type.category == "accrual"]
        cnam_row = next((i for i in items if i.pay_type.auto == "cnam" and i.base is not None), None)
        ln.taxable = sum((i.taxable_part for i in accruals), zero)
        ln.cnam_base = cnam_row.base if cnam_row else sum((i.amount for i in accruals if i.pay_type.cnam), zero)
        ln.deductions = sum((i.amount for i in items if i.pay_type.category == "deduction" and i.pay_type.auto not in AT_PAYMENT), zero)
        ln.net = ln.gross - ln.deductions
        ln.save(update_fields=["taxable", "cnam_base", "deductions", "net"])
        ln.items.filter(pay_type__auto__in=AT_PAYMENT).delete()
    for doc in Payroll.objects.all():
        totals = {f: zero for f in ("gross", "taxable", "cnam_base", "cas", "deductions", "net")}
        count = 0
        for ln in doc.lines.all():
            count += 1
            for f in totals:
                totals[f] += getattr(ln, f)
        doc.totals = {k: float(v) for k, v in totals.items()} | {"lines": count}
        doc.save(update_fields=["totals"])


def rename_series(apps, schema_editor):
    NumberSeries = apps.get_model("core", "NumberSeries")
    NumberSeries.objects.filter(doc_type="payroll_payment", name_ro="Plata salariului").update(name_ro="Îndreptarea spre plată")
    NumberSeries.objects.filter(doc_type="payroll_payment", name_ru="Выплата зарплаты").update(name_ru="Ведомость на выплату")


class Migration(migrations.Migration):

    dependencies = [
        ('payroll', '0006_payment_deletion_mark_payroll_deletion_mark_and_more'),
        ('core', '0005_bank_deletion_mark_locality_deletion_mark'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='payment',
            options={'ordering': ['-year', '-month', '-date', '-id'], 'verbose_name': 'Îndreptarea spre plată'},
        ),
        migrations.AddField(
            model_name='payment',
            name='payroll',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='payments', to='payroll.payroll', verbose_name='În baza calculului (gol = pe sold)'),
        ),
        migrations.AddField(
            model_name='payrollline',
            name='cnam_base',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=12, verbose_name='Baza CNAM'),
        ),
        migrations.AlterField(
            model_name='payrollline',
            name='net',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=12, verbose_name='Brutul minus reținerile (înainte de impozit și CNAM)'),
        ),
        migrations.AlterField(
            model_name='payrollline',
            name='taxable',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=12, verbose_name='Baza impozitului pe venit (acumulările impozabile)'),
        ),
        migrations.AlterField(
            model_name='paytype',
            name='auto',
            field=models.CharField(choices=[('salary', 'Salariul de funcție (pro-rata la orele lucrate)'), ('allowance', 'Sporurile fixe din raportul de muncă (%)'), ('combination', 'Plata pentru cumul (% din salariul de funcție)'), ('night', 'Munca de noapte (+ % la tariful orar)'), ('holiday', 'Munca în zile de sărbătoare (+ % la tariful orar)'), ('overtime', 'Ore suplimentare (+ % la tariful orar)'), ('leave', 'Indemnizația de concediu de odihnă (media × zile)'), ('leave_comp', 'Compensarea concediului nefolosit'), ('sick', 'Incapacitate temporară: zilele plătite de angajator'), ('bonus', 'Premii din ordine'), ('aid', 'Ajutor material din ordine'), ('advance', 'Avansul plătit (se ia din plăți, pe fluturaș)'), ('income_tax', 'Impozitul pe venit (se reține la plată)'), ('cnam', 'Prima de asigurare medicală (se reține la plată)'), ('cas', 'Contribuția de asigurări sociale (angajator)'), ('none', '—')], default='none', max_length=16, verbose_name='Calculul automat'),
        ),
        migrations.RunPython(to_bases, migrations.RunPython.noop),
        migrations.RunPython(rename_series, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='payrollline',
            name='cnam',
        ),
        migrations.RemoveField(
            model_name='payrollline',
            name='exemption',
        ),
        migrations.RemoveField(
            model_name='payrollline',
            name='income_tax',
        ),
    ]
