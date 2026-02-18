from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class CalendarEvent(models.Model):
    """Calendar event model"""
    EVENT_TYPE_CHOICES = [
        ('meeting', 'Meeting'),
        ('appointment', 'Appointment'),
        ('reminder', 'Reminder'),
        ('task', 'Task'),
        ('other', 'Other'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='calendar_events'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)  # Additional notes field
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    all_day = models.BooleanField(default=False)
    location = models.CharField(max_length=255, null=True, blank=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES, default='other')
    priority = models.CharField(max_length=50, choices=PRIORITY_CHOICES, default='medium')
    color = models.CharField(max_length=7, null=True, blank=True)
    is_recurring = models.BooleanField(default=False)
    recurrence_pattern = models.JSONField(null=True, blank=True)  # Store recurrence rules
    reminder_minutes = models.IntegerField(null=True, blank=True)  # Minutes before event
    parent_task = models.ForeignKey(
        'tasks.Task',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='calendar_events'
    )
    template_id = models.UUIDField(null=True, blank=True)  # Reference to event template
    files = models.JSONField(default=list, blank=True)  # List of file URLs or file references
    attendees = models.ManyToManyField(User, related_name='attending_events', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'calendar_events'
        ordering = ['start_time']
        indexes = [
            models.Index(fields=['user', 'start_time']),
            models.Index(fields=['start_time', 'end_time']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.start_time}"

