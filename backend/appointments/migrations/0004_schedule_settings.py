from django.db import migrations

def create_settings(apps, schema_editor):
    apps.get_model('appointments', 'ScheduleSettings').objects.get_or_create(pk=1)

class Migration(migrations.Migration):
    dependencies = [('appointments', '0003_initial')]
    operations = [migrations.RunPython(create_settings, migrations.RunPython.noop)]
