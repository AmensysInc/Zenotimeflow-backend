from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


# ---------------------------------------------------------------------------
# RBAC Role constants (Zeno-time-flow hierarchy: Super Admin > Org Manager > Company Manager > Employee)
# ---------------------------------------------------------------------------
class User(AbstractUser):
    """Custom User model with RBAC role helpers."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'auth_user'
    
    def __str__(self):
        return self.email
    
    # ---------------------------------------------------------------------------
    # RBAC: Role helper methods (hierarchy-aware; Super Admin has full access)
    # ---------------------------------------------------------------------------
    
    def is_super_admin(self):
        """True if user has global access (Django superuser or super_admin role)."""
        if self.is_superuser:
            return True
        return self.roles.filter(role='super_admin').exists()
    
    def is_organization_manager(self):
        """True if user manages at least one organization (assigned as organization_manager)."""
        if self.is_super_admin():
            return True
        from scheduler.models import Organization
        return Organization.objects.filter(organization_manager_id=self.id).exists()
    
    def is_company_manager(self):
        """True if user manages at least one company (assigned as company_manager)."""
        if self.is_super_admin():
            return True
        from scheduler.models import Company
        return Company.objects.filter(company_manager_id=self.id).exists()
    
    def is_employee_role(self):
        """True if user has an Employee record (staff member in a company)."""
        from scheduler.models import Employee
        return Employee.objects.filter(user=self).exists()
    
    def get_managed_organization_ids(self):
        """Organization IDs this user can access. Super Admin: all; Org Manager: assigned orgs only."""
        from scheduler.models import Organization
        if self.is_super_admin():
            return set(Organization.objects.values_list('id', flat=True))
        # Use organization_manager_id so Org/Company managers see their scope reliably
        return set(Organization.objects.filter(organization_manager_id=self.id).values_list('id', flat=True))
    
    def get_managed_company_ids(self):
        """Company IDs this user can access. Super Admin: all; Org Manager: companies in their orgs; Company Manager: assigned companies only."""
        from scheduler.models import Company, Organization
        if self.is_super_admin():
            return set(Company.objects.values_list('id', flat=True))
        # Companies where user is company_manager (use _id for reliable lookup)
        company_ids = set(Company.objects.filter(company_manager_id=self.id).values_list('id', flat=True))
        # Companies in organizations this user manages (org manager)
        org_ids = self.get_managed_organization_ids()
        if org_ids:
            company_ids |= set(Company.objects.filter(organization_id__in=org_ids).values_list('id', flat=True))
        return company_ids
    
    def get_employee_record(self):
        """Employee record for this user, or None."""
        from scheduler.models import Employee
        return Employee.objects.filter(user=self).first()
    
    def get_accessible_employee_ids(self):
        """Employee IDs this user can view. Super Admin/Managers: by scope; pure Employee: only self."""
        from scheduler.models import Employee
        if self.is_super_admin():
            return set(Employee.objects.values_list('id', flat=True))
        company_ids = self.get_managed_company_ids()
        # Org/Company managers: employees in their companies; also include employees with no company (unassigned)
        if company_ids:
            emp_ids = set(Employee.objects.filter(company_id__in=company_ids).values_list('id', flat=True))
            emp_ids |= set(Employee.objects.filter(company_id__isnull=True).values_list('id', flat=True))
            return emp_ids
        # No manager scope: if they have an employee record, they see only themselves
        emp = self.get_employee_record()
        if emp:
            return {emp.id}
        return set()


class Profile(models.Model):
    """User profile with additional information"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    email = models.EmailField()
    full_name = models.CharField(max_length=255, null=True, blank=True)
    avatar_url = models.URLField(null=True, blank=True)
    mobile_number = models.CharField(max_length=20, null=True, blank=True)
    status = models.CharField(max_length=50, default='active')
    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinates'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'profiles'
    
    def __str__(self):
        return f"{self.full_name or self.email} - {self.user.email}"


class UserRole(models.Model):
    """User roles and app type associations. RBAC: Super Admin, Organization Manager, Company Manager, Employee."""
    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('organization_manager', 'Organization Manager'),
        ('company_manager', 'Company Manager'),
        ('employee', 'Employee'),
        ('user', 'User'),
        ('admin', 'Admin'),
        ('operations_manager', 'Operations Manager'),
        ('manager', 'Manager'),
        ('candidate', 'Candidate'),
        ('house_keeping', 'House Keeping'),
        ('maintenance', 'Maintenance'),
    ]
    
    APP_TYPE_CHOICES = [
        ('calendar', 'Calendar'),
        ('scheduler', 'Scheduler'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='roles')
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='user')
    app_type = models.CharField(max_length=50, choices=APP_TYPE_CHOICES, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_roles'
        unique_together = [['user', 'role', 'app_type']]
    
    def __str__(self):
        return f"{self.user.email} - {self.role} ({self.app_type or 'all'})"

