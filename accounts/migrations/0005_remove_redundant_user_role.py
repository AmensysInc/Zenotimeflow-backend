# Remove redundant 'user' role when user has an assigned role (employee, company_manager, etc.)
# So each user has only one role: no duplicate User + Employee rows for the same person.

from django.db import migrations


def remove_redundant_user_roles(apps, schema_editor):
    UserRole = apps.get_model('accounts', 'UserRole')
    # Users who have an assigned role (not just 'user')
    assigned_roles = ('employee', 'company_manager', 'organization_manager', 'operations_manager', 'manager', 'admin')
    user_ids_with_assigned = set(
        UserRole.objects.filter(role__in=assigned_roles).values_list('user_id', flat=True).distinct()
    )
    # Delete role='user' for those users so they have only their assigned role
    deleted, _ = UserRole.objects.filter(user_id__in=user_ids_with_assigned, role='user').delete()
    return deleted


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_merge_20260220_0001'),
    ]

    operations = [
        migrations.RunPython(remove_redundant_user_roles, noop),
    ]
