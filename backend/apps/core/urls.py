from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, SchoolConfigView, NotificationViewSet, PasswordResetRequestView, PasswordResetConfirmView, AccessAuditLogViewSet

router = DefaultRouter()
# Isso cria a rota /api/users/ e /api/users/me/
router.register(r'users', UserViewSet)
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'access-audits', AccessAuditLogViewSet, basename='access-audits')

urlpatterns = [
    path('', include(router.urls)),
    path('school-config/', SchoolConfigView.as_view(), name='school-config'),
    path('password_reset/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password_reset_confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]