from django.db import models
from django.conf import settings
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
    name = models.CharField("Nome Completo", max_length=150)
    cpf = models.CharField("CPF", max_length=14, unique=True) 
    rg = models.CharField("RG", max_length=20, blank=True, null=True)
    email = models.EmailField("Email", blank=True, null=True) 
    phone = models.CharField("Celular/WhatsApp", max_length=20)
    profession = models.CharField("Profissão", max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Responsável"
        verbose_name_plural = "Responsáveis"

    def __str__(self):
        return self.name

class Student(models.Model):
    # Identificação Básica
    name = models.CharField("Nome Completo", max_length=150)
    registration_number = models.CharField("Matrícula", max_length=20, unique=True)
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

    # Dados de Saúde/Emergência
    allergies = models.TextField("Alergias", blank=True)
    medications = models.TextField("Uso Contínuo de Medicamentos", blank=True)
    emergency_contact = models.CharField("Contato de Emergência (Nome/Tel)", max_length=100, blank=True)

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
    period = models.ForeignKey(AcademicPeriod, on_delete=models.PROTECT, verbose_name="Período", null=True, blank=True)

    class Meta:
        verbose_name = "Frequência"
        verbose_name_plural = "Frequências"
        # Um aluno só pode ter um registro de presença por matéria no dia
        unique_together = ('enrollment', 'subject', 'date')

    def __str__(self):
        status = "Presente" if self.present else "Faltou"
        return f"{self.date} - {self.enrollment.student.name}: {status}"

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
    resources = models.TextField("Recursos Didáticos", blank=True)
    homework = models.TextField("Lição de Casa / Fixação", blank=True)
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