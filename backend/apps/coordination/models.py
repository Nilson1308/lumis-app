from django.db import models
from django.conf import settings
from apps.academic.models import TeacherAssignment, Student

class WeeklyReport(models.Model):
    """Relatório Semanal da Coordenadora"""
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Autor")
    start_date = models.DateField("Início da Semana")
    end_date = models.DateField("Fim da Semana")
    description = models.TextField("Resumo das Atividades")
    pending_issues = models.TextField("Pendências / Pontos de Atenção", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Relatório Semanal"
        verbose_name_plural = "Relatórios Semanais"
        ordering = ['-start_date']

    def __str__(self):
        return f"Relatório {self.author} ({self.start_date})"

class ClassObservation(models.Model):
    """Observação de Sala de Aula (Feedback ao Professor)"""
    coordinator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='observations_made', verbose_name="Coordenador")
    assignment = models.ForeignKey(TeacherAssignment, on_delete=models.CASCADE, verbose_name="Aula Observada")
    date = models.DateField("Data da Observação")
    pontuality = models.IntegerField("Pontualidade (1-5)", default=3)
    class_control = models.IntegerField("Domínio de Classe (1-5)", default=3)
    planning = models.IntegerField("Cumprimento do Planejamento (1-5)", default=3)
    student_engagement = models.IntegerField("Engajamento dos Alunos (1-5)", default=3)
    strong_points = models.TextField("Pontos Fortes")
    points_to_improve = models.TextField("Pontos a Melhorar")
    feedback_given = models.BooleanField("Feedback já foi passado?", default=False)
    is_read = models.BooleanField(default=False, verbose_name="Lido pelo Professor")

    class Meta:
        verbose_name = "Observação de Sala"
        verbose_name_plural = "Observações de Sala"

    def __str__(self):
        return f"Obs: {self.assignment.teacher} - {self.date}"

class MeetingMinute(models.Model):
    """Ata de Reunião"""
    title = models.CharField("Título / Pauta", max_length=200)
    date = models.DateField("Data da Reunião")
    participants = models.TextField("Participantes") # Lista de nomes em texto
    content = models.TextField("Conteúdo / Decisões")
    next_steps = models.TextField("Próximos Passos / Tarefas", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        verbose_name = "Ata de Reunião"
        verbose_name_plural = "Atas de Reunião"
        ordering = ['-date']

    def __str__(self):
        return f"Ata: {self.title} ({self.date})"

class StudentReport(models.Model):
    # --- STATUS EXISTENTE (Fluxo de Aprovação) ---
    STATUS_CHOICES = [
        ('PENDING', 'Pendente de Aprovação'),
        ('APPROVED', 'Aprovado'),
        ('REJECTED', 'Precisa de Ajustes')
    ]

    # --- NOVOS CAMPOS (Tipificação) ---
    TYPE_CHOICES = [
        ('PEDAGOGICAL', 'Pedagógico/Acompanhamento'), # Padrão (Relatórios longos)
        ('DISCIPLINARY', 'Disciplinar/Ocorrência'),   # Ocorrências negativas
        ('PRAISE', 'Elogio/Mérito'),                  # Ocorrências positivas
        ('MEDICAL', 'Saúde/Enfermaria'),              # Ocorrências de saúde
    ]

    LEVEL_CHOICES = [
        ('LOW', 'Baixo/Informativo'),      # Apenas registro
        ('MEDIUM', 'Médio/Atenção'),       # Requer observação
        ('CRITICAL', 'Crítico/Urgente'),   # Requer convocação dos pais
    ]

    student = models.ForeignKey('academic.Student', on_delete=models.CASCADE, related_name='reports')
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Adicionamos os novos campos com defaults para não quebrar dados antigos
    report_type = models.CharField("Tipo", max_length=20, choices=TYPE_CHOICES, default='PEDAGOGICAL')
    severity_level = models.CharField("Nível de Gravidade", max_length=10, choices=LEVEL_CHOICES, default='LOW')

    date = models.DateField(verbose_name="Data do Relatório")
    subject = models.CharField(max_length=200, verbose_name="Assunto")
    content = models.TextField(verbose_name="Conteúdo")
    
    # Controle da Coordenação
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    visible_to_family = models.BooleanField(default=False, verbose_name="Disponível para os Pais")
    coordinator_comment = models.TextField(null=True, blank=True, verbose_name="Comentário da Coordenação")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_report_type_display()}] {self.student.name} - {self.subject}"