from rest_framework import serializers
from .models import Habit, HabitCompletion


class HabitCompletionSerializer(serializers.ModelSerializer):
    habit_name = serializers.CharField(source='habit.name', read_only=True)
    
    class Meta:
        model = HabitCompletion
        fields = [
            'id', 'habit', 'habit_name', 'completion_date',
            'completion_time', 'notes', 'count'
        ]
        read_only_fields = ['id', 'completion_time']


class HabitSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    completions_count = serializers.IntegerField(source='completions.count', read_only=True)
    recent_completions = HabitCompletionSerializer(source='completions', many=True, read_only=True)
    
    class Meta:
        model = Habit
        fields = [
            'id', 'user', 'user_email', 'name', 'description', 'frequency',
            'target_count', 'color', 'icon', 'is_active', 'start_date',
            'end_date', 'reminder_time', 'streak_count', 'longest_streak',
            'total_completions', 'completions_count', 'recent_completions',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'streak_count', 'longest_streak', 'total_completions',
            'created_at', 'updated_at'
        ]


class HabitDetailSerializer(HabitSerializer):
    """Extended serializer with all completions"""
    completions = HabitCompletionSerializer(many=True, read_only=True)

