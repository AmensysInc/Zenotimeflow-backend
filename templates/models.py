from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class LearningTemplate(models.Model):
    """Check list / learning template - as shown in Check Lists UI"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    technology = models.CharField(max_length=100, null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_templates'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'learning_templates'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_by']),
        ]

    def __str__(self):
        return self.name


class TemplateAssignment(models.Model):
    """Assignment of a template/checklist to a user"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        LearningTemplate,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='template_assignments'
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='template_assignments_made'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'template_assignments'
        unique_together = [['template', 'user']]
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['template']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.template.name} -> {self.user.email}"
