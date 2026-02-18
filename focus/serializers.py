from rest_framework import serializers
from .models import FocusSession, FocusBlock


class FocusSessionSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = FocusSession
        fields = [
            'id', 'user', 'user_email', 'title', 'description', 'planned_duration',
            'actual_duration', 'start_time', 'end_time', 'status', 'category',
            'tags', 'distractions', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FocusBlockSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = FocusBlock
        fields = [
            'id', 'user', 'user_email', 'title', 'start_time', 'end_time',
            'is_recurring', 'recurrence_pattern', 'color', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

