from rest_framework import serializers
from .models import (
    Organization, Company, Department, ScheduleTeam, Employee,
    Shift, ShiftTask, ShiftReplacementRequest, EmployeeAvailability,
    TimeClock, ScheduleTemplate, AppSettings
)
from accounts.models import User


class OrganizationSerializer(serializers.ModelSerializer):
    organization_manager_email = serializers.EmailField(source='organization_manager.email', read_only=True)
    operations_manager_email = serializers.EmailField(source='operations_manager.email', read_only=True)
    
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'color', 'address', 'phone', 'email',
            'organization_manager', 'organization_manager_email',
            'operations_manager', 'operations_manager_email',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CompanyManagerSerializer(serializers.ModelSerializer):
    """Nested manager details for company/manager window."""
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        if not obj:
            return None
        return f"{obj.first_name or ''} {obj.last_name or ''}".strip() or obj.email

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'is_active']


class CompanySerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    company_manager_email = serializers.EmailField(source='company_manager.email', read_only=True)
    operations_manager_email = serializers.EmailField(source='operations_manager.email', read_only=True)
    company_manager_details = serializers.SerializerMethodField()
    employees_count = serializers.SerializerMethodField()
    employees_preview = serializers.SerializerMethodField()

    def get_company_manager_details(self, obj):
        """Full manager details for the manager window (id, email, name)."""
        if not obj.company_manager_id:
            return None
        try:
            return CompanyManagerSerializer(obj.company_manager).data
        except Exception:
            return None

    def get_employees_count(self, obj):
        """A company can have any number of employees."""
        return obj.employees.count() if hasattr(obj, 'employees') else 0

    def get_employees_preview(self, obj):
        """List of employees in this company (supports multiple employees per company)."""
        if not hasattr(obj, 'employees'):
            return []
        return [
            {'id': str(e.id), 'full_name': e.full_name, 'email': e.email, 'status': e.status}
            for e in obj.employees.all()[:50]
        ]

    class Meta:
        model = Company
        fields = [
            'id', 'name', 'type', 'field_type', 'color', 'address',
            'phone', 'email', 'organization', 'organization_name',
            'company_manager', 'company_manager_email', 'company_manager_details',
            'operations_manager', 'operations_manager_email',
            'employees_count', 'employees_preview',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DepartmentSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    class Meta:
        model = Department
        fields = [
            'id', 'name', 'color', 'company', 'company_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ScheduleTeamSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    class Meta:
        model = ScheduleTeam
        fields = [
            'id', 'name', 'description', 'color', 'company', 'company_name',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmployeeUserSerializer(serializers.ModelSerializer):
    """Minimal user info nested in Employee response; single source of truth in User table."""
    class Meta:
        model = User
        fields = ['id', 'email', 'is_active', 'first_name', 'last_name']


class EmployeeSerializer(serializers.ModelSerializer):
    """
    Employee in dedicated table; linked to User (OneToOne) and Company.
    Employees are stored in the employees table; company can be set on create or assigned later via PATCH.
    """
    full_name = serializers.CharField(read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_info = serializers.SerializerMethodField()
    # Accept company_id from client (maps to company FK)
    company_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)

    def get_user_info(self, obj):
        """Nested user info for Employee Management UI; User table remains source of truth."""
        if not obj.user_id:
            return None
        return EmployeeUserSerializer(obj.user).data

    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'user_email', 'user_info', 'first_name', 'last_name', 'full_name',
            'email', 'phone', 'hire_date', 'hourly_rate', 'position', 'status',
            'company', 'company_id', 'company_name', 'department', 'department_name',
            'team', 'team_name', 'employee_pin', 'emergency_contact_name',
            'emergency_contact_phone', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'full_name', 'created_at', 'updated_at']
        extra_kwargs = {'company': {'required': False, 'allow_null': True}}

    def validate_company(self, value):
        """Company must exist when provided."""
        if value is not None:
            from .models import Company
            if not Company.objects.filter(id=value.id).exists():
                raise serializers.ValidationError('Company not found.')
        return value

    def validate(self, attrs):
        """Map company_id to company; prevent duplicate Employee per User."""
        # Allow client to send company_id instead of (or in addition to) company
        company_id = attrs.pop('company_id', None)
        if company_id is not None:
            from .models import Company
            try:
                attrs['company'] = Company.objects.get(id=company_id)
            except Company.DoesNotExist:
                raise serializers.ValidationError({'company_id': 'Company not found.'})

        # Employee must be stored in employees table; one record per user
        if not self.instance and attrs.get('user'):
            if Employee.objects.filter(user=attrs['user']).exists():
                raise serializers.ValidationError(
                    {'user': 'This user already has an employee record. One user can have only one employee profile.'}
                )
        return attrs


class ShiftTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShiftTask
        fields = ['id', 'shift', 'title', 'order', 'calendar_event_id', 'created_at']
        read_only_fields = ['id', 'calendar_event_id', 'created_at']


class ShiftSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    replacement_employee_name = serializers.CharField(source='replacement_employee.full_name', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)
    shift_tasks = ShiftTaskSerializer(many=True, read_only=True)

    def validate(self, attrs):
        # Merge with instance for PATCH so we validate full data
        employee = attrs.get('employee')
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')
        if self.instance:
            if employee is None:
                employee = self.instance.employee
            if start_time is None:
                start_time = self.instance.start_time
            if end_time is None:
                end_time = self.instance.end_time
        if employee and start_time and end_time:
            qs = Shift.objects.filter(
                employee=employee,
                start_time=start_time,
                end_time=end_time,
            ).exclude(status='cancelled')
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    'This employee is already scheduled for this time slot. Duplicate shifts are not allowed.'
                )
        return attrs

    class Meta:
        model = Shift
        fields = [
            'id', 'employee', 'employee_name', 'replacement_employee',
            'replacement_employee_name', 'company', 'company_name',
            'department', 'department_name', 'team', 'team_name',
            'start_time', 'end_time', 'break_minutes', 'hourly_rate',
            'status', 'is_published', 'notes', 'is_missed', 'missed_at',
            'replacement_approved_at', 'replacement_started_at',
            'created_by', 'created_at', 'updated_at',
            'shift_tasks',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ShiftReplacementRequestSerializer(serializers.ModelSerializer):
    shift_details = ShiftSerializer(source='shift', read_only=True)
    original_employee_name = serializers.CharField(source='original_employee.full_name', read_only=True)
    replacement_employee_name = serializers.CharField(source='replacement_employee.full_name', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    reviewer_email = serializers.EmailField(source='reviewed_by.email', read_only=True)
    
    class Meta:
        model = ShiftReplacementRequest
        fields = [
            'id', 'shift', 'shift_details', 'original_employee', 'original_employee_name',
            'replacement_employee', 'replacement_employee_name', 'company', 'company_name',
            'status', 'requested_at', 'reviewed_at', 'reviewed_by', 'reviewer_email',
            'reviewer_notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'requested_at', 'created_at', 'updated_at']


class EmployeeAvailabilitySerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    class Meta:
        model = EmployeeAvailability
        fields = [
            'id', 'employee', 'employee_name', 'company', 'company_name',
            'date', 'start_time', 'end_time', 'status', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TimeClockSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    shift_details = ShiftSerializer(source='shift', read_only=True)
    
    class Meta:
        model = TimeClock
        fields = [
            'id', 'employee', 'employee_name', 'shift', 'shift_details',
            'clock_in', 'clock_out', 'break_start', 'break_end',
            'total_hours', 'overtime_hours', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ScheduleTemplateSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)
    
    class Meta:
        model = ScheduleTemplate
        fields = [
            'id', 'name', 'description', 'company', 'company_name',
            'team', 'team_name', 'template_data', 'created_by',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AppSettingsSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = AppSettings
        fields = [
            'id', 'user', 'user_email', 'company_name', 'admin_email',
            'timezone', 'week_start_day', 'clock_in_grace_period',
            'break_duration', 'overtime_threshold', 'data_retention_period',
            'shift_reminders', 'clock_in_reminders', 'overtime_alerts',
            'schedule_changes', 'auto_approve_time_off',
            'allow_mobile_clock_in', 'require_clock_in_location',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

