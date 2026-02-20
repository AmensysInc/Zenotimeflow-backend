# One-time cleanup: 1) Remove duplicate user_roles (same user+role+app_type). 2) Remove redundant 'user' role when user has an assigned role.

from django.db import migrations


def remove_duplicate_user_roles(apps, schema_editor):
    """Keep one row per (user_id, role, app_type); delete the rest so user_roles has no duplicates."""
    UserRole = apps.get_model('accounts', 'UserRole')
    from django.db.models import Min
    kept_ids = list(
        UserRole.objects.values('user_id', 'role', 'app_type')
        .annotate(keep_id=Min('id'))
        .values_list('keep_id', flat=True)
    )
    UserRole.objects.exclude(id__in=kept_ids).delete()


def remove_user_role_when_has_assigned_role(apps, schema_editor):
    """Remove role='user' for users who have an assigned role so they appear once with that role."""
    UserRole = apps.get_model('accounts', 'UserRole')
    assigned_roles = ('employee', 'company_manager', 'organization_manager')
    user_ids = UserRole.objects.filter(role__in=assigned_roles).values_list('user_id', flat=True).distinct()
    UserRole.objects.filter(user_id__in=user_ids, role='user').delete()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(remove_duplicate_user_roles, noop),
        migrations.RunPython(remove_user_role_when_has_assigned_role, noop),
    ]
