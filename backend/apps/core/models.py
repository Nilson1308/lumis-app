from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

def default_non_teaching_event_types():
    return ['HOLIDAY']

class User(AbstractUser):
    is_teacher = models.BooleanField(default=False)
    is_coordinator = models.BooleanField(default=False)
    
    class Meta:
        # Isso garante que o Django use a tabela padrão 'auth_user' se quiser,
        # mas recomenda-se deixar o Django gerenciar.
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

    def __str__(self):
        return self.username

class SchoolAccount(models.Model):
    """
    Configurações da Conta (Tenant) para White Label.
    Geralmente haverá apenas 1 registro por instância do sistema.
    """
    name = models.CharField("Nome da Escola", max_length=100)
    slug = models.SlugField(unique=True, help_text="Identificador único (ex: saint-thomas)")
    
    # Identidade Visual
    logo = models.ImageField("Logotipo", upload_to='school_logos/', null=True, blank=True)
    icon = models.ImageField("Ícone (Favicon/Mobile)", upload_to='school_icons/', null=True, blank=True)
    primary_color = models.CharField("Cor Primária (Hex)", max_length=7, default='#6366f1', help_text="Ex: #3B82F6")
    secondary_color = models.CharField("Cor Secundária (Hex)", max_length=7, default='#475569', help_text="Ex: #1E293B")
    
    # Dados Institucionais (Rodapé/Contato)
    email = models.EmailField("Email de Contato", blank=True)
    phone = models.CharField("Telefone", max_length=20, blank=True)
    address = models.TextField("Endereço", blank=True)
    website = models.URLField("Site Oficial", blank=True)
    non_teaching_event_types = models.JSONField(
        "Tipos não letivos no calendário",
        default=default_non_teaching_event_types,
        blank=True,
        help_text="Tipos de evento do calendário que NÃO exigem chamada. Ex: ['HOLIDAY', 'MEETING']",
    )
    enforce_lesson_plan_submission_guard = models.BooleanField(
        "Bloquear envio de planejamento por atraso",
        default=False,
        help_text="Quando ativo, professores com planejamento semanal em atraso ficam bloqueados até liberação da coordenação/admin.",
    )

    @staticmethod
    def _allowed_calendar_event_types():
        from apps.academic.models import SchoolEvent
        return {value for value, _ in SchoolEvent.EVENT_TYPES}

    def clean(self):
        values = self.non_teaching_event_types or []
        if not isinstance(values, list):
            raise ValidationError({
                'non_teaching_event_types': 'Informe uma lista de tipos de evento (ex: ["HOLIDAY", "MEETING"]).'
            })

        allowed = self._allowed_calendar_event_types()
        normalized = []
        invalid = []
        for raw_value in values:
            value = str(raw_value).strip().upper()
            if value in allowed and value not in normalized:
                normalized.append(value)
            elif value not in allowed:
                invalid.append(value)

        if invalid:
            raise ValidationError({
                'non_teaching_event_types': (
                    f"Tipos inválidos: {', '.join(invalid)}. "
                    f"Permitidos: {', '.join(sorted(allowed))}."
                )
            })

        self.non_teaching_event_types = normalized or default_non_teaching_event_types()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Configuração da Escola"
        verbose_name_plural = "Configurações da Escola"

class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, null=True) # Ex: /teacher/planning
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"


class AccessAuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='access_audits')
    action = models.CharField(max_length=80)
    resource_type = models.CharField(max_length=80)
    resource_id = models.CharField(max_length=80, blank=True)
    student_id = models.IntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Log de Auditoria"
        verbose_name_plural = "Logs de Auditoria"

    def __str__(self):
        username = self.user.username if self.user else "anon"
        return f"{self.action} - {username} - {self.created_at:%Y-%m-%d %H:%M}"