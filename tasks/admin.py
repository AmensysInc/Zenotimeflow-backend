from django.contrib import admin
from .models import Task, TaskComment, TaskAttachment


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'status', 'priority', 'due_date', 'created_at']
    list_filter = ['status', 'priority', 'is_template', 'created_at', 'due_date']
    search_fields = ['title', 'description']
    filter_horizontal = ['assigned_to']
    date_hierarchy = 'created_at'


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ['task', 'user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['content']
    date_hierarchy = 'created_at'


@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'task', 'user', 'file_size', 'created_at']
    list_filter = ['created_at']
    search_fields = ['file_name']
    date_hierarchy = 'created_at'

