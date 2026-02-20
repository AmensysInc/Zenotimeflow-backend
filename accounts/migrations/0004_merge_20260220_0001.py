# Merge migration: resolve conflicting leaf nodes (0003_alter_userrole_role, 0003_deduplicate_user_roles)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_alter_userrole_role'),
        ('accounts', '0003_deduplicate_user_roles'),
    ]

    operations = []
