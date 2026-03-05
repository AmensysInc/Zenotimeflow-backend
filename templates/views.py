from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from zeno_time.cache_mixins import CacheListResponseMixin
from .models import LearningTemplate, TemplateAssignment
from .serializers import LearningTemplateSerializer, LearningTemplateListSerializer, TemplateAssignmentSerializer


def is_template_admin(user):
    """Check if user can manage all templates (super_admin, operations_manager, manager)."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role_names = set(user.roles.values_list('role', flat=True))
    return bool(role_names & {'super_admin', 'operations_manager', 'manager'})


class LearningTemplateViewSet(CacheListResponseMixin, viewsets.ModelViewSet):
    serializer_class = LearningTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['created_by']
    search_fields = ['name', 'description', 'technology']
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return LearningTemplateListSerializer
        return LearningTemplateSerializer

    def get_queryset(self):
        if is_template_admin(self.request.user):
            return LearningTemplate.objects.all()
        return LearningTemplate.objects.filter(
            assignments__user=self.request.user
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class TemplateAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = TemplateAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['template', 'user']
    ordering = ['-assigned_at']

    def get_queryset(self):
        if is_template_admin(self.request.user):
            return TemplateAssignment.objects.all()
        return TemplateAssignment.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        if not is_template_admin(self.request.user):
            raise permissions.PermissionDenied('Only admins can create assignments.')
        serializer.save(assigned_by=self.request.user)
