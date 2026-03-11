# Add is_published to Shift. Existing shifts default to True so employees keep seeing them.

from django.db import migrations, models


def set_existing_published(apps, schema_editor):
    Shift = apps.get_model('scheduler', 'Shift')
    Shift.objects.all().update(is_published=True)


class Migration(migrations.Migration):

    dependencies = [
        ('scheduler', '0006_shift_task_calendar_event_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='shift',
            name='is_published',
            field=models.BooleanField(default=False, help_text='False=draft; employees only see published shifts'),
        ),
        migrations.RunPython(set_existing_published, migrations.RunPython.noop),
    ]
