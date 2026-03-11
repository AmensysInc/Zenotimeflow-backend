import logging
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .serializers import (
    UserSerializer, UserCreateSerializer, RegisterSerializer, LoginSerializer,
    EmployeeLoginSerializer, ProfileSerializer, UserRoleSerializer
)
from .models import Profile, UserRole
from .permissions import IsSuperAdminOrReadOnly

User = get_user_model()
logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register(request):
    """User registration"""
    serializer = RegisterSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        user_serializer = UserSerializer(user)
        return Response({
            'user': user_serializer.data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def employee_login(request):
    """Mobile/app login: email + employee PIN. Returns user + employee + JWT. For employees only."""
    serializer = EmployeeLoginSerializer(data=request.data, context={'request': request})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    user = serializer.validated_data['user']
    employee = serializer.validated_data['employee']
    refresh = RefreshToken.for_user(user)
    # Minimal employee payload (no PIN)
    employee_data = {
        'id': str(employee.id),
        'full_name': employee.full_name,
        'first_name': employee.first_name,
        'last_name': employee.last_name,
        'email': employee.email,
        'position': getattr(employee, 'position', None) or '',
        'company_id': str(employee.company_id) if employee.company_id else None,
        'company_name': employee.company.name if employee.company else None,
    }
    return Response({
        'user': UserSerializer(user).data,
        'employee': employee_data,
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login(request):
    """User login (all roles including Super Admin). Returns user + JWT access/refresh."""
    logger.info("POST /api/auth/login/ received")
    try:
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.exception("Login is_valid error: %s", e)
        return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    user = serializer.validated_data.get('user')
    if not user:
        return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        payload = serializer.data
        if not payload.get('access') and user:
            refresh = RefreshToken.for_user(user)
            payload = {
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        return Response(payload, status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception("Login: building full payload failed: %s", e)
        try:
            refresh = RefreshToken.for_user(user)
            from accounts.rbac import get_user_role
            return Response({
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'username': getattr(user, 'username', None),
                    'is_active': user.is_active,
                    'profile': None,
                    'roles': [],
                    'primary_role': get_user_role(user),
                    'assigned_organization_id': None,
                    'assigned_company_id': None,
                },
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }, status=status.HTTP_200_OK)
        except Exception as e2:
            logger.exception("Login: fallback payload also failed: %s", e2)
            return Response(
                {'detail': 'Login succeeded but building response failed. Check server logs.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_welcome_email(request):
    """Stub: frontend may call this after creating a user. Optionally implement email sending later."""
    return Response({'message': 'OK'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout(request):
    """User logout - blacklist refresh token"""
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({'message': 'Successfully logged out'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def me(request):
    """Get current user information"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def update_profile(request):
    """Update user profile"""
    profile = request.user.profile
    serializer = ProfileSerializer(profile, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserListView(generics.ListCreateAPIView):
    """List/Create users. Only Super Admin can POST; list filtered by RBAC (Super Admin sees all)."""
    permission_classes = [permissions.IsAuthenticated, IsSuperAdminOrReadOnly]
    filterset_fields = ['is_active']
    search_fields = ['email', 'username', 'profile__full_name']
    pagination_class = None  # Disable pagination - frontend expects plain array
    
    def get_serializer_class(self):
        """Use UserCreateSerializer for POST, UserSerializer for GET."""
        if self.request.method == 'POST':
            return UserCreateSerializer
        return UserSerializer
    
    def list(self, request, *args, **kwargs):
        """Override to return plain array instead of paginated response. distinct() avoids duplicate users from search/filter joins."""
        queryset = self.filter_queryset(self.get_queryset()).distinct()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def _user_queryset_optimized(self):
        """Base User queryset with select_related/prefetch_related to avoid N+1 in UserSerializer."""
        return User.objects.select_related('profile').prefetch_related(
            'roles', 'managed_organizations', 'managed_companies', 'employee_profile'
        )

    def get_queryset(self):
        user = self.request.user
        base = self._user_queryset_optimized()
        # Super Admin sees all users; others are filtered by RBAC scope
        if user.is_super_admin():
            return base.order_by('email')
        # RBAC filtering for non-super-admin users
        from scheduler.models import Organization, Company, Employee
        user_ids = {user.id}
        # Organization managers see users in their organizations
        for org in Organization.objects.filter(organization_manager=user):
            if org.created_by_id:
                user_ids.add(org.created_by_id)
            if org.organization_manager_id:
                user_ids.add(org.organization_manager_id)
            for c in org.companies.all():
                if c.company_manager_id:
                    user_ids.add(c.company_manager_id)
                for e in c.employees.filter(user__isnull=False):
                    if e.user_id:
                        user_ids.add(e.user_id)
        # Company managers see users in their companies
        for c in Company.objects.filter(company_manager=user):
            if c.company_manager_id:
                user_ids.add(c.company_manager_id)
            for e in c.employees.filter(user__isnull=False):
                if e.user_id:
                    user_ids.add(e.user_id)
        # Employees see only themselves (unless they're also managers)
        emp = Employee.objects.filter(user=user).first()
        if emp and not (user.is_organization_manager() or user.is_company_manager()):
            return base.filter(id=user.id).order_by('email')
        if user_ids:
            return base.filter(id__in=user_ids).order_by('email')
        return User.objects.none()
    
    def perform_create(self, serializer):
        """Create user. Super Admin can create any user; others create regular users."""
        user = serializer.save()
        # Profile and default role created via serializer.create()
        return user


class UserRoleViewSet(ModelViewSet):
    """List/create/retrieve/delete user roles. Super Admin can manage any role; others can only list/retrieve own roles."""
    serializer_class = UserRoleSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdminOrReadOnly]
    http_method_names = ['get', 'head', 'options', 'post', 'put', 'patch', 'delete']

    def get_queryset(self):
        if self.request.user.is_super_admin():
            return UserRole.objects.all().select_related('user')
        return UserRole.objects.filter(user=self.request.user)


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete user. RBAC: scope for read; only Super Admin can update/delete."""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdminOrReadOnly]

    def perform_update(self, serializer):
        user = serializer.save()
        # Sync User first_name, last_name, email to linked Employee so Employees and Schedule show correct names
        from scheduler.models import Employee
        emp = Employee.objects.filter(user=user).first()
        if emp is not None:
            Employee.objects.filter(pk=emp.pk).update(
                first_name=user.first_name or '',
                last_name=user.last_name or '',
                email=user.email,
            )

    def get_queryset(self):
        user = self.request.user
        base = User.objects.select_related('profile').prefetch_related(
            'roles', 'managed_organizations', 'managed_companies', 'employee_profile'
        )
        if user.is_super_admin():
            return base
        if user.is_employee_role() and not (user.is_organization_manager() or user.is_company_manager()):
            return base.filter(id=user.id)
        from scheduler.models import Organization, Company, Employee
        user_ids = {user.id}
        for org in Organization.objects.filter(organization_manager=user):
            if org.created_by_id:
                user_ids.add(org.created_by_id)
            for c in org.companies.all():
                if c.company_manager_id:
                    user_ids.add(c.company_manager_id)
                for e in c.employees.filter(user__isnull=False):
                    if e.user_id:
                        user_ids.add(e.user_id)
        for c in Company.objects.filter(company_manager=user):
            if c.company_manager_id:
                user_ids.add(c.company_manager_id)
            for e in c.employees.filter(user__isnull=False):
                if e.user_id:
                    user_ids.add(e.user_id)
        return base.filter(id__in=user_ids)


def _get_profile_queryset(request):
    """Profiles the request user may access (same scope as user list)."""
    user = request.user
    if user.is_super_admin():
        return Profile.objects.all().select_related('user')
    from scheduler.models import Organization, Company, Employee
    user_ids = {user.id}
    for org in Organization.objects.filter(organization_manager=user):
        if org.created_by_id:
            user_ids.add(org.created_by_id)
        for c in org.companies.all():
            if c.company_manager_id:
                user_ids.add(c.company_manager_id)
            for e in c.employees.filter(user__isnull=False):
                if e.user_id:
                    user_ids.add(e.user_id)
    for c in Company.objects.filter(company_manager=user):
        if c.company_manager_id:
            user_ids.add(c.company_manager_id)
        for e in c.employees.filter(user__isnull=False):
            if e.user_id:
                user_ids.add(e.user_id)
    return Profile.objects.filter(user_id__in=user_ids).select_related('user')


class ProfileDetailView(generics.RetrieveUpdateAPIView):
    """GET/PATCH profile by profile id or user id. RBAC: same scope as user list; only Super Admin can update."""
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdminOrReadOnly]
    lookup_url_kwarg = 'pk'
    lookup_field = 'id'

    def get_queryset(self):
        return _get_profile_queryset(self.request)

    def get_object(self):
        """Resolve by profile id or by user id (frontend may send user id)."""
        queryset = self.filter_queryset(self.get_queryset())
        pk = self.kwargs.get(self.lookup_url_kwarg)
        # Try as profile id first
        obj = queryset.filter(id=pk).first()
        if obj is not None:
            return obj
        # Else try as user id so /profiles/<user_uuid>/ works
        obj = queryset.filter(user_id=pk).first()
        if obj is not None:
            return obj
        from rest_framework.exceptions import NotFound
        raise NotFound()

