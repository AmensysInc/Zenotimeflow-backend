# Backfill: create Employee record for every user who has role=employee but no Employee row.
# So employee-role users appear in Employee Management.

from django.db import migrations


def backfill_employee_records(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    UserRole = apps.get_model('accounts', 'UserRole')
    Employee = apps.get_model('scheduler', 'Employee')
    # Users with role=employee (any app_type)
    employee_user_ids = UserRole.objects.filter(role='employee').values_list('user_id', flat=True).distinct()
    created = 0
    for user_id in employee_user_ids:
        if Employee.objects.filter(user_id=user_id).exists():
            continue
        user = User.objects.filter(pk=user_id).first()
        if not user:
            continue
        Employee.objects.create(
            user_id=user_id,
            first_name=user.first_name or (user.email.split('@')[0] if user.email else ''),
            last_name=user.last_name or '',
            email=user.email,
            status='active',
        )
        created += 1
    return created


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('scheduler', '0003_employee_user_onetoone'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(backfill_employee_records, noop),
    ]
