from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from accounts.permissions import IsOwnerOrManager
from .models import CalendarEvent
from .serializers import CalendarEventSerializer


class CalendarEventViewSet(viewsets.ModelViewSet):
    serializer_class = CalendarEventSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrManager]
    filterset_fields = ['event_type', 'priority', 'all_day', 'is_recurring']
    search_fields = ['title', 'description', 'location']
    ordering_fields = ['start_time', 'end_time', 'created_at', 'priority']
    ordering = ['start_time']
    
    def get_queryset(self):
        user = self.request.user
        queryset = CalendarEvent.objects.filter(
            Q(user=user) | Q(attendees=user)
        ).distinct()
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(end_time__gte=start_date)
        if end_date:
            queryset = queryset.filter(start_time__lte=end_date)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming events"""
        queryset = self.get_queryset().filter(
            start_time__gte=timezone.now()
        ).order_by('start_time')[:10]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's events"""
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        queryset = self.get_queryset().filter(
            start_time__gte=today_start,
            end_time__lte=today_end
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

