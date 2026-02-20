from rest_framework import permissions
from .models import UserRole


# ---------------------------------------------------------------------------
# RBAC: Zeno-time-flow role hierarchy
# Super Admin > Organization Manager > Company Manager > Employee
# ---------------------------------------------------------------------------

class IsSuperAdmin(permissions.BasePermission):
    """Only Super Admin (Django superuser or super_admin role) has permission."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_super_admin()


class IsSuperAdminOrReadOnly(permissions.BasePermission):
    """
    Allow GET/HEAD/OPTIONS for any authenticated user; allow POST/PUT/PATCH/DELETE only for Super Admin.
    Use on user list/create so only Super Admin can create users; others can list (filtered by get_queryset).
    """
    message = 'Only Super Admin can create or modify users.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_super_admin()


class IsOrganizationManagerOrAbove(permissions.BasePermission):
    """Super Admin or user who manages at least one organization."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_super_admin() or request.user.is_organization_manager()


class IsCompanyManagerOrAbove(permissions.BasePermission):
    """Super Admin, Org Manager, or user who manages at least one company."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            request.user.is_super_admin()
            or request.user.is_organization_manager()
            or request.user.is_company_manager()
        )


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
        
        # Super Admin (Django superuser OR super_admin role) has all permissions
        if request.user.is_super_admin():
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
    """Permission for scheduler app admin access. RBAC: Super Admin + Org/Company managers (by assignment)."""
    required_roles = ['admin', 'super_admin', 'operations_manager', 'organization_manager', 'company_manager']
    app_type = 'scheduler'


class IsSchedulerManager(HasRolePermission):
    """Permission for scheduler app manager access."""
    required_roles = ['admin', 'super_admin', 'operations_manager', 'manager', 'organization_manager', 'company_manager']
    app_type = 'scheduler'


class IsCalendarAdmin(HasRolePermission):
    """Permission for calendar app admin access"""
    required_roles = ['admin', 'super_admin']
    app_type = 'calendar'


class IsEmployeeOrManager(permissions.BasePermission):
    """
    RBAC: Employees can access own data; Org/Company managers and Super Admin can access by scope.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_super_admin():
            return True
        # Any user with managed org/company or an employee record can access employee-related views
        return (
            request.user.is_organization_manager()
            or request.user.is_company_manager()
            or request.user.is_employee_role()
        )


class IsEmployeeOrManagerOrReadOnly(permissions.BasePermission):
    """
    Allow GET/HEAD/OPTIONS for any authenticated user (list/retrieve); allow create/update/delete only for managers/employees.
    Use on EmployeeViewSet so the Employee Management page loads for all users; get_queryset still filters by RBAC.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_super_admin():
            return True
        return (
            request.user.is_organization_manager()
            or request.user.is_company_manager()
            or request.user.is_employee_role()
        )

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_super_admin():
            return True
        # Employee object: owner or in scope
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        if getattr(obj, 'id', None) and obj.id in request.user.get_accessible_employee_ids():
            return True
        # TimeClock/Shift etc: employee-owned or in scope
        if hasattr(obj, 'employee') and obj.employee:
            if hasattr(obj.employee, 'user') and obj.employee.user == request.user:
                return True
            if getattr(obj, 'employee_id', None) and obj.employee_id in request.user.get_accessible_employee_ids():
                return True
        if getattr(obj, 'employee_id', None) and obj.employee_id in request.user.get_accessible_employee_ids():
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
        
        manager_roles = ['admin', 'super_admin', 'manager', 'operations_manager', 'organization_manager', 'company_manager']
        return any(role in manager_roles for role in role_names)


# ---------------------------------------------------------------------------
# RBAC Queryset scoping: use in ViewSet.get_queryset() to enforce data filtering
# Delegates to centralized rbac module for consistency
# ---------------------------------------------------------------------------

def get_organization_queryset_for_user(user, base_queryset=None):
    """Return Organization queryset visible to user. Super Admin: all; Org Manager: assigned only."""
    from accounts.rbac import scope_organization_queryset
    return scope_organization_queryset(user, base_queryset)


def get_company_queryset_for_user(user, base_queryset=None):
    """Return Company queryset visible to user. Super Admin: all; Org/Company Manager: by scope."""
    from accounts.rbac import scope_company_queryset
    return scope_company_queryset(user, base_queryset)


def get_employee_queryset_for_user(user, base_queryset=None):
    """Return Employee table queryset visible to user. RBAC: Super Admin=all; Managers=by company scope; Employee=self only."""
    from accounts.rbac import scope_employee_queryset
    return scope_employee_queryset(user, base_queryset)


def get_shift_queryset_for_user(user, base_queryset=None):
    """Return Shift queryset visible to user. Company Manager: shifts in their companies; Employee: own shifts only."""
    from accounts.rbac import scope_shift_queryset
    return scope_shift_queryset(user, base_queryset)

