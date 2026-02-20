# Remove duplicate rows in user_roles: keep one per (user_id, role, app_type).

from django.db import migrations
from django.db.models import Min


def deduplicate_user_roles(apps, schema_editor):
    UserRole = apps.get_model('accounts', 'UserRole')
    kept_ids = list(
        UserRole.objects.values('user_id', 'role', 'app_type')
        .annotate(keep_id=Min('id'))
        .values_list('keep_id', flat=True)
    )
    deleted_count = UserRole.objects.exclude(id__in=kept_ids).delete()
    return deleted_count


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_remove_duplicate_user_roles'),
    ]

    operations = [
        migrations.RunPython(deduplicate_user_roles, noop),
    ]
