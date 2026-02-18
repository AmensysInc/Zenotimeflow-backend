from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class Habit(models.Model):
    """Habit model"""
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('custom', 'Custom'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='habits'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    frequency = models.CharField(max_length=50, choices=FREQUENCY_CHOICES, default='daily')
    target_count = models.IntegerField(default=1)  # Target completions per period
    color = models.CharField(max_length=7, null=True, blank=True)
    icon = models.CharField(max_length=50, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    reminder_time = models.TimeField(null=True, blank=True)
    streak_count = models.IntegerField(default=0)  # Current streak
    longest_streak = models.IntegerField(default=0)  # Longest streak achieved
    total_completions = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'habits'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.user.email}"


class HabitCompletion(models.Model):
    """Habit completion record"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    habit = models.ForeignKey(
        Habit,
        on_delete=models.CASCADE,
        related_name='completions'
    )
    completion_date = models.DateField()
    completion_time = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(null=True, blank=True)
    count = models.IntegerField(default=1)  # For habits with target_count > 1
    
    class Meta:
        db_table = 'habit_completions'
        unique_together = [['habit', 'completion_date']]
        ordering = ['-completion_date']
        indexes = [
            models.Index(fields=['habit', 'completion_date']),
        ]
    
    def __str__(self):
        return f"{self.habit.name} - {self.completion_date}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update habit statistics
        self._update_habit_stats(self.habit)
    
    def delete(self, *args, **kwargs):
        habit = self.habit  # Store reference before deletion
        super().delete(*args, **kwargs)
        # Update habit statistics after deletion
        self._update_habit_stats(habit)
    
    def _update_habit_stats(self, habit):
        """Update habit streak and completion statistics"""
        completions = HabitCompletion.objects.filter(habit=habit).order_by('completion_date')
        
        # Calculate total completions
        habit.total_completions = completions.aggregate(
            total=models.Sum('count')
        )['total'] or 0
        
        # Calculate current streak
        from django.utils import timezone
        from datetime import timedelta
        
        current_streak = 0
        check_date = timezone.now().date()
        
        # Check backwards from today
        while True:
            completion = completions.filter(completion_date=check_date).first()
            if completion:
                current_streak += 1
                check_date -= timedelta(days=1)
            else:
                break
        
        habit.streak_count = current_streak
        
        # Calculate longest streak
        longest_streak = 0
        current_run = 0
        prev_date = None
        
        for completion in completions:
            if prev_date is None:
                current_run = 1
            elif (completion.completion_date - prev_date).days == 1:
                current_run += 1
            else:
                longest_streak = max(longest_streak, current_run)
                current_run = 1
            
            prev_date = completion.completion_date
            longest_streak = max(longest_streak, current_run)
        
        habit.longest_streak = longest_streak
        habit.save()

