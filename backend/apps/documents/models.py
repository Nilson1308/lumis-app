from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models


class SharedDocument(models.Model):
    CATEGORY_CHOICES = [
        ('GENERAL', 'Geral'),
        ('PEDAGOGICAL', 'Pedagógico'),
        ('ADMINISTRATIVE', 'Administrativo'),
        ('FINANCIAL', 'Financeiro'),
        ('EVENTS', 'Eventos'),
    ]

    TARGET_AUDIENCE = [
        ('ALL', 'Todos (professores e responsáveis)'),
        ('TEACHERS', 'Professores'),
        ('GUARDIANS', 'Responsáveis / Pais'),
        ('CLASSROOM', 'Turma específica'),
        ('SEGMENT', 'Segmento / série'),
    ]

    ALLOWED_EXTENSIONS = [
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
        'jpg', 'jpeg', 'png', 'zip',
    ]

    title = models.CharField('Título', max_length=200)
    description = models.TextField('Descrição', blank=True)
    category = models.CharField(
        'Categoria',
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='GENERAL',
    )
    target_audience = models.CharField(
        'Público-alvo',
        max_length=20,
        choices=TARGET_AUDIENCE,
        default='ALL',
    )
    classroom = models.ForeignKey(
        'academic.ClassRoom',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='shared_documents',
        verbose_name='Turma',
    )
    segment = models.ForeignKey(
        'academic.Segment',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='shared_documents',
        verbose_name='Segmento',
    )
    file = models.FileField(
        'Arquivo',
        upload_to='documents/%Y/%m/',
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=ALLOWED_EXTENSIONS),
        ],
    )
    external_link = models.URLField('Link externo', blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_documents',
        verbose_name='Enviado por',
    )
    is_active = models.BooleanField('Ativo', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']
        verbose_name = 'Documento compartilhado'
        verbose_name_plural = 'Documentos compartilhados'

    def __str__(self):
        return self.title

    def clean(self):
        if self.target_audience == 'CLASSROOM' and not self.classroom_id:
            raise ValidationError({'classroom': 'Selecione a turma para documentos de turma específica.'})
        if self.target_audience == 'SEGMENT' and not self.segment_id:
            raise ValidationError({'segment': 'Selecione o segmento/série.'})
        if self.target_audience != 'CLASSROOM':
            self.classroom = None
        if self.target_audience != 'SEGMENT':
            self.segment = None
        if not self.file and not self.external_link:
            raise ValidationError('Informe um arquivo ou um link externo.')
        if self.file and self.external_link:
            raise ValidationError('Use apenas arquivo ou link externo, não ambos.')


class SharedDocumentReadStatus(models.Model):
    document = models.ForeignKey(
        SharedDocument,
        on_delete=models.CASCADE,
        related_name='read_statuses',
        verbose_name='Documento',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shared_document_reads',
        verbose_name='Usuário',
    )
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='Lido em')

    class Meta:
        unique_together = ('document', 'user')
        verbose_name = 'Leitura de documento'
        verbose_name_plural = 'Leituras de documentos'

    def __str__(self):
        return f'{self.user_id} -> doc {self.document_id}'
