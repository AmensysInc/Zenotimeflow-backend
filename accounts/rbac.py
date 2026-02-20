"""
Centralized RBAC (Role-Based Access Control) utility for ZenoTimeFlow.

RBAC Hierarchy:
- Super Admin: Full access to all resources
- Organization Manager: Access to companies within their assigned organization(s)
- Company Manager: Access to assigned company(ies) and employees within
- Employee: Access to own data and assigned shifts only

This module provides:
1. Permission checkers
2. Queryset scoping functions
3. RBAC validation helpers
"""

from typing import Set, Optional
from django.db.models import QuerySet, Q
from django.contrib.auth import get_user_model

User = get_user_model()


# ---------------------------------------------------------------------------
# RBAC Permission Checkers
# ---------------------------------------------------------------------------

def is_super_admin(user) -> bool:
    """Check if user is Super Admin (Django superuser or super_admin role)."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.roles.filter(role='super_admin').exists()


def is_organization_manager(user) -> bool:
    """Check if user manages at least one organization."""
    if not user or not user.is_authenticated:
        return False
    if is_super_admin(user):
        return True
    from scheduler.models import Organization
    return Organization.objects.filter(organization_manager_id=user.id).exists()


def is_company_manager(user) -> bool:
    """Check if user manages at least one company."""
    if not user or not user.is_authenticated:
        return False
    if is_super_admin(user):
        return True
    from scheduler.models import Company
    return Company.objects.filter(company_manager_id=user.id).exists()


def is_employee(user) -> bool:
    """Check if user has an Employee record."""
    if not user or not user.is_authenticated:
        return False
    from scheduler.models import Employee
    return Employee.objects.filter(user=user).exists()


def get_user_role(user) -> str:
    """Get primary role of user. Returns: 'super_admin', 'organization_manager', 'company_manager', 'employee', or 'user'."""
    if is_super_admin(user):
        return 'super_admin'
    if is_organization_manager(user):
        return 'organization_manager'
    if is_company_manager(user):
        return 'company_manager'
    if is_employee(user):
        return 'employee'
    return 'user'


# ---------------------------------------------------------------------------
# RBAC Scope Helpers (get accessible IDs)
# ---------------------------------------------------------------------------

def get_managed_organization_ids(user) -> Set[str]:
    """Get organization IDs user can access. Super Admin: all; Org Manager: assigned only."""
    if not user or not user.is_authenticated:
        return set()
    if is_super_admin(user):
        from scheduler.models import Organization
        return set(Organization.objects.values_list('id', flat=True))
    from scheduler.models import Organization
    return set(Organization.objects.filter(organization_manager_id=user.id).values_list('id', flat=True))


def get_manager_company(user):
    """
    Get the single company a Company Manager manages (TASK 1).
    Returns Company instance or None.
    Company Manager manages ONLY their assigned company (Company.company_manager FK).
    """
    if not user or not user.is_authenticated:
        return None
    if is_super_admin(user):
        return None  # Super Admin manages all, not a single company
    from scheduler.models import Company
    # Company Manager: get the company where they are assigned as company_manager
    return Company.objects.filter(company_manager_id=user.id).first()


def get_managed_company_ids(user) -> Set[str]:
    """Get company IDs user can access. Super Admin: all; Org Manager: companies in their orgs; Company Manager: assigned only."""
    if not user or not user.is_authenticated:
        return set()
    if is_super_admin(user):
        from scheduler.models import Company
        return set(Company.objects.values_list('id', flat=True))
    
    company_ids = set()
    # Companies where user is company_manager
    from scheduler.models import Company
    company_ids |= set(Company.objects.filter(company_manager_id=user.id).values_list('id', flat=True))
    
    # Companies in organizations this user manages (org manager)
    org_ids = get_managed_organization_ids(user)
    if org_ids:
        company_ids |= set(Company.objects.filter(organization_id__in=org_ids).values_list('id', flat=True))
    
    return company_ids


def get_accessible_employee_ids(user) -> Set[str]:
    """
    Get employee IDs user can view (TASK 2).
    - Super Admin: all employees
    - Organization Manager: employees in companies within their orgs (includes unassigned)
    - Company Manager: ONLY employees of their assigned company (no unassigned)
    - Employee: only self
    """
    if not user or not user.is_authenticated:
        return set()
    if is_super_admin(user):
        from scheduler.models import Employee
        return set(Employee.objects.values_list('id', flat=True))
    
    # Company Manager: ONLY their assigned company's employees (strict restriction)
    manager_company = get_manager_company(user)
    if manager_company:
        from scheduler.models import Employee
        return set(Employee.objects.filter(company_id=manager_company.id).values_list('id', flat=True))
    
    # Organization Manager: employees in companies within their orgs (includes unassigned for flexibility)
    company_ids = get_managed_company_ids(user)
    if company_ids:
        from scheduler.models import Employee
        emp_ids = set(Employee.objects.filter(company_id__in=company_ids).values_list('id', flat=True))
        # Org managers can see unassigned employees (for assignment)
        emp_ids |= set(Employee.objects.filter(company_id__isnull=True).values_list('id', flat=True))
        return emp_ids
    
    # No manager scope: if they have an employee record, they see only themselves
    from scheduler.models import Employee
    emp = Employee.objects.filter(user=user).first()
    if emp:
        return {emp.id}
    return set()


def get_accessible_shift_ids(user) -> Set[str]:
    """Get shift IDs user can access. Company Manager: shifts in their companies; Employee: own shifts only."""
    if not user or not user.is_authenticated:
        return set()
    if is_super_admin(user):
        from scheduler.models import Shift
        return set(Shift.objects.values_list('id', flat=True))
    
    company_ids = get_managed_company_ids(user)
    emp_ids = get_accessible_employee_ids(user)
    
    from scheduler.models import Shift
    shift_ids = set(Shift.objects.filter(
        Q(company_id__in=company_ids) | Q(employee_id__in=emp_ids)
    ).values_list('id', flat=True))
    
    return shift_ids


# ---------------------------------------------------------------------------
# RBAC Queryset Scoping Functions
# ---------------------------------------------------------------------------

def scope_organization_queryset(user, queryset: Optional[QuerySet] = None):
    """Return Organization queryset visible to user. Super Admin: all; Org Manager: assigned only."""
    from scheduler.models import Organization
    qs = queryset if queryset is not None else Organization.objects.all()
    if is_super_admin(user):
        return qs
    org_ids = get_managed_organization_ids(user)
    return qs.filter(id__in=org_ids)


def scope_company_queryset(user, queryset: Optional[QuerySet] = None):
    """Return Company queryset visible to user. Super Admin: all; Org/Company Manager: by scope."""
    from scheduler.models import Company
    qs = queryset if queryset is not None else Company.objects.all()
    if is_super_admin(user):
        return qs
    company_ids = get_managed_company_ids(user)
    return qs.filter(id__in=company_ids)


def scope_employee_queryset(user, queryset: Optional[QuerySet] = None):
    """Return Employee queryset visible to user. RBAC: Super Admin=all; Managers=by company scope; Employee=self only."""
    from scheduler.models import Employee
    qs = queryset if queryset is not None else Employee.objects.all()
    if is_super_admin(user):
        return qs
    emp_ids = get_accessible_employee_ids(user)
    return qs.filter(id__in=emp_ids)


def scope_shift_queryset(user, queryset: Optional[QuerySet] = None):
    """Return Shift queryset visible to user. Company Manager: shifts in their companies; Employee: own shifts only."""
    from scheduler.models import Shift
    qs = queryset if queryset is not None else Shift.objects.all()
    if is_super_admin(user):
        return qs
    company_ids = get_managed_company_ids(user)
    emp_ids = get_accessible_employee_ids(user)
    return qs.filter(Q(company_id__in=company_ids) | Q(employee_id__in=emp_ids)).distinct()


# ---------------------------------------------------------------------------
# RBAC Validation Helpers
# ---------------------------------------------------------------------------

def can_access_organization(user, organization_id: str) -> bool:
    """Check if user can access a specific organization."""
    if is_super_admin(user):
        return True
    return organization_id in get_managed_organization_ids(user)


def can_access_company(user, company_id: str) -> bool:
    """Check if user can access a specific company."""
    if is_super_admin(user):
        return True
    return company_id in get_managed_company_ids(user)


def can_access_employee(user, employee_id: str) -> bool:
    """Check if user can access a specific employee."""
    if is_super_admin(user):
        return True
    return employee_id in get_accessible_employee_ids(user)


def can_access_shift(user, shift_id: str) -> bool:
    """Check if user can access a specific shift."""
    if is_super_admin(user):
        return True
    return shift_id in get_accessible_shift_ids(user)


def can_create_shift(user, company_id: str) -> bool:
    """Check if user can create shifts for a company. Company Manager only."""
    if is_super_admin(user):
        return True
    if is_organization_manager(user):
        # Org managers can create shifts for companies in their orgs
        return can_access_company(user, company_id)
    if is_company_manager(user):
        # Company managers can create shifts for their assigned companies
        return can_access_company(user, company_id)
    return False


def can_modify_shift(user, shift_id: str) -> bool:
    """Check if user can modify a specific shift. Company Manager or shift creator."""
    if is_super_admin(user):
        return True
    if not can_access_shift(user, shift_id):
        return False
    # Company managers can modify shifts in their companies
    if is_company_manager(user) or is_organization_manager(user):
        return True
    # Employees can modify their own shifts if not yet started
    from scheduler.models import Shift
    try:
        shift = Shift.objects.get(id=shift_id)
        if shift.employee and shift.employee.user == user:
            from django.utils import timezone
            if shift.start_time > timezone.now():
                return True
    except Shift.DoesNotExist:
        pass
    return False
