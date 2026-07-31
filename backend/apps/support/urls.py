from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SupportTicketViewSet

router = DefaultRouter()
router.register(r'support-tickets', SupportTicketViewSet, basename='support-tickets')

urlpatterns = [
    path('', include(router.urls)),
]
