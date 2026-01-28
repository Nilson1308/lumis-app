from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, SchoolConfigView

router = DefaultRouter()
# Isso cria a rota /api/users/ e /api/users/me/
router.register(r'users', UserViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('school-config/', SchoolConfigView.as_view(), name='school-config'),
]