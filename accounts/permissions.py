from rest_framework import permissions
from .models import UserRole


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False


class HasRolePermission(permissions.BasePermission):
    """
    Permission class that checks if user has a specific role.
    """
    required_roles = []
    app_type = None
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers have all permissions
        if request.user.is_superuser:
            return True
        
        # Check if user has any of the required roles
        if not self.required_roles:
            return True
        
        user_roles = UserRole.objects.filter(user=request.user)
        
        # Filter by app_type if specified
        if self.app_type:
            user_roles = user_roles.filter(
                app_type__in=[self.app_type, None]  # None means role applies to all apps
            )
        
        role_names = user_roles.values_list('role', flat=True)
        
        # Check if user has any of the required roles
        return any(role in self.required_roles for role in role_names)


class IsAdminOrReadOnly(HasRolePermission):
    """Permission for admin-only write access"""
    required_roles = ['admin', 'super_admin']


class IsManagerOrReadOnly(HasRolePermission):
    """Permission for manager or admin write access"""
    required_roles = ['admin', 'super_admin', 'manager', 'operations_manager']


class IsSchedulerAdmin(HasRolePermission):
    """Permission for scheduler app admin access"""
    required_roles = ['admin', 'super_admin', 'operations_manager']
    app_type = 'scheduler'


class IsSchedulerManager(HasRolePermission):
    """Permission for scheduler app manager access"""
    required_roles = ['admin', 'super_admin', 'operations_manager', 'manager']
    app_type = 'scheduler'


class IsCalendarAdmin(HasRolePermission):
    """Permission for calendar app admin access"""
    required_roles = ['admin', 'super_admin']
    app_type = 'calendar'


class IsEmployeeOrManager(permissions.BasePermission):
    """
    Permission for employees to access their own data, managers to access their team's data.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Check if user is an employee or has manager role
        user_roles = UserRole.objects.filter(user=request.user)
        role_names = user_roles.values_list('role', flat=True)
        
        allowed_roles = ['admin', 'super_admin', 'manager', 'operations_manager', 'employee']
        return any(role in allowed_roles for role in role_names)
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        
        # If object has an employee field, check if it's the user's employee record
        if hasattr(obj, 'employee') and obj.employee:
            if hasattr(obj.employee, 'user') and obj.employee.user == request.user:
                return True
        
        # If object is an employee, check if it's the user's employee record
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        # Managers can access their team's data
        user_roles = UserRole.objects.filter(user=request.user)
        role_names = user_roles.values_list('role', flat=True)
        
        manager_roles = ['admin', 'super_admin', 'manager', 'operations_manager']
        if any(role in manager_roles for role in role_names):
            return True
        
        return False


class IsOwnerOrManager(permissions.BasePermission):
    """
    Permission that allows owners or managers to access objects.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        
        # Check if user is the owner
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        # Check if user is a manager
        user_roles = UserRole.objects.filter(user=request.user)
        role_names = user_roles.values_list('role', flat=True)
        
        manager_roles = ['admin', 'super_admin', 'manager', 'operations_manager']
        return any(role in manager_roles for role in role_names)

