from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from accounts.permissions import (
    IsSchedulerAdmin, IsSchedulerManager, IsEmployeeOrManager, IsOwnerOrManager
)
from .models import (
    Organization, Company, Department, ScheduleTeam, Employee,
    Shift, ShiftReplacementRequest, EmployeeAvailability,
    TimeClock, ScheduleTemplate, AppSettings
)
from .serializers import (
    OrganizationSerializer, CompanySerializer, DepartmentSerializer,
    ScheduleTeamSerializer, EmployeeSerializer, ShiftSerializer,
    ShiftReplacementRequestSerializer, EmployeeAvailabilitySerializer,
    TimeClockSerializer, ScheduleTemplateSerializer, AppSettingsSerializer
)


class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated, IsSchedulerAdmin]
    filterset_fields = ['organization_manager', 'operations_manager']
    search_fields = ['name', 'email', 'phone']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['organization', 'type', 'field_type', 'company_manager', 'operations_manager']
    search_fields = ['name', 'email', 'phone']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['company']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class ScheduleTeamViewSet(viewsets.ModelViewSet):
    queryset = ScheduleTeam.objects.all()
    serializer_class = ScheduleTeamSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['company']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated, IsEmployeeOrManager]
    filterset_fields = ['company', 'department', 'team', 'status']
    search_fields = ['first_name', 'last_name', 'email', 'phone', 'position']
    ordering_fields = ['last_name', 'first_name', 'hire_date', 'created_at']
    ordering = ['last_name', 'first_name']


class ShiftViewSet(viewsets.ModelViewSet):
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['employee', 'company', 'department', 'team', 'status']
    search_fields = ['notes']
    ordering_fields = ['start_time', 'end_time', 'created_at']
    ordering = ['start_time']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(start_time__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_time__lte=end_date)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_missed(self, request, pk=None):
        shift = self.get_object()
        shift.is_missed = True
        shift.missed_at = timezone.now()
        shift.status = 'missed'
        shift.save()
        serializer = self.get_serializer(shift)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve_replacement(self, request, pk=None):
        shift = self.get_object()
        shift.replacement_approved_at = timezone.now()
        shift.status = 'confirmed'
        shift.save()
        serializer = self.get_serializer(shift)
        return Response(serializer.data)


class ShiftReplacementRequestViewSet(viewsets.ModelViewSet):
    queryset = ShiftReplacementRequest.objects.all()
    serializer_class = ShiftReplacementRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['shift', 'original_employee', 'replacement_employee', 'company', 'status']
    ordering_fields = ['requested_at', 'reviewed_at']
    ordering = ['-requested_at']
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        replacement_request = self.get_object()
        replacement_request.status = 'approved'
        replacement_request.reviewed_at = timezone.now()
        replacement_request.reviewed_by = request.user
        replacement_request.save()
        
        # Update the shift
        shift = replacement_request.shift
        shift.replacement_employee = replacement_request.replacement_employee
        shift.replacement_approved_at = timezone.now()
        shift.save()
        
        serializer = self.get_serializer(replacement_request)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        replacement_request = self.get_object()
        replacement_request.status = 'rejected'
        replacement_request.reviewed_at = timezone.now()
        replacement_request.reviewed_by = request.user
        replacement_request.reviewer_notes = request.data.get('notes', '')
        replacement_request.save()
        
        serializer = self.get_serializer(replacement_request)
        return Response(serializer.data)


class EmployeeAvailabilityViewSet(viewsets.ModelViewSet):
    queryset = EmployeeAvailability.objects.all()
    serializer_class = EmployeeAvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['employee', 'company', 'status']
    ordering_fields = ['date', 'created_at']
    ordering = ['date']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        return queryset


class TimeClockViewSet(viewsets.ModelViewSet):
    queryset = TimeClock.objects.all()
    serializer_class = TimeClockSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['employee', 'shift']
    ordering_fields = ['clock_in', 'clock_out', 'created_at']
    ordering = ['-clock_in']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(clock_in__gte=start_date)
        if end_date:
            queryset = queryset.filter(clock_out__lte=end_date)
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def clock_in(self, request):
        employee_id = request.data.get('employee_id')
        shift_id = request.data.get('shift_id')
        
        employee = get_object_or_404(Employee, id=employee_id)
        shift = get_object_or_404(Shift, id=shift_id) if shift_id else None
        
        # Check if there's an open clock entry
        open_entry = TimeClock.objects.filter(
            employee=employee,
            clock_in__isnull=False,
            clock_out__isnull=True
        ).first()
        
        if open_entry:
            return Response(
                {'error': 'Employee already clocked in. Please clock out first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        time_clock = TimeClock.objects.create(
            employee=employee,
            shift=shift,
            clock_in=timezone.now()
        )
        
        serializer = self.get_serializer(time_clock)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def clock_out(self, request):
        employee_id = request.data.get('employee_id')
        time_clock_id = request.data.get('time_clock_id')
        
        if time_clock_id:
            time_clock = get_object_or_404(TimeClock, id=time_clock_id)
        else:
            employee = get_object_or_404(Employee, id=employee_id)
            time_clock = TimeClock.objects.filter(
                employee=employee,
                clock_in__isnull=False,
                clock_out__isnull=True
            ).first()
            
            if not time_clock:
                return Response(
                    {'error': 'No open clock entry found.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        time_clock.clock_out = timezone.now()
        
        # Calculate total hours
        if time_clock.clock_in and time_clock.clock_out:
            delta = time_clock.clock_out - time_clock.clock_in
            total_seconds = delta.total_seconds()
            break_seconds = 0
            
            if time_clock.break_start and time_clock.break_end:
                break_delta = time_clock.break_end - time_clock.break_start
                break_seconds = break_delta.total_seconds()
            
            total_hours = (total_seconds - break_seconds) / 3600
            time_clock.total_hours = round(total_hours, 2)
        
        time_clock.save()
        
        serializer = self.get_serializer(time_clock)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def start_break(self, request, pk=None):
        time_clock = self.get_object()
        if time_clock.break_start:
            return Response(
                {'error': 'Break already started.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        time_clock.break_start = timezone.now()
        time_clock.save()
        serializer = self.get_serializer(time_clock)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def end_break(self, request, pk=None):
        time_clock = self.get_object()
        if not time_clock.break_start:
            return Response(
                {'error': 'No break started.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        time_clock.break_end = timezone.now()
        time_clock.save()
        serializer = self.get_serializer(time_clock)
        return Response(serializer.data)


class ScheduleTemplateViewSet(viewsets.ModelViewSet):
    queryset = ScheduleTemplate.objects.all()
    serializer_class = ScheduleTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['company', 'team']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class AppSettingsViewSet(viewsets.ModelViewSet):
    queryset = AppSettings.objects.all()
    serializer_class = AppSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['user']
    
    def get_queryset(self):
        # Users can only see their own settings
        if self.request.user.is_staff:
            return super().get_queryset()
        return AppSettings.objects.filter(user=self.request.user)

