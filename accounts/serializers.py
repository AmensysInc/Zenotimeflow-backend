from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Profile, UserRole


class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRole
        fields = ['id', 'user', 'role', 'app_type', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProfileSerializer(serializers.ModelSerializer):
    roles = UserRoleSerializer(source='user.roles', many=True, read_only=True)
    
    class Meta:
        model = Profile
        fields = [
            'id', 'email', 'full_name', 'avatar_url', 'mobile_number',
            'status', 'manager', 'created_at', 'updated_at', 'roles'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    # RBAC: assigned org/company for dashboard (Organization Manager, Company Manager, Employee)
    assigned_organization_id = serializers.SerializerMethodField()
    assigned_company_id = serializers.SerializerMethodField()
    # Primary role summary for quick access
    primary_role = serializers.SerializerMethodField()

    def get_profile(self, obj):
        """Safe for superusers and users without Profile (e.g. created before signal)."""
        try:
            return ProfileSerializer(obj.profile).data
        except (Profile.DoesNotExist, AttributeError, Exception):
            return None

    def get_roles(self, obj):
        """Safe when user has no UserRole entries."""
        try:
            return UserRoleSerializer(obj.roles.all(), many=True).data
        except Exception:
            return []

    def get_primary_role(self, obj):
        """Get primary role: 'super_admin', 'organization_manager', 'company_manager', 'employee', or 'user'."""
        from accounts.rbac import get_user_role
        return get_user_role(obj)

    def get_assigned_organization_id(self, obj):
        """Organization this user manages (Organization Manager role)."""
        try:
            org = obj.managed_organizations.first()
            return str(org.id) if org else None
        except Exception:
            return None

    def get_assigned_company_id(self, obj):
        """Company this user manages (Company Manager) or is employed by (Employee)."""
        try:
            company = obj.managed_companies.first()
            if company:
                return str(company.id)
            emp = getattr(obj, 'employee_profile', None)
            if emp is not None:
                first_emp = emp.filter(company__isnull=False).first() if hasattr(emp, 'filter') else None
                if first_emp and getattr(first_emp, 'company_id', None):
                    return str(first_emp.company_id)
            return None
        except Exception:
            return None

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'is_active', 'date_joined', 'profile', 'roles', 'primary_role',
            'assigned_organization_id', 'assigned_company_id'
        ]
        read_only_fields = ['id', 'date_joined']


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Super Admin serializer for creating users with role and org/company assignment.
    Password is hashed via User.objects.create_user(). Validates role + org/company mapping.
    """
    password = serializers.CharField(write_only=True, min_length=8, required=True)
    full_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    role = serializers.ChoiceField(
        choices=[
            ('user', 'User'),
            ('employee', 'Employee'),
            ('company_manager', 'Company Manager'),
            ('organization_manager', 'Organization Manager'),
        ],
        write_only=True,
        required=False,
        default='user'
    )
    organization_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    company_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    # Employee-only: stored in employees table when role=employee
    employee_pin = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=10)

    class Meta:
        model = User
        fields = [
            'email', 'username', 'password', 'first_name', 'last_name',
            'is_active', 'full_name', 'role', 'organization_id', 'company_id', 'employee_pin'
        ]
    
    def validate(self, attrs):
        role = attrs.get('role', 'user')
        organization_id = attrs.get('organization_id')
        company_id = attrs.get('company_id')
        email = (attrs.get('email') or '').strip().lower()

        # Create only once: reject duplicate email (case-insensitive)
        if email and User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({'email': 'A user with this email already exists.'})

        # Import here to avoid circular import
        from scheduler.models import Organization, Company

        if role == 'organization_manager':
            if not organization_id:
                raise serializers.ValidationError({
                    'organization_id': 'Required when role is Organization Manager.'
                })
            if not Organization.objects.filter(id=organization_id).exists():
                raise serializers.ValidationError({
                    'organization_id': 'Organization not found.'
                })
        
        if role == 'company_manager':
            if not company_id:
                raise serializers.ValidationError({
                    'company_id': 'Required when role is Company Manager.'
                })
            try:
                company = Company.objects.get(id=company_id)
            except Company.DoesNotExist:
                raise serializers.ValidationError({'company_id': 'Company not found.'})
            if organization_id and str(company.organization_id) != str(organization_id):
                raise serializers.ValidationError({
                    'company_id': 'Company must belong to the specified organization.'
                })
        
        if role == 'employee' and company_id:
            if not Company.objects.filter(id=company_id).exists():
                raise serializers.ValidationError({'company_id': 'Company not found.'})
        if role == 'employee' and attrs.get('employee_pin'):
            pin = (attrs.get('employee_pin') or '').strip()
            if pin and (len(pin) > 10 or not pin.isdigit()):
                raise serializers.ValidationError({
                    'employee_pin': 'Employee PIN must be up to 10 digits (numeric).'
                })
        return attrs
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        full_name = validated_data.pop('full_name', None) or ''
        role = validated_data.pop('role', 'user')
        organization_id = validated_data.pop('organization_id', None)
        company_id = validated_data.pop('company_id', None)
        employee_pin = (validated_data.pop('employee_pin', None) or '').strip() or None
        username = validated_data.pop('username', None) or validated_data['email']
        
        # create_user() hashes password; create user only once
        user = User.objects.create_user(
            email=validated_data['email'],
            username=username,
            password=password,
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            is_active=validated_data.get('is_active', True)
        )

        # Profile: signal already created it; just update full_name
        try:
            profile = user.profile
            if full_name:
                profile.full_name = full_name
                profile.save(update_fields=['full_name', 'updated_at'])
        except Profile.DoesNotExist:
            Profile.objects.create(user=user, email=user.email, full_name=full_name)

        # Single role per user: remove all roles except super_admin, then add exactly one UserRole for this role.
        # Employee -> app_type calendar only (no duplicate scheduler+calendar). Others -> one row with scheduler.
        UserRole.objects.filter(user=user).exclude(role='super_admin').delete()
        if role == 'employee':
            UserRole.objects.get_or_create(user=user, role=role, app_type='calendar', defaults={})
        else:
            UserRole.objects.get_or_create(user=user, role=role, app_type='scheduler', defaults={})
        
        # Assign organization_manager -> Organization.organization_manager
        if role == 'organization_manager' and organization_id:
            from scheduler.models import Organization
            Organization.objects.filter(id=organization_id).update(organization_manager=user)
        
        # Assign company_manager -> Company.company_manager
        if role == 'company_manager' and company_id:
            from scheduler.models import Company
            Company.objects.filter(id=company_id).update(company_manager=user)
        
        # Employee -> store in employees table with all form fields (full name, email, employee_pin, company)
        if role == 'employee':
            from scheduler.models import Company, Employee
            company = None
            if company_id:
                try:
                    company = Company.objects.get(id=company_id)
                except Company.DoesNotExist:
                    pass
            # Use full_name for employee record; fallback to first_name/last_name or email
            if full_name:
                parts = full_name.strip().split(None, 1)
                emp_first = parts[0] if parts else (user.first_name or user.email.split('@')[0])
                emp_last = parts[1] if len(parts) > 1 else (user.last_name or '')
            else:
                emp_first = user.first_name or user.email.split('@')[0]
                emp_last = user.last_name or ''
            obj, created = Employee.objects.get_or_create(
                user=user,
                defaults={
                    'first_name': emp_first,
                    'last_name': emp_last,
                    'email': user.email,
                    'company': company,
                    'status': 'active',
                    'employee_pin': employee_pin,
                }
            )
            if not created:
                update_fields = []
                if company and not obj.company_id:
                    obj.company = company
                    update_fields.extend(['company', 'updated_at'])
                if employee_pin is not None and obj.employee_pin != employee_pin:
                    obj.employee_pin = employee_pin
                    update_fields.extend(['employee_pin', 'updated_at'])
                if full_name and (obj.first_name != emp_first or obj.last_name != emp_last):
                    obj.first_name, obj.last_name = emp_first, emp_last
                    update_fields.extend(['first_name', 'last_name', 'updated_at'])
                if update_fields:
                    obj.save(update_fields=list(dict.fromkeys(update_fields)))
        
        return user
    
    def to_representation(self, instance):
        """Return full user with roles and org/company info for dashboard."""
        return UserSerializer(instance).data


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    full_name = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'password_confirm', 'full_name']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        full_name = validated_data.pop('full_name', None)
        username = validated_data.pop('username', None) or validated_data['email']

        user = User.objects.create_user(
            email=validated_data['email'],
            username=username,
            password=validated_data['password']
        )

        # Profile and default UserRole are created by post_save signal (accounts.signals).
        # Only update profile full_name if provided.
        if full_name:
            try:
                profile = user.profile
                profile.full_name = full_name
                profile.save(update_fields=['full_name', 'updated_at'])
            except Profile.DoesNotExist:
                Profile.objects.create(user=user, email=user.email, full_name=full_name)

        return user


class LoginSerializer(serializers.Serializer):
    """Login by email + password. Returns user + JWT. Works for all roles (Super Admin, Org/Company Manager, Employee)."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = (attrs.get('email') or '').strip()
        password = attrs.get('password')

        if not email or not password:
            raise serializers.ValidationError('Must include email and password')

        UserModel = get_user_model()
        # Case-insensitive email lookup so Company@x.com and company@x.com both work
        # Optimize query with select_related/prefetch_related for login response
        try:
            user = UserModel.objects.select_related(
                'profile'
            ).prefetch_related(
                'roles', 'managed_organizations', 'managed_companies', 'employee_profile__company'
            ).get(email__iexact=email)
        except UserModel.DoesNotExist:
            # Run default hasher to reduce timing difference (security)
            UserModel().set_password(password)
            raise serializers.ValidationError('Invalid email or password')

        if not user.check_password(password):
            UserModel().set_password(password)
            raise serializers.ValidationError('Invalid email or password')

        if not getattr(user, 'is_active', True):
            raise serializers.ValidationError('User account is disabled')

        attrs['user'] = user
        return attrs
    
    def to_representation(self, instance):
        # DRF passes validated_data (dict with 'user' key) after is_valid()
        user = None
        if isinstance(instance, dict):
            user = instance.get('user')
        elif hasattr(instance, 'pk') and hasattr(instance, 'email'):
            user = instance  # instance is the User
        else:
            user = getattr(instance, 'user', None)
        if not user:
            return {'user': None, 'access': '', 'refresh': ''}
        try:
            refresh = RefreshToken.for_user(user)
            user_data = UserSerializer(user).data
        except Exception:
            # Minimal payload so login still works (e.g. token for superuser)
            refresh = RefreshToken.for_user(user)
            user_data = {
                'id': str(user.id),
                'email': user.email,
                'username': getattr(user, 'username', None),
                'is_active': user.is_active,
                'profile': None,
                'roles': [],
            }
        return {
            'user': user_data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }

