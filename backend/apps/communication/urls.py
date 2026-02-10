from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views # Importe suas views

router = DefaultRouter()

# ... outras rotas existentes (students, assignments, etc) ...

# ADICIONE ESTA LINHA:
router.register(r'announcements', views.AnnouncementViewSet, basename='announcements')

urlpatterns = [
    path('', include(router.urls)),
]