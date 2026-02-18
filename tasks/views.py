from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from .models import Task, TaskComment, TaskAttachment
from .serializers import (
    TaskSerializer, TaskDetailSerializer,
    TaskCommentSerializer, TaskAttachmentSerializer
)


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'priority', 'is_template', 'parent_task']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'due_date', 'priority']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        queryset = Task.objects.filter(
            Q(user=user) | Q(assigned_to=user)
        ).distinct()
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(due_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(due_date__lte=end_date)
        
        # Filter by tags
        tags = self.request.query_params.getlist('tags')
        if tags:
            queryset = queryset.filter(tags__overlap=tags)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TaskDetailSerializer
        return TaskSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        task = self.get_object()
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.save()
        serializer = self.get_serializer(task)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        task = self.get_object()
        task.status = 'todo'
        task.completed_at = None
        task.save()
        serializer = self.get_serializer(task)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue tasks"""
        queryset = self.get_queryset().filter(
            due_date__lt=timezone.now(),
            status__in=['todo', 'in_progress']
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming tasks"""
        queryset = self.get_queryset().filter(
            due_date__gte=timezone.now(),
            status__in=['todo', 'in_progress']
        ).order_by('due_date')[:10]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class TaskCommentViewSet(viewsets.ModelViewSet):
    serializer_class = TaskCommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ['created_at']
    ordering = ['created_at']
    
    def get_queryset(self):
        task_id = self.request.query_params.get('task_id')
        if task_id:
            return TaskComment.objects.filter(task_id=task_id)
        return TaskComment.objects.filter(
            task__user=self.request.user
        ) | TaskComment.objects.filter(
            task__assigned_to=self.request.user
        )
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TaskAttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = TaskAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        task_id = self.request.query_params.get('task_id')
        if task_id:
            return TaskAttachment.objects.filter(task_id=task_id)
        return TaskAttachment.objects.filter(
            task__user=self.request.user
        ) | TaskAttachment.objects.filter(
            task__assigned_to=self.request.user
        )
    
    def perform_create(self, serializer):
        file = serializer.validated_data['file']
        serializer.save(
            user=self.request.user,
            file_name=file.name,
            file_size=file.size,
            mime_type=file.content_type
        )

