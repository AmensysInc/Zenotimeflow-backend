#!/usr/bin/env python
"""Test user list endpoint for super admin"""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zeno_time.settings')

import django
django.setup()

from accounts.models import User

print("=" * 60)
print("Testing User List for Super Admin")
print("=" * 60)
print()

# Check super admin
super_admin = User.objects.filter(email='admin@zenotimeflow.com').first()
if super_admin:
    print(f"Super Admin found: {super_admin.email}")
    print(f"  is_superuser: {super_admin.is_superuser}")
    print(f"  is_super_admin(): {super_admin.is_super_admin()}")
    print(f"  Roles: {list(super_admin.roles.values_list('role', flat=True))}")
    print()
    
    # Test queryset
    from accounts.views import UserListView
    from rest_framework.test import APIRequestFactory
    from rest_framework.request import Request
    
    factory = APIRequestFactory()
    request = factory.get('/api/auth/users/')
    request.user = super_admin
    
    view = UserListView()
    view.request = Request(request)
    view.format_kwarg = None
    
    queryset = view.get_queryset()
    user_count = queryset.count()
    
    print(f"Users visible to Super Admin: {user_count}")
    if user_count > 0:
        print("Sample users:")
        for u in queryset[:5]:
            print(f"  - {u.email} (active: {u.is_active})")
    else:
        print("⚠️  No users found! This might be why the frontend shows empty list.")
    print()
else:
    print("⚠️  Super Admin not found. Run: D:\\Django\\python.exe create_superadmin.py")
    print()

# List all users
all_users = User.objects.all()
print(f"Total users in database: {all_users.count()}")
if all_users.exists():
    print("All users:")
    for u in all_users:
        print(f"  - {u.email} (superuser: {u.is_superuser}, active: {u.is_active})")
print()
print("=" * 60)
