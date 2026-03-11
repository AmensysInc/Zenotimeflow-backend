# ShiftTask: responsibilities per shift, shown to employee when they clock in

import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('scheduler', '0004_backfill_employee_for_employee_role_users'),
    ]

    operations = [
        migrations.CreateModel(
            name='ShiftTask',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=255)),
                ('order', models.PositiveSmallIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('shift', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shift_tasks', to='scheduler.shift')),
            ],
            options={
                'db_table': 'shift_tasks',
                'ordering': ['order', 'created_at'],
            },
        ),
    ]
