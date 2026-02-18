from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q, Sum, Avg
from .models import FocusSession, FocusBlock
from .serializers import FocusSessionSerializer, FocusBlockSerializer


class FocusSessionViewSet(viewsets.ModelViewSet):
    serializer_class = FocusSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'category']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'start_time', 'planned_duration']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = FocusSession.objects.filter(user=self.request.user)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(start_time__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_time__lte=end_date)
        
        # Filter by tags
        tags = self.request.query_params.getlist('tags')
        if tags:
            queryset = queryset.filter(tags__overlap=tags)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a focus session"""
        session = self.get_object()
        if session.status != 'planned':
            return Response(
                {'error': 'Session can only be started if it is planned'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session.status = 'in_progress'
        session.start_time = timezone.now()
        session.save()
        
        serializer = self.get_serializer(session)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete a focus session"""
        session = self.get_object()
        if session.status != 'in_progress':
            return Response(
                {'error': 'Session can only be completed if it is in progress'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session.status = 'completed'
        session.end_time = timezone.now()
        
        # Calculate actual duration
        if session.start_time and session.end_time:
            delta = session.end_time - session.start_time
            session.actual_duration = int(delta.total_seconds() / 60)
        
        session.save()
        
        serializer = self.get_serializer(session)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause a focus session"""
        session = self.get_object()
        if session.status != 'in_progress':
            return Response(
                {'error': 'Session can only be paused if it is in progress'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session.status = 'paused'
        session.save()
        
        serializer = self.get_serializer(session)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Resume a paused focus session"""
        session = self.get_object()
        if session.status != 'paused':
            return Response(
                {'error': 'Session can only be resumed if it is paused'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session.status = 'in_progress'
        session.save()
        
        serializer = self.get_serializer(session)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get focus session statistics"""
        queryset = self.get_queryset().filter(status='completed')
        
        total_sessions = queryset.count()
        total_minutes = queryset.aggregate(
            total=Sum('actual_duration')
        )['total'] or 0
        avg_duration = queryset.aggregate(
            avg=Avg('actual_duration')
        )['avg'] or 0
        total_distractions = queryset.aggregate(
            total=Sum('distractions')
        )['total'] or 0
        
        return Response({
            'total_sessions': total_sessions,
            'total_minutes': total_minutes,
            'total_hours': round(total_minutes / 60, 2),
            'average_duration_minutes': round(avg_duration, 2),
            'total_distractions': total_distractions,
            'average_distractions_per_session': round(total_distractions / total_sessions, 2) if total_sessions > 0 else 0
        })


class FocusBlockViewSet(viewsets.ModelViewSet):
    serializer_class = FocusBlockSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['is_recurring']
    search_fields = ['title']
    ordering_fields = ['start_time', 'end_time', 'created_at']
    ordering = ['start_time']
    
    def get_queryset(self):
        queryset = FocusBlock.objects.filter(user=self.request.user)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(start_time__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_time__lte=end_date)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

