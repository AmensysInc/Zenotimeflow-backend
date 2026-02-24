from django.contrib import admin
from .models import LearningTemplate, TemplateAssignment


@admin.register(LearningTemplate)
class LearningTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'technology', 'created_by', 'created_at']
    search_fields = ['name', 'description', 'technology']


@admin.register(TemplateAssignment)
class TemplateAssignmentAdmin(admin.ModelAdmin):
    list_display = ['template', 'user', 'assigned_by', 'assigned_at']
    list_filter = ['template']
