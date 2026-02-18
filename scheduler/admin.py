from django.contrib import admin
from .models import (
    Organization, Company, Department, ScheduleTeam, Employee,
    Shift, ShiftReplacementRequest, EmployeeAvailability,
    TimeClock, ScheduleTemplate, AppSettings
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization_manager', 'operations_manager', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'email', 'phone']


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'organization', 'company_manager', 'created_at']
    list_filter = ['type', 'field_type', 'created_at']
    search_fields = ['name', 'email', 'phone']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'created_at']
    list_filter = ['company', 'created_at']
    search_fields = ['name']


@admin.register(ScheduleTeam)
class ScheduleTeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'created_at']
    list_filter = ['company', 'created_at']
    search_fields = ['name', 'description']


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'company', 'department', 'status', 'hire_date']
    list_filter = ['status', 'company', 'department', 'hire_date']
    search_fields = ['first_name', 'last_name', 'email', 'phone', 'position']


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ['employee', 'company', 'start_time', 'end_time', 'status', 'is_missed']
    list_filter = ['status', 'is_missed', 'company', 'start_time']
    search_fields = ['notes']
    date_hierarchy = 'start_time'


@admin.register(ShiftReplacementRequest)
class ShiftReplacementRequestAdmin(admin.ModelAdmin):
    list_display = ['original_employee', 'replacement_employee', 'status', 'requested_at', 'reviewed_at']
    list_filter = ['status', 'requested_at', 'reviewed_at']
    search_fields = ['reviewer_notes']


@admin.register(EmployeeAvailability)
class EmployeeAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['employee', 'company', 'date', 'status']
    list_filter = ['status', 'date', 'company']
    search_fields = ['notes']
    date_hierarchy = 'date'


@admin.register(TimeClock)
class TimeClockAdmin(admin.ModelAdmin):
    list_display = ['employee', 'clock_in', 'clock_out', 'total_hours']
    list_filter = ['clock_in', 'clock_out']
    search_fields = ['notes']
    date_hierarchy = 'clock_in'


@admin.register(ScheduleTemplate)
class ScheduleTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'team', 'created_at']
    list_filter = ['company', 'created_at']
    search_fields = ['name', 'description']


@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'company_name', 'timezone', 'created_at']
    list_filter = ['timezone', 'created_at']
    search_fields = ['user__email', 'company_name']

