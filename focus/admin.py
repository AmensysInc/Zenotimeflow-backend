from django.contrib import admin
from .models import FocusSession, FocusBlock


@admin.register(FocusSession)
class FocusSessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'status', 'planned_duration', 'actual_duration', 'start_time', 'created_at']
    list_filter = ['status', 'category', 'start_time', 'created_at']
    search_fields = ['title', 'description', 'notes']
    date_hierarchy = 'created_at'


@admin.register(FocusBlock)
class FocusBlockAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'start_time', 'end_time', 'is_recurring', 'created_at']
    list_filter = ['is_recurring', 'start_time', 'created_at']
    search_fields = ['title']
    date_hierarchy = 'start_time'

