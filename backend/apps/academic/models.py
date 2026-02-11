from django.db import models
from django.core.validators import FileExtensionValidator
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

class Segment(models.Model):
    """Ex: Educação Infantil, Fundamental I, Médio"""
    name = models.CharField("Nome do Segmento", max_length=100)
    
    def __str__(self):
        return self.name

class ClassRoom(models.Model):
    """Ex: 6º Ano A - 2025"""
    name = models.CharField("Nome da Turma", max_length=50)
    year = models.IntegerField("Ano Letivo", default=2025)
    segment = models.ForeignKey(Segment, on_delete=models.PROTECT, verbose_name="Segmento")
    
    class Meta:
        verbose_name = "Turma"
        verbose_name_plural = "Turmas"

    def __str__(self):
        return f"{self.name} ({self.year})"

class Subject(models.Model):
    """Ex: Matemática, História"""
    name = models.CharField("Nome da Matéria", max_length=100)
    
    def __str__(self):
        return self.name

class Guardian(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='guardian_profile'
    )
    name = models.CharField("Nome Completo", max_length=150)
    cpf = models.CharField("CPF", max_length=14, unique=True) 
    rg = models.CharField("RG", max_length=20, blank=True, null=True)
    email = models.EmailField("Email", blank=True, null=True) 
    phone = models.CharField("Celular/WhatsApp", max_length=20)
    secondary_phone = models.CharField("Telefone Secundário / Recado", max_length=20, blank=True, null=True)
    profession = models.CharField("Profissão", max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Responsável"
        verbose_name_plural = "Responsáveis"

    def __str__(self):
        return self.name

class ExtraActivity(models.Model):
    name = models.CharField("Nome da Atividade", max_length=100)
    description = models.TextField("Descrição", blank=True)
    price = models.DecimalField("Valor Mensal", max_digits=10, decimal_places=2, default=0.00)
    
    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Atividade Extra"
        verbose_name_plural = "Atividades Extras"

class Student(models.Model):
    # Identificação Básica
    name = models.CharField("Nome Completo", max_length=150)
    registration_number = models.CharField("Matrícula", max_length=20, unique=True)
    ra = models.CharField("RA (Registro do Aluno)", max_length=20, blank=True, null=True, help_text="Registro Acadêmico do aluno")
    photo = models.ImageField(upload_to='students/', blank=True, null=True)
    
    # Identificação Civil (Novos Campos)
    birth_date = models.DateField("Data de Nascimento", null=True, blank=True)
    gender = models.CharField("Gênero", max_length=10, choices=[('M', 'Masculino'), ('F', 'Feminino')], blank=True)
    cpf = models.CharField("CPF", max_length=14, blank=True, null=True)
    rg = models.CharField("RG", max_length=20, blank=True, null=True)
    nationality = models.CharField("Nacionalidade", max_length=50, default="Brasileira")
    
    # Endereço
    zip_code = models.CharField("CEP", max_length=9, blank=True)
    street = models.CharField("Endereço", max_length=150, blank=True)
    number = models.CharField("Número", max_length=10, blank=True)
    complement = models.CharField("Complemento", max_length=50, blank=True)
    neighborhood = models.CharField("Bairro", max_length=50, blank=True)
    city = models.CharField("Cidade", max_length=50, default="Mogi das Cruzes")
    state = models.CharField("UF", max_length=2, default="SP")

    # Pedagógico & Rotina ---
    PERIOD_CHOICES = [
        ('MORNING', 'Manhã'),
        ('AFTERNOON', 'Tarde'),
    ]
    period = models.CharField("Período", max_length=20, choices=PERIOD_CHOICES, default='AFTERNOON')
    
    is_full_time = models.BooleanField("Integral?", default=False)
    
    MEALS_CHOICES = [
        ('NONE', 'Não optante'),
        ('LUNCH', 'Almoço'),
        ('SNACK', 'Lanche'),
        ('BOTH', 'Almoço + Lanche'),
    ]
    meals = models.CharField("Plano de Refeições", max_length=20, choices=MEALS_CHOICES, default='NONE')

    # atividades extra
    extra_activities = models.ManyToManyField(ExtraActivity, blank=True, verbose_name="Atividades Extras")

    # Dados de Saúde/Emergência
    allergies = models.TextField("Alergias", blank=True)
    medications = models.TextField("Uso Contínuo de Medicamentos", blank=True)
    emergency_contact = models.CharField("Contato de Emergência (Nome/Tel)", max_length=100, blank=True)
    medical_report = models.FileField("Laudo Médico", upload_to='students/medical/', null=True, blank=True)
    prescription = models.FileField("Receita Médica", upload_to='students/prescriptions/', null=True, blank=True)

    # Vínculos
    # ManyToMany: Um aluno pode ter vários responsáveis (Pai e Mãe)
    # e um responsável pode ter vários alunos (Irmãos)
    guardians = models.ManyToManyField(Guardian, related_name="students", verbose_name="Responsáveis", blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Aluno"
        verbose_name_plural = "Alunos"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.registration_number})"

class Enrollment(models.Model):
    """Vincula o Aluno a uma Turma"""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="Aluno")
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, verbose_name="Turma")
    date_enrolled = models.DateField("Data da Matrícula", auto_now_add=True)
    active = models.BooleanField("Ativo", default=True)

    class Meta:
        unique_together = ('student', 'classroom') # Aluno não pode estar 2x na mesma turma
        verbose_name = "Matrícula"

    def __str__(self):
        return f"{self.student.name} -> {self.classroom.name}"

class TeacherAssignment(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name="Professor",
        limit_choices_to={'groups__name': 'Professores'} 
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name="Matéria")
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, verbose_name="Turma")

    class Meta:
        verbose_name = "Atribuição de Aula"
        verbose_name_plural = "Atribuições de Aulas"
        unique_together = ('teacher', 'subject', 'classroom')

    def __str__(self):
        return f"{self.teacher} - {self.subject} ({self.classroom})"

class AcademicPeriod(models.Model):
    name = models.CharField("Nome", max_length=20) # Ex: 1º Bimestre
    start_date = models.DateField("Início")
    end_date = models.DateField("Fim")
    is_active = models.BooleanField("Período Ativo?", default=False) # Só um pode ser True

    class Meta:
        verbose_name = "Período Letivo"
        verbose_name_plural = "Períodos Letivos"
        ordering = ['start_date']

    def __str__(self):
        return self.name

class Grade(models.Model):
    """Lançamento de Notas"""
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, verbose_name="Matrícula")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name="Matéria")
    # Ex: "Prova 1", "Trabalho Bimestral", "Simulado"
    name = models.CharField("Avaliação", max_length=50) 
    # Nota de 0.00 a 10.00
    value = models.DecimalField("Nota", max_digits=4, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(10)])
    weight = models.DecimalField("Peso", max_digits=4, decimal_places=2, default=1.00, validators=[MinValueValidator(0)])
    date = models.DateField("Data da Avaliação", auto_now_add=True)
    period = models.ForeignKey(AcademicPeriod, on_delete=models.PROTECT, verbose_name="Período", null=True, blank=True)

    class Meta:
        verbose_name = "Nota"
        verbose_name_plural = "Notas"
        # Garante que não lance a mesma prova duas vezes pro mesmo aluno (opcional, mas bom)
        # unique_together = ('enrollment', 'subject', 'name') 

    def __str__(self):
        return f"{self.enrollment.student.name} - {self.name}: {self.value}"

class Attendance(models.Model):
    """Lançamento de Frequência (Diário de Classe)"""
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, verbose_name="Matrícula")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name="Matéria")
    date = models.DateField("Data da Aula")
    present = models.BooleanField("Presente", default=True) # True = Presente, False = Falta
    justified = models.BooleanField(default=False, verbose_name="Falta Justificada")
    period = models.ForeignKey(AcademicPeriod, on_delete=models.PROTECT, verbose_name="Período", null=True, blank=True)

    class Meta:
        verbose_name = "Frequência"
        verbose_name_plural = "Frequências"
        # Um aluno só pode ter um registro de presença por matéria no dia
        unique_together = ('enrollment', 'subject', 'date')

    def __str__(self):
        status = "Presente" if self.present else "Faltou"
        return f"{self.date} - {self.enrollment.student.name}: {status}"

class AbsenceJustification(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Em Análise'),
        ('APPROVED', 'Aprovada'),
        ('REJECTED', 'Rejeitada')
    ]

    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name='justification_request')
    reason = models.TextField(verbose_name="Motivo")
    file = models.FileField(upload_to='justifications/%Y/%m/', verbose_name="Atestado/Documento", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    rejection_reason = models.TextField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status == 'APPROVED':
            self.attendance.justified = True
            self.attendance.save()
        elif self.status == 'REJECTED':
            self.attendance.justified = False
            self.attendance.save()
            
        super().save(*args, **kwargs)

class LessonPlan(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Rascunho'),
        ('SUBMITTED', 'Enviado'),
        ('APPROVED', 'Visto da Coordenação'),
        ('RETURNED', 'Precisa de Ajuste')
    ]

    # Vínculo: Quem é o professor, qual matéria e qual turma?
    # Usamos o TeacherAssignment que já amarra tudo isso.
    assignment = models.ForeignKey(TeacherAssignment, on_delete=models.CASCADE, verbose_name="Atribuição")
    
    # Período
    start_date = models.DateField("Início da Semana")
    end_date = models.DateField("Fim da Semana")
    
    # Conteúdo (Usaremos Editor Rico aqui)
    topic = models.CharField("Tema / Tópico Principal", max_length=200)
    description = models.TextField("Desenvolvimento da Aula", blank=True)
    attachment = models.FileField(
        "Anexo (Atividade/Material)", 
        upload_to='lesson_plans/', 
        null=True, 
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'jpg', 'jpeg', 'png'])]
    )
    recipients = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name='received_plans', 
        verbose_name="Enviar para", 
        blank=True
    )
    
    # Fluxo de Aprovação
    status = models.CharField("Status", max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    coordinator_note = models.TextField("Feedback da Coordenação", blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Planejamento Semanal"
        verbose_name_plural = "Planejamentos Semanais"
        ordering = ['-start_date']

    def __str__(self):
        return f"Semana {self.start_date} - {self.assignment}"

class LessonPlanFile(models.Model):
    plan = models.ForeignKey(LessonPlan, related_name='attachments', on_delete=models.CASCADE)
    file = models.FileField(upload_to='lesson_plans/%Y/%m/')
    name = models.CharField(max_length=255, blank=True) # Nome original do arquivo
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or self.file.name

class TaughtContent(models.Model):
    """Registro diário do Conteúdo Ministrado"""
    assignment = models.ForeignKey(TeacherAssignment, on_delete=models.CASCADE, verbose_name="Atribuição")
    date = models.DateField("Data da Aula")
    content = models.TextField("Conteúdo Trabalhado")
    homework = models.TextField("Lição de Casa / Tarefa", blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Conteúdo Ministrado"
        verbose_name_plural = "Conteúdos Ministrados"
        ordering = ['-date']
        # Garante que não haja dois registros para a mesma aula/dia (opcional, mas recomendado)
        unique_together = ('assignment', 'date') 

    def __str__(self):
        return f"{self.date} - {self.assignment}"

class SchoolEvent(models.Model):
    EVENT_TYPES = [
        ('HOLIDAY', 'Feriado / Recesso'),
        ('SCHOOL_DAY', 'Dia Letivo Especial'), # Ex: Sábado letivo
        ('EXAM', 'Prova / Avaliação'),
        ('ASSIGNMENT', 'Entrega de Trabalho'),
        ('EVENT', 'Evento / Festa'),
        ('MEETING', 'Reunião Pedagógica'),
    ]

    TARGET_AUDIENCE = [
        ('ALL', 'Toda a Escola (Público)'),
        ('TEACHERS', 'Apenas Professores/Staff'),
        ('CLASSROOM', 'Turma Específica'),
    ]

    title = models.CharField("Título", max_length=200)
    description = models.TextField("Descrição", blank=True, null=True)
    
    start_time = models.DateTimeField("Início")
    end_time = models.DateTimeField("Fim", blank=True, null=True)
    
    event_type = models.CharField("Tipo de Evento", max_length=20, choices=EVENT_TYPES, default='EVENT')
    target_audience = models.CharField("Público Alvo", max_length=20, choices=TARGET_AUDIENCE, default='ALL')
    
    # Relacionamentos Opcionais
    # Se for PROVA ou TRABALHO para uma turma específica:
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, null=True, blank=True, related_name='events', verbose_name="Turma")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True, related_name='events', verbose_name="Matéria")
    
    # Campo de controle (quem criou)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_events'
    )

    class Meta:
        verbose_name = "Evento / Calendário"
        verbose_name_plural = "Calendário Escolar"
        ordering = ['start_time']

    def __str__(self):
        return f"{self.get_event_type_display()}: {self.title} ({self.start_time.strftime('%d/%m')})"

class ClassSchedule(models.Model):
    # Padrão FullCalendar: 0=Dom, 1=Seg, ..., 6=Sab
    DAYS_OF_WEEK = [
        (1, 'Segunda-feira'),
        (2, 'Terça-feira'),
        (3, 'Quarta-feira'),
        (4, 'Quinta-feira'),
        (5, 'Sexta-feira'),
        (6, 'Sábado'),
        (0, 'Domingo'),
    ]

    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name='schedules')
    assignment = models.ForeignKey(TeacherAssignment, on_delete=models.CASCADE)
    
    day_of_week = models.IntegerField("Dia da Semana", choices=DAYS_OF_WEEK)
    start_time = models.TimeField("Início")
    end_time = models.TimeField("Fim")

    class Meta:
        verbose_name = "Grade Horária"
        verbose_name_plural = "Grades Horárias"
        ordering = ['day_of_week', 'start_time']
        # Evita duplicidade simples (mesma turma, mesmo dia, mesmo horário de início)
        unique_together = ['classroom', 'day_of_week', 'start_time']

    def __str__(self):
        return f"{self.get_day_of_week_display()} - {self.start_time} - {self.assignment.subject.name}"

class AcademicHistory(models.Model):
    STATUS_CHOICES = [
        ('APPROVED', 'Aprovado'),
        ('RETAINED', 'Reprovado/Retido'),
        ('TRANSFERRED', 'Transferido'),
        ('DROPOUT', 'Evadido/Desistente'),
        ('IN_PROGRESS', 'Cursando (Atual)'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='academic_history')
    year = models.IntegerField("Ano Letivo")
    
    # Texto livre pois pode ser uma turma antiga que não existe mais no sistema
    # ou uma turma de outra escola.
    classroom_name = models.CharField("Turma/Série", max_length=100, help_text="Ex: 5º Ano B ou 3ª Série EM")
    
    school_name = models.CharField("Escola", max_length=200, default="Lumis School", help_text="Nome da escola onde cursou")
    
    status = models.CharField("Situação Final", max_length=20, choices=STATUS_CHOICES, default='APPROVED')
    final_grade = models.CharField("Média Final", max_length=10, blank=True, null=True, help_text="Opcional")
    
    observation = models.TextField("Observações", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Registro de Histórico"
        verbose_name_plural = "Histórico Acadêmico"
        ordering = ['-year'] # Do mais recente para o mais antigo

    def __str__(self):
        return f"{self.student.name} - {self.year} - {self.classroom_name}"