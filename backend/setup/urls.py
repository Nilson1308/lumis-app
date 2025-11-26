from django.contrib import admin
from django.urls import path, include
# Importar as views do JWT
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.academic.urls')),
    path('api/', include('apps.core.urls')),
    path('api/', include('apps.coordination.urls')),
    
    # Rotas de Autenticação
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'), # Login
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'), # Atualizar Token
]