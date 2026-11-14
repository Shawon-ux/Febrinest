from django.db import migrations, models


def flag_main(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    main = User.objects.filter(phone="01700000000").first() or User.objects.filter(is_superuser=True).order_by("id").first()
    if main:
        User.objects.filter(pk=main.pk).update(is_main_admin=True, is_staff=True)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]
    operations = [
        migrations.AddField("user", "is_main_admin", models.BooleanField(default=False, editable=False)),
        migrations.RunPython(flag_main, migrations.RunPython.noop),
    ]
