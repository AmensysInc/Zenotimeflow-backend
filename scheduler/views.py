from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from zeno_time.cache_mixins import CacheListResponseMixin
from accounts.permissions import (
    IsSchedulerAdmin, IsSchedulerManager, IsEmployeeOrManager, IsEmployeeOrManagerOrReadOnly,
    IsOwnerOrManager, IsCompanyManagerOrAbove,
    get_organization_queryset_for_user,
    get_company_queryset_for_user,
    get_employee_queryset_for_user,
    get_shift_queryset_for_user,
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
    """Organizations. RBAC: Super Admin sees all and can create; Organization Manager sees only assigned orgs.
    List cache disabled so create/delete/update are visible immediately."""
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['organization_manager', 'operations_manager']
    search_fields = ['name', 'email', 'phone']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        return get_organization_queryset_for_user(self.request.user).select_related(
            'organization_manager', 'operations_manager', 'created_by'
        )
    
    def get_permissions(self):
        """Super Admin can create/edit; others need IsSchedulerAdmin."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            if self.request.user.is_super_admin():
                return [permissions.IsAuthenticated()]
            return [permissions.IsAuthenticated(), IsSchedulerAdmin()]
        return [permissions.IsAuthenticated()]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class CompanyViewSet(viewsets.ModelViewSet):
    """
    Companies (TASK 4).
    - Super Admin: sees all companies
    - Organization Manager: sees companies in their orgs
    - Company Manager: sees ONLY their assigned company (strict restriction)
    """
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['organization', 'type', 'field_type', 'company_manager', 'operations_manager']
    search_fields = ['name', 'email', 'phone']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        """TASK 4: Company Manager sees ONLY their assigned company."""
        from accounts.rbac import get_manager_company
        
        # Company Manager: restrict to their single assigned company
        manager_company = get_manager_company(self.request.user)
        if manager_company:
            return Company.objects.filter(id=manager_company.id).select_related(
                'company_manager', 'organization'
            ).prefetch_related('employees')
        
        # Super Admin / Org Manager: use standard RBAC filtering
        return get_company_queryset_for_user(self.request.user).select_related(
            'company_manager', 'organization'
        ).prefetch_related('employees')
    
    def get_permissions(self):
        """Super Admin can create/edit; others need appropriate permissions (IsAuthenticated allows read, create needs org/company manager)."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            if self.request.user.is_super_admin():
                return [permissions.IsAuthenticated()]
            # Allow Organization Manager or Company Manager to create companies
            from accounts.permissions import IsOrganizationManagerOrAbove, IsCompanyManagerOrAbove
            return [permissions.IsAuthenticated(), IsOrganizationManagerOrAbove()]
        return [permissions.IsAuthenticated()]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class DepartmentViewSet(CacheListResponseMixin, viewsets.ModelViewSet):
    """Departments. RBAC: filtered by companies the user can access."""
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['company']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        company_ids = self.request.user.get_managed_company_ids() if not self.request.user.is_super_admin() else None
        qs = Department.objects.all()
        if company_ids is not None:
            qs = qs.filter(company_id__in=company_ids)
        return qs


class ScheduleTeamViewSet(viewsets.ModelViewSet):
    """Schedule teams. RBAC: filtered by companies the user can access."""
    serializer_class = ScheduleTeamSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['company']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        company_ids = self.request.user.get_managed_company_ids() if not self.request.user.is_super_admin() else None
        qs = ScheduleTeam.objects.all()
        if company_ids is not None:
            qs = qs.filter(company_id__in=company_ids)
        return qs
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class EmployeeViewSet(CacheListResponseMixin, viewsets.ModelViewSet):
    """
    Employees are stored in the scheduler Employee table (employees), not in user_roles.
    List/retrieve from employees table only; RBAC filters by managed companies / self.
    """
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated, IsEmployeeOrManagerOrReadOnly]
    pagination_class = None  # Return plain array so frontend can display list
    filterset_fields = ['company', 'department', 'team', 'status', 'user', 'email']
    search_fields = ['first_name', 'last_name', 'email', 'phone', 'position']
    ordering_fields = ['last_name', 'first_name', 'hire_date', 'created_at']
    ordering = ['last_name', 'first_name']

    def get_queryset(self):
        # Source of truth: employees table only; RBAC filters who can see what
        return get_employee_queryset_for_user(self.request.user).select_related(
            'user', 'company', 'company__organization', 'department', 'team'
        ).prefetch_related('user__roles')

    def perform_create(self, serializer):
        """
        Store employee in employees table and set UserRole to employee (TASK 3).
        Company Manager: auto-assign their company (ignore incoming company_id).
        """
        from accounts.models import UserRole
        from accounts.rbac import get_manager_company
        
        # TASK 3: Company Manager can only create employees for their assigned company
        manager_company = get_manager_company(self.request.user)
        if manager_company:
            # Override company: manager can only assign their own company
            serializer.validated_data['company'] = manager_company
            serializer.validated_data.pop('company_id', None)  # Remove if present
        
        employee = serializer.save()
        
        # One user = one role: employee gets a single UserRole with app_type=calendar (no duplicate rows)
        if employee.user_id:
            UserRole.objects.filter(user=employee.user).exclude(role='super_admin').delete()
            UserRole.objects.get_or_create(
                user=employee.user, role='employee', app_type='calendar', defaults={}
            )

    def list(self, request, *args, **kwargs):
        """Return plain array of employees from employees table (no pagination wrapper)."""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ShiftViewSet(viewsets.ModelViewSet):
    """
    Shifts. RBAC: Company Manager sees/manages shifts in their companies; Employee sees only assigned shifts.
    Permissions:
    - Super Admin: Full access
    - Organization Manager: Can create/manage shifts in companies within their orgs
    - Company Manager: Can create/manage shifts in assigned companies
    - Employee: Can view own shifts only, can request replacements
    """
    serializer_class = ShiftSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['employee', 'company', 'department', 'team', 'status']
    search_fields = ['notes']
    ordering_fields = ['start_time', 'end_time', 'created_at']
    ordering = ['start_time']
    
    def get_queryset(self):
        """Return shifts visible to user with optimized queries."""
        queryset = get_shift_queryset_for_user(self.request.user).select_related(
            'employee', 'employee__user', 'company', 'department', 'team', 'created_by'
        ).prefetch_related('employee__company')
        
        # Filter by date range if provided
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(start_time__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_time__lte=end_date)
        
        # Additional filters
        employee_id = self.request.query_params.get('employee')
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        company_id = self.request.query_params.get('company')
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        
        return queryset
    
    def get_permissions(self):
        """Enforce RBAC: Company Manager can create; Employee can only view own shifts."""
        from accounts.rbac import can_create_shift, can_modify_shift
        
        if self.action == 'create':
            # Check if user can create shifts (Company Manager or above)
            if self.request.user.is_super_admin():
                return [permissions.IsAuthenticated()]
            # Check company_id from request data
            company_id = self.request.data.get('company')
            if company_id and can_create_shift(self.request.user, company_id):
                return [permissions.IsAuthenticated()]
            return [permissions.IsAuthenticated(), IsCompanyManagerOrAbove()]
        
        if self.action in ['update', 'partial_update', 'destroy']:
            # Check if user can modify this shift
            if self.request.user.is_super_admin():
                return [permissions.IsAuthenticated()]
            return [permissions.IsAuthenticated(), IsCompanyManagerOrAbove()]
        
        return [permissions.IsAuthenticated()]
    
    def perform_create(self, serializer):
        """
        Create shift with RBAC validation (TASK 5).
        Company Manager: can only schedule shifts for employees of their assigned company.
        Validates: employee.company == manager.company
        """
        from accounts.rbac import can_create_shift, get_manager_company
        from rest_framework.exceptions import PermissionDenied, ValidationError
        
        employee = serializer.validated_data.get('employee')
        company = serializer.validated_data.get('company')
        
        # TASK 5: Company Manager restriction - employee must belong to manager's company
        manager_company = get_manager_company(self.request.user)
        if manager_company:
            if not employee:
                raise ValidationError({'employee': 'Employee is required for shift creation.'})
            if employee.company_id != manager_company.id:
                raise PermissionDenied(
                    f'You can only schedule shifts for employees of your assigned company ({manager_company.name}).'
                )
            # Auto-assign manager's company
            serializer.validated_data['company'] = manager_company
        else:
            # Super Admin / Org Manager: validate company access
            if company:
                company_id_str = str(company.id) if hasattr(company, 'id') else str(company)
                if not can_create_shift(self.request.user, company_id_str):
                    raise PermissionDenied('You do not have permission to create shifts for this company.')
        
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        """
        Update shift with RBAC validation (TASK 5).
        Company Manager: can only update shifts for employees of their assigned company.
        """
        from accounts.rbac import can_modify_shift, get_manager_company
        from rest_framework.exceptions import PermissionDenied
        
        shift = self.get_object()
        manager_company = get_manager_company(self.request.user)
        
        # TASK 5: Company Manager can only update shifts for their company's employees
        if manager_company:
            if shift.employee_id and shift.employee.company_id != manager_company.id:
                raise PermissionDenied(
                    'You can only modify shifts for employees of your assigned company.'
                )
            # Prevent changing employee to one outside manager's company
            employee = serializer.validated_data.get('employee', shift.employee)
            if employee and employee.company_id != manager_company.id:
                raise PermissionDenied(
                    'You can only assign shifts to employees of your assigned company.'
                )
        else:
            # Super Admin / Org Manager: use standard RBAC check
            shift_id = str(shift.id)
            if not can_modify_shift(self.request.user, shift_id):
                raise PermissionDenied('You do not have permission to modify this shift.')
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """
        Delete shift with RBAC validation (TASK 5).
        Company Manager: can only delete shifts for employees of their assigned company.
        """
        from accounts.rbac import can_modify_shift, get_manager_company
        from rest_framework.exceptions import PermissionDenied
        
        manager_company = get_manager_company(self.request.user)
        
        # TASK 5: Company Manager can only delete shifts for their company's employees
        if manager_company:
            if instance.employee_id and instance.employee.company_id != manager_company.id:
                raise PermissionDenied(
                    'You can only delete shifts for employees of your assigned company.'
                )
        else:
            # Super Admin / Org Manager: use standard RBAC check
            shift_id = str(instance.id)
            if not can_modify_shift(self.request.user, shift_id):
                raise PermissionDenied('You do not have permission to delete this shift.')
        
        instance.delete()
    
    @action(detail=False, methods=['get'])
    def missed(self, request):
        """
        Get missed shifts (TASK 6).
        Definition: shift_date < today AND (status is missed/scheduled/confirmed) AND
        (is_missed=True OR no TimeClock with clock_in for this shift).
        Company Manager: sees only missed shifts of employees in their assigned company.
        """
        from accounts.rbac import get_manager_company
        from rest_framework.response import Response

        today = timezone.now().date()
        manager_company = get_manager_company(request.user)

        # Base: shifts that started before today; include scheduled, confirmed, and already-marked missed
        queryset = Shift.objects.filter(
            start_time__date__lt=today,
            status__in=['scheduled', 'confirmed', 'missed']
        ).select_related('employee', 'employee__user', 'company', 'department', 'team')

        # TASK 6: Company Manager sees only their company's missed shifts
        if manager_company:
            queryset = queryset.filter(company_id=manager_company.id)
        elif not request.user.is_super_admin():
            company_ids = request.user.get_managed_company_ids()
            emp_ids = request.user.get_accessible_employee_ids()
            queryset = queryset.filter(
                Q(company_id__in=company_ids) | Q(employee_id__in=emp_ids)
            ).distinct()

        shifts = list(queryset)
        shift_ids = [s.id for s in shifts]
        # One query: shift IDs that have at least one clock-in (avoid N+1)
        shift_ids_with_clock_in = set(
            TimeClock.objects.filter(
                shift_id__in=shift_ids,
                clock_in__isnull=False
            ).values_list('shift_id', flat=True).distinct()
        )
        # Missed = explicitly marked OR no clock-in
        missed_shifts = [
            s for s in shifts
            if s.is_missed or s.id not in shift_ids_with_clock_in
        ]

        serializer = self.get_serializer(missed_shifts, many=True)
        return Response(serializer.data)
    
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
    """Shift replacement requests. RBAC: filtered by company/employee scope."""
    serializer_class = ShiftReplacementRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['shift', 'original_employee', 'replacement_employee', 'company', 'status']
    ordering_fields = ['requested_at', 'reviewed_at']
    ordering = ['-requested_at']
    
    def get_queryset(self):
        qs = ShiftReplacementRequest.objects.all()
        if self.request.user.is_super_admin():
            return qs
        company_ids = self.request.user.get_managed_company_ids()
        emp_ids = self.request.user.get_accessible_employee_ids()
        qs = qs.filter(
            Q(company_id__in=company_ids) |
            Q(original_employee_id__in=emp_ids) |
            Q(replacement_employee_id__in=emp_ids)
        ).distinct()
        return qs
    
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
    """Employee availability. RBAC: filtered by company/employee scope."""
    serializer_class = EmployeeAvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['employee', 'company', 'status']
    ordering_fields = ['date', 'created_at']
    ordering = ['date']
    
    def get_queryset(self):
        qs = EmployeeAvailability.objects.all()
        if not self.request.user.is_super_admin():
            emp_ids = self.request.user.get_accessible_employee_ids()
            qs = qs.filter(employee_id__in=emp_ids)
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)
        return qs


class TimeClockViewSet(viewsets.ModelViewSet):
    """Time clock entries. RBAC: Company Manager sees their company's entries; Employee sees own only."""
    serializer_class = TimeClockSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None  # Return plain list for mobile and web
    filterset_fields = ['employee', 'shift']
    ordering_fields = ['clock_in', 'clock_out', 'created_at']
    ordering = ['-clock_in']
    
    def get_queryset(self):
        qs = TimeClock.objects.select_related(
            'employee', 'employee__user', 'employee__company', 'shift', 'shift__company'
        )
        if not self.request.user.is_super_admin():
            emp_ids = self.request.user.get_accessible_employee_ids()
            qs = qs.filter(employee_id__in=emp_ids)
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            qs = qs.filter(clock_in__gte=start_date)
        if end_date:
            qs = qs.filter(clock_out__lte=end_date)
        return qs
    
    def _ensure_employee_access(self, request, employee_id):
        """Ensure non-super_admin can only act on their own employee record."""
        if getattr(request.user, 'is_super_admin', lambda: False)():
            return
        allowed = request.user.get_accessible_employee_ids()
        # Compare as strings (allowed may be UUIDs, employee_id from JSON is string)
        allowed_str = {str(eid) for eid in (allowed or set())}
        if employee_id and str(employee_id) not in allowed_str:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('You can only clock in/out for your own employee record.')

    @action(detail=False, methods=['post'])
    def clock_in(self, request):
        employee_id = request.data.get('employee_id')
        shift_id = request.data.get('shift_id')
        if not employee_id:
            return Response(
                {'error': 'employee_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        self._ensure_employee_access(request, employee_id)
        employee = get_object_or_404(Employee, id=employee_id)
        shift = get_object_or_404(Shift, id=shift_id) if (shift_id and str(shift_id).strip()) else None
        
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
        if employee_id:
            self._ensure_employee_access(request, employee_id)
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
    
    def perform_update(self, serializer):
        """Allow super_admin to edit clock_in/clock_out; recalc total_hours and overtime_hours."""
        from rest_framework.exceptions import PermissionDenied
        data = serializer.validated_data
        if 'clock_in' in data or 'clock_out' in data:
            if not self.request.user.is_super_admin():
                raise PermissionDenied('Only super admin can edit clock in/out times.')
        instance = serializer.save()
        if 'clock_in' in data or 'clock_out' in data:
            if instance.clock_in and instance.clock_out:
                delta = instance.clock_out - instance.clock_in
                total_seconds = delta.total_seconds()
                break_seconds = 0
                if instance.break_start and instance.break_end:
                    break_seconds = (instance.break_end - instance.break_start).total_seconds()
                total_hours = round((total_seconds - break_seconds) / 3600, 2)
                instance.total_hours = total_hours
                instance.overtime_hours = round(max(0, total_hours - 8), 2)
                instance.save(update_fields=['total_hours', 'overtime_hours'])

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


class ScheduleTemplateViewSet(CacheListResponseMixin, viewsets.ModelViewSet):
    """Schedule templates. RBAC: filtered by companies the user can access."""
    serializer_class = ScheduleTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['company', 'team']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        company_ids = self.request.user.get_managed_company_ids() if not self.request.user.is_super_admin() else None
        qs = ScheduleTemplate.objects.all()
        if company_ids is not None:
            qs = qs.filter(company_id__in=company_ids)
        return qs
    
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

