from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'organizations', views.OrganizationViewSet, basename='organization')
router.register(r'companies', views.CompanyViewSet, basename='company')
router.register(r'departments', views.DepartmentViewSet, basename='department')
router.register(r'teams', views.ScheduleTeamViewSet, basename='team')
router.register(r'employees', views.EmployeeViewSet, basename='employee')
router.register(r'shifts', views.ShiftViewSet, basename='shift')
router.register(r'replacement-requests', views.ShiftReplacementRequestViewSet, basename='replacement-request')
router.register(r'availability', views.EmployeeAvailabilityViewSet, basename='availability')
router.register(r'time-clock', views.TimeClockViewSet, basename='time-clock')
router.register(r'schedule-templates', views.ScheduleTemplateViewSet, basename='schedule-template')
router.register(r'settings', views.AppSettingsViewSet, basename='app-settings')

urlpatterns = [
    path('', include(router.urls)),
]

