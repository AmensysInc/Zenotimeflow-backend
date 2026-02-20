#!/usr/bin/env python
"""Create a superadmin user. Run: python create_superadmin.py"""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zeno_time.settings')

import django
django.setup()

from accounts.models import User, UserRole

# Default superadmin credentials (change in production)
EMAIL = os.environ.get('SUPERADMIN_EMAIL', 'admin@zenotimeflow.com')
USERNAME = os.environ.get('SUPERADMIN_USERNAME', 'Superadmin')
PASSWORD = os.environ.get('SUPERADMIN_PASSWORD', 'Admin@123')

if User.objects.filter(email=EMAIL).exists():
    user = User.objects.get(email=EMAIL)
    if not user.is_superuser:
        user.is_superuser = True
        user.is_staff = True
        user.save()
        print(f"Updated existing user to superadmin: {EMAIL}")
    else:
        print(f"Superadmin already exists: {EMAIL}")
    # Reset password so you can login with SUPERADMIN_PASSWORD (e.g. Admin@123)
    user.set_password(PASSWORD)
    user.save()
    # Ensure RBAC super_admin role exists for login/role checks
    UserRole.objects.get_or_create(user=user, role='super_admin', app_type=None, defaults={})
    print(f"Password reset. Use email: {EMAIL} and password: {PASSWORD} to login.")
else:
    user = User.objects.create_superuser(email=EMAIL, username=USERNAME, password=PASSWORD)
    UserRole.objects.get_or_create(user=user, role='super_admin', app_type=None, defaults={})
    print("Superadmin created successfully!")
    print()
    print("=" * 50)
    print("SUPERADMIN LOGIN CREDENTIALS")
    print("=" * 50)
    print("Login URL (Django Admin): http://127.0.0.1:8000/admin/")
    print("Login URL (API):          http://127.0.0.1:8000/api/accounts/login/")
    print()
    print("Email (use this to log in):", EMAIL)
    print("Password:                 ", PASSWORD)
    print()
    print("=" * 50)
    print("Change this password in production!")
    print("=" * 50)
