"""
URL configuration for zeno_time project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/scheduler/', include('scheduler.urls')),
    path('api/calendar/', include('calendar_app.urls')),
    path('api/tasks/', include('tasks.urls')),
    path('api/habits/', include('habits.urls')),
    path('api/focus/', include('focus.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

