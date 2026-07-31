from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SharedDocumentViewSet

router = DefaultRouter()
router.register(r'shared-documents', SharedDocumentViewSet, basename='shared-documents')

urlpatterns = [
    path('', include(router.urls)),
]
