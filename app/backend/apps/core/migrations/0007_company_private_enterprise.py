"""Constantele unei întreprinderi private: fără fondator și Stema de Stat, fără resturile CRM (TVA, marja, oferta,
metoda costului, discounturile, valuta și zecimalele prețurilor); codul CAEM și funcțiile semnatarilor formelor.
Codul CAEM stătea în setările declarațiilor (IPC21 / IALS21) — trece în Constante, ca să fie scris într-un singur loc."""
import re

from django.db import migrations, models

TAX_SETTINGS = "tax_report_settings"


def caem_to_company(apps, schema_editor):
    Company, SystemSetting = apps.get_model("core", "Company"), apps.get_model("core", "SystemSetting")
    setting = SystemSetting.objects.filter(key=TAX_SETTINGS).first()
    value = dict(setting.value or {}) if setting else {}
    caem = re.sub(r"\D", "", str(value.pop("caem", "") or ""))[:4]
    company = Company.objects.filter(pk=1).first()
    if company is not None and caem and not company.caem:
        company.caem = caem
        company.save(update_fields=["caem"])
    if setting is not None:
        setting.value = value
        setting.save(update_fields=["value"])


def caem_to_settings(apps, schema_editor):
    Company, SystemSetting = apps.get_model("core", "Company"), apps.get_model("core", "SystemSetting")
    company = Company.objects.filter(pk=1).first()
    if company is None or not company.caem:
        return
    setting, _ = SystemSetting.objects.get_or_create(key=TAX_SETTINGS, defaults={"value": {}})
    setting.value = {**(setting.value or {}), "caem": company.caem}
    setting.save(update_fields=["value"])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_company_function_panel'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='company',
            name='base_currency',
        ),
        migrations.RemoveField(
            model_name='company',
            name='cost_method',
        ),
        migrations.RemoveField(
            model_name='company',
            name='default_vat_rate',
        ),
        migrations.RemoveField(
            model_name='company',
            name='discount_mode',
        ),
        migrations.RemoveField(
            model_name='company',
            name='founder_ro',
        ),
        migrations.RemoveField(
            model_name='company',
            name='founder_ru',
        ),
        migrations.RemoveField(
            model_name='company',
            name='margin_visible_to_all',
        ),
        migrations.RemoveField(
            model_name='company',
            name='min_margin_pct',
        ),
        migrations.RemoveField(
            model_name='company',
            name='offer_validity_days',
        ),
        migrations.RemoveField(
            model_name='company',
            name='price_rounding',
        ),
        migrations.RemoveField(
            model_name='company',
            name='show_stema',
        ),
        migrations.RemoveField(
            model_name='company',
            name='vat_code',
        ),
        migrations.AddField(
            model_name='company',
            name='caem',
            field=models.CharField(blank=True, help_text='Patru cifre, fără punct (de ex. 6201); intră în antetul declarațiilor IPC21 / IALS21.', max_length=4, verbose_name='Codul CAEM (genul principal de activitate)'),
        ),
        migrations.AddField(
            model_name='company',
            name='chief_accountant_position_ro',
            field=models.CharField(blank=True, max_length=100, verbose_name='Funcția contabilului (RO)'),
        ),
        migrations.AddField(
            model_name='company',
            name='chief_accountant_position_ru',
            field=models.CharField(blank=True, max_length=100, verbose_name='Funcția contabilului (RU)'),
        ),
        migrations.AddField(
            model_name='company',
            name='director_position_ro',
            field=models.CharField(blank=True, help_text='De ex. Director, Director general, Administrator', max_length=100, verbose_name='Funcția conducătorului (RO)'),
        ),
        migrations.AddField(
            model_name='company',
            name='director_position_ru',
            field=models.CharField(blank=True, max_length=100, verbose_name='Funcția conducătorului (RU)'),
        ),
        migrations.AddField(
            model_name='company',
            name='hr_head_position_ro',
            field=models.CharField(blank=True, max_length=100, verbose_name='Funcția responsabilului de personal (RO)'),
        ),
        migrations.AddField(
            model_name='company',
            name='hr_head_position_ru',
            field=models.CharField(blank=True, max_length=100, verbose_name='Funcția responsabilului de personal (RU)'),
        ),
        migrations.AlterField(
            model_name='company',
            name='chief_accountant',
            field=models.CharField(blank=True, max_length=150, verbose_name='Contabil-șef (numele)'),
        ),
        migrations.AlterField(
            model_name='company',
            name='director',
            field=models.CharField(blank=True, max_length=150, verbose_name='Conducătorul (numele)'),
        ),
        migrations.AlterField(
            model_name='company',
            name='hr_head',
            field=models.CharField(blank=True, max_length=150, verbose_name='Responsabilul de personal (numele)'),
        ),
        migrations.AlterField(
            model_name='company',
            name='legal_form',
            field=models.CharField(blank=True, help_text='De ex. SRL, SA, ÎI', max_length=20, verbose_name='Formă juridică'),
        ),
            migrations.RunPython(caem_to_company, caem_to_settings),
    ]
