from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class Organization(models.Model):
    """Organization model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    color = models.CharField(max_length=7, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    organization_manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_organizations'
    )
    operations_manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operations_managed_organizations'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_organizations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'organizations'
        ordering = ['name']
        # SaaS Indexes: Optimize role-based queries (Organization Manager, Operations Manager)
        indexes = [
            models.Index(fields=['organization_manager'], name='org_manager_idx'),
            models.Index(fields=['operations_manager'], name='org_ops_manager_idx'),
            models.Index(fields=['created_by'], name='org_created_by_idx'),
            models.Index(fields=['created_at'], name='org_created_at_idx'),
        ]
    
    def __str__(self):
        return self.name


class Company(models.Model):
    """Company model"""
    TYPE_CHOICES = [
        ('IT', 'IT'),
        ('Non-IT', 'Non-IT'),
    ]
    
    FIELD_TYPE_CHOICES = [
        ('IT', 'IT'),
        ('Non-IT', 'Non-IT'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50)
    field_type = models.CharField(max_length=50, choices=FIELD_TYPE_CHOICES, null=True, blank=True)
    color = models.CharField(max_length=7, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='companies',
        null=True,
        blank=True
    )
    company_manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_companies'
    )
    operations_manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operations_managed_companies'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_companies'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'companies'
        ordering = ['name']
        verbose_name_plural = 'companies'
        # SaaS Indexes: Multi-tenant filtering by organization, role-based access
        indexes = [
            models.Index(fields=['organization'], name='company_org_idx'),  # Critical for tenant isolation
            models.Index(fields=['company_manager'], name='company_manager_idx'),
            models.Index(fields=['operations_manager'], name='company_ops_manager_idx'),
            models.Index(fields=['organization', 'name'], name='company_org_name_idx'),  # Composite for filtered lists
            models.Index(fields=['created_at'], name='company_created_at_idx'),
        ]
    
    def __str__(self):
        return self.name


class Department(models.Model):
    """Department model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    color = models.CharField(max_length=7, null=True, blank=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='departments',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'departments'
        ordering = ['name']
        # SaaS Index: Filter departments by company (multi-tenant)
        indexes = [
            models.Index(fields=['company'], name='dept_company_idx'),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.company.name if self.company else 'No Company'}"


class ScheduleTeam(models.Model):
    """Schedule Team model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    color = models.CharField(max_length=7, null=True, blank=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='teams'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_teams'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'schedule_teams'
        ordering = ['name']
        # SaaS Index: Filter teams by company (multi-tenant)
        indexes = [
            models.Index(fields=['company'], name='team_company_idx'),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.company.name}"


class Employee(models.Model):
    """
    Dedicated Employee table: one record per user (OneToOne).
    Links to User (single source of truth for auth) and Company.
    Employee-specific fields only; created when a user is created with role=employee.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('on_leave', 'On Leave'),
        ('terminated', 'Terminated'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # OneToOne: one user has at most one Employee record; prevents duplicate employee profiles
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employee_profile'
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, null=True, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    position = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='active')
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='employees',
        null=True,
        blank=True
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees'
    )
    team = models.ForeignKey(
        ScheduleTeam,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees'
    )
    employee_pin = models.CharField(max_length=10, null=True, blank=True)
    emergency_contact_name = models.CharField(max_length=255, null=True, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'employees'
        ordering = ['last_name', 'first_name']
        # OneToOneField on user enforces at most one Employee per user
        indexes = [
            models.Index(fields=['company'], name='employee_company_idx'),  # Critical for tenant isolation
            models.Index(fields=['user'], name='employee_user_idx'),  # User-Employee relationship
            models.Index(fields=['status'], name='employee_status_idx'),  # Filter by active/inactive
            models.Index(fields=['email'], name='employee_email_idx'),  # Email lookups
            models.Index(fields=['company', 'status'], name='employee_company_status_idx'),  # Composite: active employees per company
            models.Index(fields=['company', 'department'], name='employee_company_dept_idx'),  # Department filtering
            models.Index(fields=['hire_date'], name='employee_hire_date_idx'),  # Date range queries
        ]
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __str__(self):
        return f"{self.full_name} - {self.company.name if self.company else 'No Company'}"


class Shift(models.Model):
    """Shift model"""
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('missed', 'Missed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='shifts',
        null=True,
        blank=True
    )
    replacement_employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replacement_shifts'
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='shifts',
        null=True,
        blank=True
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shifts'
    )
    team = models.ForeignKey(
        ScheduleTeam,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shifts'
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    break_minutes = models.IntegerField(default=0)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='scheduled')
    is_published = models.BooleanField(default=False, help_text='False=draft; employees only see published shifts')
    notes = models.TextField(null=True, blank=True)
    is_missed = models.BooleanField(default=False)
    missed_at = models.DateTimeField(null=True, blank=True)
    replacement_approved_at = models.DateTimeField(null=True, blank=True)
    replacement_started_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_shifts'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'shifts'
        ordering = ['start_time']
        # SaaS Indexes: Time-range queries, employee schedules, company filtering
        indexes = [
            models.Index(fields=['company'], name='shift_company_idx'),  # Tenant isolation
            models.Index(fields=['employee'], name='shift_employee_idx'),  # Employee schedule queries
            models.Index(fields=['start_time', 'end_time'], name='shift_time_range_idx'),  # Time range queries
            models.Index(fields=['company', 'start_time'], name='shift_company_time_idx'),  # Company schedules
            models.Index(fields=['status'], name='shift_status_idx'),  # Filter by status
        ]
    
    def __str__(self):
        return f"{self.employee.full_name if self.employee else 'Unassigned'} - {self.start_time}"


class ShiftTask(models.Model):
    """Task/responsibility assigned to a shift. Shown to employee when they clock in.
    Syncs to CalendarEvent so employee sees it in Calendar and Tasks."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shift = models.ForeignKey(
        Shift,
        on_delete=models.CASCADE,
        related_name='shift_tasks'
    )
    title = models.CharField(max_length=255)
    order = models.PositiveSmallIntegerField(default=0)
    calendar_event_id = models.UUIDField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'shift_tasks'
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.title} (shift {self.shift_id})"


class ShiftReplacementRequest(models.Model):
    """Shift replacement request model"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shift = models.ForeignKey(
        Shift,
        on_delete=models.CASCADE,
        related_name='replacement_requests'
    )
    original_employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='replacement_requests_sent'
    )
    replacement_employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='replacement_requests_received'
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='replacement_requests'
    )
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_replacement_requests'
    )
    reviewer_notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'shift_replacement_requests'
        ordering = ['-requested_at']
    
    def __str__(self):
        return f"{self.original_employee.full_name} -> {self.replacement_employee.full_name} - {self.status}"


class EmployeeAvailability(models.Model):
    """Employee availability model"""
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('unavailable', 'Unavailable'),
        ('maybe', 'Maybe'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='availability'
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='employee_availability'
    )
    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='available')
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'employee_availability'
        unique_together = [['employee', 'company', 'date']]
        ordering = ['date']
    
    def __str__(self):
        return f"{self.employee.full_name} - {self.date} - {self.status}"


class TimeClock(models.Model):
    """Time clock entry model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='time_clock_entries',
        null=True,
        blank=True
    )
    shift = models.ForeignKey(
        Shift,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='time_clock_entries'
    )
    clock_in = models.DateTimeField(null=True, blank=True)
    clock_out = models.DateTimeField(null=True, blank=True)
    break_start = models.DateTimeField(null=True, blank=True)
    break_end = models.DateTimeField(null=True, blank=True)
    total_hours = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    overtime_hours = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'time_clock'
        ordering = ['-clock_in']
    
    def __str__(self):
        return f"{self.employee.full_name if self.employee else 'Unknown'} - {self.clock_in}"


class ScheduleTemplate(models.Model):
    """Schedule template model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='schedule_templates',
        null=True,
        blank=True
    )
    team = models.ForeignKey(
        ScheduleTeam,
        on_delete=models.CASCADE,
        related_name='schedule_templates',
        null=True,
        blank=True
    )
    template_data = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_schedule_templates'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'schedule_templates'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class AppSettings(models.Model):
    """Application settings model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='app_settings'
    )
    company_name = models.CharField(max_length=255, null=True, blank=True)
    admin_email = models.EmailField(null=True, blank=True)
    timezone = models.CharField(max_length=50, null=True, blank=True)
    week_start_day = models.CharField(max_length=20, null=True, blank=True)
    clock_in_grace_period = models.IntegerField(null=True, blank=True)  # in minutes
    break_duration = models.IntegerField(null=True, blank=True)  # in minutes
    overtime_threshold = models.IntegerField(null=True, blank=True)  # in hours
    data_retention_period = models.IntegerField(null=True, blank=True)  # in days
    shift_reminders = models.BooleanField(default=True)
    clock_in_reminders = models.BooleanField(default=True)
    overtime_alerts = models.BooleanField(default=True)
    schedule_changes = models.BooleanField(default=True)
    auto_approve_time_off = models.BooleanField(default=False)
    allow_mobile_clock_in = models.BooleanField(default=True)
    require_clock_in_location = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'app_settings'
        verbose_name_plural = 'app settings'
    
    def __str__(self):
        return f"Settings for {self.user.email}"

