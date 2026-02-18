from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class FocusSession(models.Model):
    """Focus session model"""
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('paused', 'Paused'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='focus_sessions'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    planned_duration = models.IntegerField()  # Duration in minutes
    actual_duration = models.IntegerField(null=True, blank=True)  # Actual duration in minutes
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='planned')
    category = models.CharField(max_length=100, null=True, blank=True)
    tags = models.JSONField(default=list, blank=True)  # List of tag strings
    distractions = models.IntegerField(default=0)  # Number of distractions during session
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'focus_sessions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['start_time']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"


class FocusBlock(models.Model):
    """Focus block - time blocks for focus sessions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='focus_blocks'
    )
    title = models.CharField(max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_recurring = models.BooleanField(default=False)
    recurrence_pattern = models.JSONField(null=True, blank=True)  # Store recurrence rules
    color = models.CharField(max_length=7, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'focus_blocks'
        ordering = ['start_time']
        indexes = [
            models.Index(fields=['user', 'start_time']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.start_time}"

