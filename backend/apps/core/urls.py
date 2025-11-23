from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet

router = DefaultRouter()
# Isso cria a rota /api/users/ e /api/users/me/
router.register(r'users', UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
]