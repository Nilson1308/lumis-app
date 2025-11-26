from django.db import models
from django.conf import settings
from apps.academic.models import TeacherAssignment

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
    # Vincula à atribuição (sabe qual professor, qual turma e qual matéria)
    assignment = models.ForeignKey(TeacherAssignment, on_delete=models.CASCADE, verbose_name="Aula Observada")
    date = models.DateField("Data da Observação")
    
    # Critérios de Avaliação (Exemplos baseados em formulários comuns)
    pontuality = models.IntegerField("Pontualidade (1-5)", default=3)
    class_control = models.IntegerField("Domínio de Classe (1-5)", default=3)
    planning = models.IntegerField("Cumprimento do Planejamento (1-5)", default=3)
    student_engagement = models.IntegerField("Engajamento dos Alunos (1-5)", default=3)
    
    strong_points = models.TextField("Pontos Fortes")
    points_to_improve = models.TextField("Pontos a Melhorar")
    feedback_given = models.BooleanField("Feedback já foi passado?", default=False)

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