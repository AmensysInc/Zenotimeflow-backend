from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


class User(AbstractUser):
    """Custom User model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'auth_user'
    
    def __str__(self):
        return self.email


class Profile(models.Model):
    """User profile with additional information"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    email = models.EmailField()
    full_name = models.CharField(max_length=255, null=True, blank=True)
    avatar_url = models.URLField(null=True, blank=True)
    mobile_number = models.CharField(max_length=20, null=True, blank=True)
    status = models.CharField(max_length=50, default='active')
    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinates'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'profiles'
    
    def __str__(self):
        return f"{self.full_name or self.email} - {self.user.email}"


class UserRole(models.Model):
    """User roles and app type associations"""
    ROLE_CHOICES = [
        ('user', 'User'),
        ('admin', 'Admin'),
        ('super_admin', 'Super Admin'),
        ('operations_manager', 'Operations Manager'),
        ('manager', 'Manager'),
        ('candidate', 'Candidate'),
        ('employee', 'Employee'),
        ('house_keeping', 'House Keeping'),
        ('maintenance', 'Maintenance'),
    ]
    
    APP_TYPE_CHOICES = [
        ('calendar', 'Calendar'),
        ('scheduler', 'Scheduler'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='roles')
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='user')
    app_type = models.CharField(max_length=50, choices=APP_TYPE_CHOICES, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_roles'
        unique_together = [['user', 'role', 'app_type']]
    
    def __str__(self):
        return f"{self.user.email} - {self.role} ({self.app_type or 'all'})"

