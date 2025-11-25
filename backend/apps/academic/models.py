from django.db import models
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

class Student(models.Model):
    name = models.CharField("Nome Completo", max_length=200)
    registration_number = models.CharField("Matrícula", max_length=20, unique=True)
    birth_date = models.DateField("Data de Nascimento", null=True, blank=True)
    # Podemos adicionar foto, nome dos pais, etc. depois
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Aluno"
        verbose_name_plural = "Alunos"

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
    """Vincula Professor -> Matéria -> Turma (Quem dá aula do quê e onde)"""
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        verbose_name="Professor",
        limit_choices_to={'is_teacher': True} # Só mostra usuários marcados como professor
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name="Matéria")
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, verbose_name="Turma")

    class Meta:
        verbose_name = "Atribuição de Aula"
        verbose_name_plural = "Atribuições de Aulas"
        unique_together = ('teacher', 'subject', 'classroom')

    def __str__(self):
        return f"{self.teacher} - {self.subject} ({self.classroom})"

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

    class Meta:
        verbose_name = "Frequência"
        verbose_name_plural = "Frequências"
        # Um aluno só pode ter um registro de presença por matéria no dia
        unique_together = ('enrollment', 'subject', 'date')

    def __str__(self):
        status = "Presente" if self.present else "Faltou"
        return f"{self.date} - {self.enrollment.student.name}: {status}"