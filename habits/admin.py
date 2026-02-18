from django.contrib import admin
from .models import Habit, HabitCompletion


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'frequency', 'streak_count', 'longest_streak', 'is_active', 'created_at']
    list_filter = ['frequency', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    date_hierarchy = 'created_at'


@admin.register(HabitCompletion)
class HabitCompletionAdmin(admin.ModelAdmin):
    list_display = ['habit', 'completion_date', 'count', 'completion_time']
    list_filter = ['completion_date', 'completion_time']
    search_fields = ['habit__name', 'notes']
    date_hierarchy = 'completion_date'

