from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from . import views
from .views import is_template_admin, TemplateAssignmentViewSet
from .models import TemplateAssignment

router = DefaultRouter()
router.register(r'', views.LearningTemplateViewSet, basename='template')


class AssignmentsListOrDeleteView(APIView):
    """Handle GET, POST for list/create and DELETE with ?template_id=&user_id= for web UI."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        view = TemplateAssignmentViewSet.as_view({'get': 'list'})
        return view(request)

    def post(self, request):
        view = TemplateAssignmentViewSet.as_view({'post': 'create'})
        return view(request)

    def delete(self, request):
        template_id = request.query_params.get('template_id')
        user_id = request.query_params.get('user_id')
        if not template_id or not user_id:
            return Response(
                {'detail': 'template_id and user_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not is_template_admin(request.user):
            return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        deleted, _ = TemplateAssignment.objects.filter(
            template_id=template_id,
            user_id=user_id
        ).delete()
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'detail': 'Assignment not found'}, status=status.HTTP_404_NOT_FOUND)


urlpatterns = [
    path('assignments/', AssignmentsListOrDeleteView.as_view()),
    path('assignments/<uuid:pk>/', TemplateAssignmentViewSet.as_view({
        'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'
    })),
    path('', include(router.urls)),
]
