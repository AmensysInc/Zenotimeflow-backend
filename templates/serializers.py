from rest_framework import serializers
from .models import LearningTemplate, TemplateAssignment


class TemplateAssignmentSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    template_id = serializers.UUIDField(source='template.id', read_only=True)
    template_id_in = serializers.UUIDField(write_only=True, required=False)
    user_id_in = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = TemplateAssignment
        fields = [
            'id', 'template', 'template_id', 'user', 'user_id',
            'template_id_in', 'user_id_in', 'assigned_by', 'assigned_at'
        ]
        read_only_fields = ['id', 'assigned_at']
        extra_kwargs = {'template': {'required': False}, 'user': {'required': False}}

    def create(self, validated_data):
        validated_data.pop('template_id_in', None)
        validated_data.pop('user_id_in', None)
        tid = self.initial_data.get('template_id') or validated_data.get('template')
        uid = self.initial_data.get('user_id') or validated_data.get('user')
        if tid is None or uid is None:
            raise serializers.ValidationError('template_id and user_id required')
        from django.contrib.auth import get_user_model
        User = get_user_model()
        template = LearningTemplate.objects.get(pk=tid) if not hasattr(tid, 'pk') else tid
        user = User.objects.get(pk=uid) if not hasattr(uid, 'pk') else uid
        return TemplateAssignment.objects.create(
            template=template,
            user=user,
            assigned_by=validated_data.get('assigned_by')
        )


class LearningTemplateSerializer(serializers.ModelSerializer):
    created_by_id = serializers.UUIDField(source='created_by.id', read_only=True, allow_null=True)

    class Meta:
        model = LearningTemplate
        fields = ['id', 'name', 'description', 'technology', 'created_by', 'created_by_id', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class LearningTemplateListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    created_by_id = serializers.UUIDField(source='created_by.id', read_only=True, allow_null=True)

    class Meta:
        model = LearningTemplate
        fields = ['id', 'name', 'description', 'technology', 'created_by_id', 'created_at', 'updated_at']
