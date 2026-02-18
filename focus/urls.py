from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'sessions', views.FocusSessionViewSet, basename='focus-session')
router.register(r'blocks', views.FocusBlockViewSet, basename='focus-block')

urlpatterns = [
    path('', include(router.urls)),
]

