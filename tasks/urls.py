from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tasks', views.TaskViewSet, basename='task')
router.register(r'comments', views.TaskCommentViewSet, basename='task-comment')
router.register(r'attachments', views.TaskAttachmentViewSet, basename='task-attachment')

urlpatterns = [
    path('', include(router.urls)),
]

