from django.contrib import admin
from .models import CalendarEvent


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'start_time', 'end_time', 'event_type', 'priority', 'all_day']
    list_filter = ['event_type', 'priority', 'all_day', 'is_recurring', 'start_time']
    search_fields = ['title', 'description', 'location']
    filter_horizontal = ['attendees']
    date_hierarchy = 'start_time'

