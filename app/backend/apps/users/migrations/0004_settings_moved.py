from django.db import migrations


def settings_moved(apps, schema_editor):
    """Administrare → Setări (1.4.0): favoritele, bifele de meniu ale rolurilor și meniul salvat — pe adresele și cheile noi
    (apps/core/moved.py). Rolul vede după actualizare exact ce vedea înainte."""
    from apps.core import moved

    for user in apps.get_model("users", "User").objects.only("id", "favorites"):
        fixed = moved.favorites(user.favorites or [])
        if fixed != (user.favorites or []):
            user.favorites = fixed
            user.save(update_fields=["favorites"])
    for role in apps.get_model("users", "Role").objects.only("id", "menu_hidden"):
        fixed = moved.hidden_keys(role.menu_hidden or [], tabs=True)
        if fixed != (role.menu_hidden or []):
            role.menu_hidden = fixed
            role.save(update_fields=["menu_hidden"])
    setting = apps.get_model("core", "SystemSetting").objects.filter(key="menu_layout").first()
    layout = setting.value if setting and isinstance(setting.value, dict) else {}
    if layout.get("version") == 2 and isinstance(layout.get("sections"), list):
        fixed = moved.sections(layout["sections"])
        if fixed != layout["sections"]:
            setting.value = {**layout, "sections": fixed}
            setting.save(update_fields=["value"])


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_remove_telegram_role_name_ru'),
        ('core', '0005_bank_deletion_mark_locality_deletion_mark'),
    ]

    operations = [
        migrations.RunPython(settings_moved, migrations.RunPython.noop),
    ]
