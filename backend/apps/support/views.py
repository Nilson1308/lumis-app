from django.db.models import Count, Prefetch, Q
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from .models import SupportTicket, SupportTicketReply
from .serializers import MAX_ATTACHMENT_BYTES
from .serializers import (
    SupportTicketCreateSerializer,
    SupportTicketDetailSerializer,
    SupportTicketListSerializer,
)


class SupportTicketViewSet(viewsets.ModelViewSet):
    """
    Chamados de suporte: usuários autenticados abrem e consultam apenas os próprios.
    Gestão (status/respostas internas) via Django Admin.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        qs = (
            SupportTicket.objects.filter(requester=self.request.user)
            .annotate(replies_count=Count('replies', filter=Q(replies__is_internal=False)))
            .select_related('requester')
        )
        if self.action == 'retrieve':
            qs = qs.prefetch_related(
                Prefetch(
                    'replies',
                    queryset=SupportTicketReply.objects.filter(is_internal=False).select_related('author'),
                )
            )
        return qs

    def get_serializer_class(self):
        if self.action == 'create':
            return SupportTicketCreateSerializer
        if self.action == 'retrieve':
            return SupportTicketDetailSerializer
        return SupportTicketListSerializer

    def _attachment_from_request(self):
        """Arquivo só via multipart (request.FILES), nunca via JSON em request.data."""
        upload = self.request.FILES.get('attachment')
        if not upload:
            return None
        if not hasattr(upload, 'read'):
            raise ValidationError(
                {'attachment': ['Anexo inválido. Use o botão de selecionar arquivo.']}
            )
        if upload.size > MAX_ATTACHMENT_BYTES:
            raise ValidationError(
                {'attachment': ['O anexo deve ter no máximo 5 MB.']}
            )
        return upload

    def perform_create(self, serializer):
        attachment = self._attachment_from_request()
        serializer.save(
            requester=self.request.user,
            status=SupportTicket.STATUS_OPEN,
            attachment=attachment,
        )
