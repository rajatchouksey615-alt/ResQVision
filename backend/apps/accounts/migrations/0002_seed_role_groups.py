from django.db import migrations


ROLE_GROUPS = ("ADMIN", "POLICE", "HOSPITAL")


def seed_role_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    database = schema_editor.connection.alias
    for role_name in ROLE_GROUPS:
        Group.objects.using(database).get_or_create(name=role_name)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(seed_role_groups, migrations.RunPython.noop),
    ]
