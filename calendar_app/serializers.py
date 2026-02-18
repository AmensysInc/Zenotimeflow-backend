from rest_framework import serializers
from .models import CalendarEvent
from accounts.serializers import UserSerializer


class CalendarEventSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    attendees_details = UserSerializer(source='attendees', many=True, read_only=True)
    attendee_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=CalendarEvent._meta.get_field('attendees').related_model.objects.all(),
        source='attendees',
        write_only=True,
        required=False
    )
    parent_task_id = serializers.UUIDField(source='parent_task.id', read_only=True)
    
    class Meta:
        model = CalendarEvent
        fields = [
            'id', 'user', 'user_email', 'title', 'description', 'notes', 'start_time', 'end_time',
            'all_day', 'location', 'event_type', 'priority', 'color', 'is_recurring',
            'recurrence_pattern', 'reminder_minutes', 'parent_task', 'parent_task_id',
            'template_id', 'files', 'attendees', 'attendees_details',
            'attendee_ids', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        attendees = validated_data.pop('attendees', [])
        event = CalendarEvent.objects.create(**validated_data)
        if attendees:
            event.attendees.set(attendees)
        return event
    
    def update(self, instance, validated_data):
        attendees = validated_data.pop('attendees', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if attendees is not None:
            instance.attendees.set(attendees)
        return instance

