# Add calendar_event_id to link ShiftTask with CalendarEvent for sync

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduler', '0005_shift_task'),
    ]

    operations = [
        migrations.AddField(
            model_name='shifttask',
            name='calendar_event_id',
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
    ]
