from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Profile, UserRole


class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRole
        fields = ['id', 'role', 'app_type', 'created_at']


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
    profile = ProfileSerializer(read_only=True)
    roles = UserRoleSerializer(many=True, read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'is_active', 'date_joined', 'profile', 'roles'
        ]
        read_only_fields = ['id', 'date_joined']


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
        
        # Create profile
        Profile.objects.create(
            user=user,
            email=user.email,
            full_name=full_name
        )
        
        # Create default user role
        UserRole.objects.create(
            user=user,
            role='user',
            app_type='calendar'
        )
        
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(request=self.context.get('request'), username=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid email or password')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('Must include email and password')
        
        return attrs
    
    def to_representation(self, instance):
        refresh = RefreshToken.for_user(instance['user'])
        user_serializer = UserSerializer(instance['user'])
        
        return {
            'user': user_serializer.data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }

