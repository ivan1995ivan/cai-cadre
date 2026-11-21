from django.db import migrations

# rolurile predefinite cu denumirea de spital → denumirea pentru o întreprindere (doar dacă n-au fost redenumite de mână)
RENAMED = {
    "department_head": (("Șef de secție", "Заведующий отделением"), ("Șef de subdiviziune", "Руководитель подразделения")),
    "director": (("Director (conducătorul instituției)", "Директор (руководитель учреждения)"),
                 ("Director / administrator", "Директор / администратор")),
}


def rename(apps, schema_editor, back=False):
    Role = apps.get_model("users", "Role")
    for code, (old, new) in RENAMED.items():
        src, dst = (new, old) if back else (old, new)
        for role in Role.objects.filter(code=code, is_system=True):
            changed = []
            if role.name_ro == src[0]:
                role.name_ro = dst[0]
                changed.append("name_ro")
            if role.name_ru == src[1]:
                role.name_ru = dst[1]
                changed.append("name_ru")
            if changed:
                role.save(update_fields=changed)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_settings_moved'),
    ]

    operations = [
        migrations.RunPython(rename, lambda apps, se: rename(apps, se, back=True)),
    ]
