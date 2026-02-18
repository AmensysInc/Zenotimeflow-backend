from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'habits', views.HabitViewSet, basename='habit')
router.register(r'completions', views.HabitCompletionViewSet, basename='habit-completion')

urlpatterns = [
    path('', include(router.urls)),
]

