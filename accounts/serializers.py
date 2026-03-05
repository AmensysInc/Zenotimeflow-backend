import re
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Profile, UserRole


def normalize_phone_10(value):
    """Strip non-digits and return last 10 digits, or None if fewer than 10 digits."""
    if value is None:
        return None
    digits = re.sub(r'\D', '', str(value).strip())
    if len(digits) < 10:
        return None
    return digits[-10:] if len(digits) > 10 else digits


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
            # OneToOne reverse: user.employee_profile raises if no Employee; catch it
            try:
                emp = obj.employee_profile
            except Exception:
                emp = None
            if emp is not None and getattr(emp, 'company_id', None):
                return str(emp.company_id)
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
    # Profile: 10-digit phone (no country code); stored in Profile.mobile_number
    mobile_number = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=20)

    class Meta:
        model = User
        fields = [
            'email', 'username', 'password', 'first_name', 'last_name',
            'is_active', 'full_name', 'role', 'organization_id', 'company_id', 'employee_pin', 'mobile_number'
        ]
    
    def validate(self, attrs):
        role = attrs.get('role', 'user')
        organization_id = attrs.get('organization_id')
        company_id = attrs.get('company_id')
        email = (attrs.get('email') or '').strip().lower()
        username = (attrs.get('username') or '').strip() or None
        if not username and email:
            username = email  # fallback for create()

        # Create only once: reject duplicate email (case-insensitive)
        if email and User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({'email': 'A user with this email already exists.'})
        if username and User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError({'username': 'A user with this username already exists.'})

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
        mobile_number_raw = (validated_data.pop('mobile_number', None) or '').strip() or None
        mobile_number = normalize_phone_10(mobile_number_raw) if mobile_number_raw else None
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

        # Profile: signal already created it; just update full_name and mobile_number
        try:
            profile = user.profile
            update_fields = ['updated_at']
            if full_name:
                profile.full_name = full_name
                update_fields.append('full_name')
            if mobile_number is not None:
                profile.mobile_number = mobile_number
                update_fields.append('mobile_number')
            profile.save(update_fields=update_fields)
        except Profile.DoesNotExist:
            Profile.objects.create(
                user=user, email=user.email, full_name=full_name,
                mobile_number=mobile_number or ''
            )

        # Employee: create Employee record BEFORE adding UserRole so the post_save signal
        # (ensure_employee_record_for_employee_role) sees it exists and doesn't create a minimal one without company/PIN.
        if role == 'employee':
            from scheduler.models import Company, Employee
            company = None
            if company_id:
                try:
                    company = Company.objects.get(id=company_id)
                except Company.DoesNotExist:
                    pass
            if full_name:
                parts = full_name.strip().split(None, 1)
                emp_first = parts[0] if parts else (user.first_name or user.email.split('@')[0])
                emp_last = parts[1] if len(parts) > 1 else (user.last_name or '')
            else:
                emp_first = user.first_name or user.email.split('@')[0]
                emp_last = user.last_name or ''
            Employee.objects.create(
                user=user,
                first_name=emp_first,
                last_name=emp_last,
                email=user.email,
                company=company,
                status='active',
                employee_pin=employee_pin,
            )

        # Single role per user: remove all roles except super_admin, then add exactly one UserRole for this role.
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
        
        return user
    
    def to_representation(self, instance):
        """Return full user with roles and org/company info for dashboard."""
        return UserSerializer(instance).data


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    full_name = serializers.CharField(write_only=True, required=False)
    mobile_number = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=20)
    
    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'password_confirm', 'full_name', 'mobile_number']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        full_name = validated_data.pop('full_name', None)
        mobile_number_raw = (validated_data.pop('mobile_number', None) or '').strip() or None
        mobile_number = normalize_phone_10(mobile_number_raw) if mobile_number_raw else None
        username = validated_data.pop('username', None) or validated_data['email']

        user = User.objects.create_user(
            email=validated_data['email'],
            username=username,
            password=validated_data['password']
        )

        # Profile and default UserRole are created by post_save signal (accounts.signals).
        try:
            profile = user.profile
            update_fields = ['updated_at']
            if full_name:
                profile.full_name = full_name
                update_fields.append('full_name')
            if mobile_number is not None:
                profile.mobile_number = mobile_number
                update_fields.append('mobile_number')
            profile.save(update_fields=update_fields)
        except Profile.DoesNotExist:
            Profile.objects.create(
                user=user, email=user.email, full_name=full_name or '',
                mobile_number=mobile_number or ''
            )

        return user


class EmployeeLoginSerializer(serializers.Serializer):
    """Login for mobile/clock-in: username + employee PIN. Returns user + employee + JWT. For users with Employee record only."""
    username = serializers.CharField(required=True, allow_blank=False)
    pin = serializers.CharField(write_only=True, max_length=10)

    def validate(self, attrs):
        from scheduler.models import Employee
        login_id = (attrs.get('username') or '').strip()
        pin = (attrs.get('pin') or '').strip()

        if not login_id or not pin:
            raise serializers.ValidationError('Username and PIN are required.')

        UserModel = get_user_model()
        user = UserModel.objects.select_related('profile').prefetch_related('roles').filter(
            Q(username__iexact=login_id) | Q(email__iexact=login_id)
        ).first()
        if not user:
            phone_10 = normalize_phone_10(login_id)
            if phone_10:
                for p in Profile.objects.select_related('user').prefetch_related('user__roles').filter(
                    mobile_number__isnull=False
                ).exclude(mobile_number=''):
                    if normalize_phone_10(p.mobile_number) == phone_10:
                        user = p.user
                        break
        if not user:
            raise serializers.ValidationError('Invalid username or PIN.')

        if not getattr(user, 'is_active', True):
            raise serializers.ValidationError('User account is disabled.')

        employee = Employee.objects.filter(user=user).first()
        if not employee:
            raise serializers.ValidationError(
                'No employee record for this email. Ask your manager to add you as an employee in User Management.'
            )
        if not (employee.employee_pin or str(employee.employee_pin).strip()):
            raise serializers.ValidationError(
                'Employee PIN is not set. Ask your manager to set your PIN in User Management (Edit User → Employee PIN).'
            )
        if str(employee.employee_pin).strip() != pin:
            raise serializers.ValidationError('Invalid PIN.')

        attrs['user'] = user
        attrs['employee'] = employee
        return attrs


class LoginSerializer(serializers.Serializer):
    """Login by username + password (username can be the user's username or email). Returns user + JWT."""
    username = serializers.CharField(required=True, allow_blank=False)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        login_id = (attrs.get('username') or '').strip()
        password = attrs.get('password')

        if not login_id or not password:
            raise serializers.ValidationError('Must include username and password')

        UserModel = get_user_model()
        # Look up by username or email (case-insensitive)
        try:
            user = UserModel.objects.select_related('profile').prefetch_related('roles').filter(
                Q(username__iexact=login_id) | Q(email__iexact=login_id)
            ).first()
        except Exception:
            user = None
        # If not found, try 10-digit phone (no country code; users enter digits only)
        if not user:
            phone_10 = normalize_phone_10(login_id)
            if phone_10:
                for p in Profile.objects.select_related('user').prefetch_related('user__roles').filter(
                    mobile_number__isnull=False
                ).exclude(mobile_number=''):
                    if normalize_phone_10(p.mobile_number) == phone_10:
                        user = p.user
                        break
        if not user:
            UserModel().set_password(password)
            raise serializers.ValidationError('Invalid username or password')

        if not user.check_password(password):
            UserModel().set_password(password)
            raise serializers.ValidationError('Invalid username or password')

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

