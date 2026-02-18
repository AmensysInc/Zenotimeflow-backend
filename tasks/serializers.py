from rest_framework import serializers
from .models import Task, TaskComment, TaskAttachment
from accounts.serializers import UserSerializer


class TaskAttachmentSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = TaskAttachment
        fields = [
            'id', 'task', 'user', 'user_email', 'file', 'file_name',
            'file_size', 'mime_type', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']


class TaskCommentSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_details = UserSerializer(source='user', read_only=True)
    
    class Meta:
        model = TaskComment
        fields = [
            'id', 'task', 'user', 'user_email', 'user_details',
            'content', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class TaskSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    assigned_to_details = UserSerializer(source='assigned_to', many=True, read_only=True)
    assigned_to_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Task._meta.get_field('assigned_to').related_model.objects.all(),
        source='assigned_to',
        write_only=True,
        required=False
    )
    subtasks = serializers.SerializerMethodField()
    comments_count = serializers.IntegerField(source='comments.count', read_only=True)
    attachments_count = serializers.IntegerField(source='attachments.count', read_only=True)
    
    class Meta:
        model = Task
        fields = [
            'id', 'user', 'user_email', 'title', 'description', 'status', 'priority',
            'due_date', 'completed_at', 'color', 'tags', 'assigned_to', 'assigned_to_details',
            'assigned_to_ids', 'parent_task', 'is_template', 'template_name',
            'estimated_hours', 'actual_hours', 'subtasks', 'comments_count',
            'attachments_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'completed_at', 'created_at', 'updated_at']
    
    def get_subtasks(self, obj):
        if obj.subtasks.exists():
            return TaskSerializer(obj.subtasks.all(), many=True).data
        return []
    
    def create(self, validated_data):
        assigned_to = validated_data.pop('assigned_to', [])
        task = Task.objects.create(**validated_data)
        if assigned_to:
            task.assigned_to.set(assigned_to)
        return task
    
    def update(self, instance, validated_data):
        assigned_to = validated_data.pop('assigned_to', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if assigned_to is not None:
            instance.assigned_to.set(assigned_to)
        return instance


class TaskDetailSerializer(TaskSerializer):
    """Extended serializer with comments and attachments"""
    comments = TaskCommentSerializer(many=True, read_only=True)
    attachments = TaskAttachmentSerializer(many=True, read_only=True)

