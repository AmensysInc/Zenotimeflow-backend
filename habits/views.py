from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from .models import Habit, HabitCompletion
from .serializers import HabitSerializer, HabitDetailSerializer, HabitCompletionSerializer


class HabitViewSet(viewsets.ModelViewSet):
    serializer_class = HabitSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['frequency', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'streak_count', 'name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Habit.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return HabitDetailSerializer
        return HabitSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active habits"""
        queryset = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark habit as completed for today"""
        habit = self.get_object()
        completion_date = request.data.get('completion_date', timezone.now().date())
        count = request.data.get('count', 1)
        notes = request.data.get('notes', '')
        
        completion, created = HabitCompletion.objects.get_or_create(
            habit=habit,
            completion_date=completion_date,
            defaults={'count': count, 'notes': notes}
        )
        
        if not created:
            completion.count = count
            completion.notes = notes
            completion.save()
        
        serializer = HabitCompletionSerializer(completion)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    @action(detail=True, methods=['delete'])
    def uncomplete(self, request, pk=None):
        """Remove completion for a specific date"""
        habit = self.get_object()
        completion_date = request.data.get('completion_date', timezone.now().date())
        
        try:
            completion = HabitCompletion.objects.get(
                habit=habit,
                completion_date=completion_date
            )
            completion.delete()
            return Response({'message': 'Completion removed'}, status=status.HTTP_200_OK)
        except HabitCompletion.DoesNotExist:
            return Response(
                {'error': 'Completion not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def streaks(self, request):
        """Get habits with current streaks"""
        queryset = self.get_queryset().filter(
            is_active=True,
            streak_count__gt=0
        ).order_by('-streak_count')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class HabitCompletionViewSet(viewsets.ModelViewSet):
    serializer_class = HabitCompletionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['habit', 'completion_date']
    ordering_fields = ['completion_date', 'completion_time']
    ordering = ['-completion_date']
    
    def get_queryset(self):
        return HabitCompletion.objects.filter(habit__user=self.request.user)
    
    def perform_create(self, serializer):
        habit = serializer.validated_data['habit']
        if habit.user != self.request.user:
            raise permissions.PermissionDenied("You don't have permission to complete this habit.")
        serializer.save()

