from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'user-roles', views.UserRoleViewSet, basename='userrole')

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('employee-login/', views.employee_login, name='employee_login'),
    path('logout/', views.logout, name='logout'),
    path('send-welcome-email/', views.send_welcome_email, name='send_welcome_email'),
    path('me/', views.me, name='me'),
    path('user/', views.me, name='user'),  # Alias for frontend: GET /api/auth/user/ → current user
    path('profile/', views.update_profile, name='update_profile'),
    path('profiles/<uuid:pk>/', views.ProfileDetailView.as_view(), name='profile-detail'),
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('users/<uuid:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    path('', include(router.urls)),
]

