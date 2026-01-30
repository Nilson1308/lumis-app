from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import get_user_model
from .models import SchoolAccount, Notification
from .serializers import UserSerializer, SchoolAccountSerializer, NotificationSerializer

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer # <--- Garanta que está usando o Serializer correto

    # Endpoint 'me' para retornar o usuário logado
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

class SchoolConfigView(APIView):
    """
    Retorna a configuração da escola ativa para personalizar o Frontend (White Label).
    Aberto ao público (AllowAny) para carregar na tela de login.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        # Pega a primeira configuração encontrada (Single Tenant)
        # Se no futuro for multi-tenant, aqui entra a lógica de domínios
        config = SchoolAccount.objects.first()
        
        if config:
            serializer = SchoolAccountSerializer(config, context={'request': request})
            return Response(serializer.data)
        
        # Se não houver config, retorna 204 (No Content) ou 404
        # O Frontend entenderá isso e usará o padrão 'Lumis'
        return Response(status=404)

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        # Cada usuário só vê as suas notificações
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=True, methods=['patch'])
    def mark_read(self, request, pk=None):
        notif = self.get_object()
        notif.read = True
        notif.save()
        return Response({'status': 'read'})

    @action(detail=False, methods=['patch'])
    def mark_all_read(self, request):
        self.get_queryset().update(read=True)
        return Response({'status': 'all_read'})