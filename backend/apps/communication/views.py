from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from .models import Announcement, AnnouncementReadStatus
from .serializers import AnnouncementSerializer

class AnnouncementViewSet(viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer

    def get_queryset(self):
        user = self.request.user
        
        return Announcement.objects.filter(
            Q(sender=user) | Q(recipients=user)
        ).distinct().order_by('-created_at')

    def perform_create(self, serializer):
        """
        Criação de anúncio.
        A relação ManyToMany `recipients` já usa a tabela intermediária
        `AnnouncementReadStatus` (via `through=`). Quando salvamos o
        `recipient_ids` pelo serializer, o Django cria automaticamente
        os registros na tabela de through.

        Antes, este método ainda criava manualmente um
        `AnnouncementReadStatus` para cada destinatário, o que gerava
        `IntegrityError` por violar o `unique_together (announcement, user)`.
        """

        # 1. Salva a mensagem com o remetente correto
        announcement = serializer.save(sender=self.request.user)

        # 2. Se o front enviou `recipient_ids`, garantimos que o ManyToMany
        # seja atualizado a partir deles (evita qualquer inconsistência).
        recipient_ids = self.request.data.get('recipient_ids', [])
        if recipient_ids:
            # Isso cria (ou ajusta) os registros na tabela de through
            announcement.recipients.set(recipient_ids)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Professor chama isso ao abrir a mensagem"""
        announcement = self.get_object()
        user = request.user
        
        try:
            status_obj = AnnouncementReadStatus.objects.get(announcement=announcement, user=user)
            if not status_obj.read_at:
                status_obj.read_at = timezone.now()
                status_obj.save()
            return Response({'status': 'read'})
        except AnnouncementReadStatus.DoesNotExist:
            return Response({'error': 'Você não é destinatário'}, status=400)
            
    @action(detail=True, methods=['get'])
    def report(self, request, pk=None):
        """Gestor vê quem leu e quem não leu"""
        announcement = self.get_object()
        statuses = AnnouncementReadStatus.objects.filter(announcement=announcement).select_related('user')
        
        data = []
        for s in statuses:
            data.append({
                'name': s.user.get_full_name() or s.user.username,
                'read': s.read_at is not None,
                'read_at': s.read_at
            })
        return Response(data)