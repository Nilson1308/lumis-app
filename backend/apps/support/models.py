from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models


class SupportTicket(models.Model):
    STATUS_OPEN = 'OPEN'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_RESOLVED = 'RESOLVED'
    STATUS_CANCELLED = 'CANCELLED'

    STATUS_CHOICES = [
        (STATUS_OPEN, 'Aberto'),
        (STATUS_IN_PROGRESS, 'Em atendimento'),
        (STATUS_RESOLVED, 'Resolvido'),
        (STATUS_CANCELLED, 'Cancelado'),
    ]

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='support_tickets',
        verbose_name='Solicitante',
    )
    occurred_date = models.DateField('Data da ocorrência')
    occurred_time = models.TimeField('Hora da ocorrência')
    description = models.TextField('Descrição')
    attachment = models.FileField(
        'Anexo',
        upload_to='support/tickets/%Y/%m/',
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
                    'jpg', 'jpeg', 'png',
                ]
            )
        ],
    )
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']
        verbose_name = 'Chamado de suporte'
        verbose_name_plural = 'Chamados de suporte'

    def __str__(self):
        return f'#{self.pk} — {self.requester} ({self.get_status_display()})'


class SupportTicketReply(models.Model):
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name='replies',
        verbose_name='Chamado',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='support_ticket_replies',
        verbose_name='Autor',
    )
    message = models.TextField('Mensagem')
    is_internal = models.BooleanField(
        'Nota interna (não visível ao solicitante)',
        default=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']
        verbose_name = 'Resposta do chamado'
        verbose_name_plural = 'Respostas do chamado'

    def __str__(self):
        return f'Resposta #{self.pk} — chamado {self.ticket_id}'
