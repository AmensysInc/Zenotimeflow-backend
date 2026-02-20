"""
Ensure every User has a Profile and default UserRole (fixes 500 on login for superusers).
Ensure employees are stored in the employees table when role=employee (not only in user_roles).
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Profile, UserRole


@receiver(post_save, sender=User)
def create_profile_and_role_for_user(sender, instance, created, **kwargs):
    """Create Profile and default UserRole when a User is created (e.g. createsuperuser). Superusers get super_admin role for RBAC."""
    if created:
        Profile.objects.get_or_create(user=instance, defaults={'email': instance.email})
        if instance.is_superuser:
            UserRole.objects.get_or_create(
                user=instance, role='super_admin', app_type=None, defaults={}
            )
        UserRole.objects.get_or_create(
            user=instance, role='user', app_type='calendar', defaults={}
        )


@receiver(post_save, sender=UserRole)
def ensure_employee_record_for_employee_role(sender, instance, created, **kwargs):
    """
    When a user gets role='employee' in user_roles, ensure they have a row in the
    scheduler Employee table. Employees must be stored in the employees table, not only in user_roles.
    """
    if instance.role != 'employee':
        return
    from scheduler.models import Employee
    user = instance.user
    if Employee.objects.filter(user=user).exists():
        return
    # Create minimal Employee record so they appear in Employee Management
    name_part = (getattr(user, 'email', '') or 'employee').split('@')[0]
    try:
        profile = user.profile
        full_name = (getattr(profile, 'full_name', None) or '').strip()
        if full_name:
            parts = full_name.split(None, 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ''
        else:
            first_name = name_part
            last_name = ''
    except Exception:
        first_name = name_part
        last_name = ''
    Employee.objects.create(
        user=user,
        first_name=first_name or 'Employee',
        last_name=last_name or '',
        email=user.email,
        status='active',
    )
