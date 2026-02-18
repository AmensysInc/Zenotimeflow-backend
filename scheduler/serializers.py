from rest_framework import serializers
from .models import (
    Organization, Company, Department, ScheduleTeam, Employee,
    Shift, ShiftReplacementRequest, EmployeeAvailability,
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


class CompanySerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    company_manager_email = serializers.EmailField(source='company_manager.email', read_only=True)
    operations_manager_email = serializers.EmailField(source='operations_manager.email', read_only=True)
    
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'type', 'field_type', 'color', 'address',
            'phone', 'email', 'organization', 'organization_name',
            'company_manager', 'company_manager_email',
            'operations_manager', 'operations_manager_email',
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


class EmployeeSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'user_email', 'first_name', 'last_name', 'full_name',
            'email', 'phone', 'hire_date', 'hourly_rate', 'position', 'status',
            'company', 'company_name', 'department', 'department_name',
            'team', 'team_name', 'employee_pin', 'emergency_contact_name',
            'emergency_contact_phone', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'full_name', 'created_at', 'updated_at']


class ShiftSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.full_name', read_only=True)
    replacement_employee_name = serializers.CharField(source='replacement_employee.full_name', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)
    
    class Meta:
        model = Shift
        fields = [
            'id', 'employee', 'employee_name', 'replacement_employee',
            'replacement_employee_name', 'company', 'company_name',
            'department', 'department_name', 'team', 'team_name',
            'start_time', 'end_time', 'break_minutes', 'hourly_rate',
            'status', 'notes', 'is_missed', 'missed_at',
            'replacement_approved_at', 'replacement_started_at',
            'created_by', 'created_at', 'updated_at'
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

