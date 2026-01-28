import random
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from faker import Faker
from datetime import date, timedelta

# Importações dos Apps
from apps.academic.models import (
    Segment, ClassRoom, Subject, Student, Enrollment, 
    TeacherAssignment, Grade, AcademicPeriod, Guardian, 
    LessonPlan, Attendance
)
from apps.coordination.models import (
    WeeklyReport, ClassObservation, MeetingMinute, StudentReport
)

User = get_user_model()

class Command(BaseCommand):
    help = 'Popula o banco de dados com dados reais de teste para o Projeto Lumis'

    def handle(self, *args, **kwargs):
        fake = Faker('pt_BR')
        self.stdout.write(self.style.WARNING('🚀 Iniciando Data Seeding Completo...'))

        with transaction.atomic():
            # 1. Limpeza Profunda
            self.stdout.write('🧹 Limpando tabelas...')
            models_to_clear = [
                StudentReport, MeetingMinute, ClassObservation, WeeklyReport,
                LessonPlan, Attendance, Grade, TeacherAssignment, Enrollment,
                Student, Guardian, ClassRoom, Subject, Segment, AcademicPeriod
            ]
            for model in models_to_clear:
                model.objects.all().delete()
            
            User.objects.filter(is_superuser=False).delete()

            # 2. Grupos de Acesso
            self.stdout.write('👥 Criando Grupos...')
            group_prof = Group.objects.get_or_create(name='Professores')[0]
            group_coord = Group.objects.get_or_create(name='Coordenacao')[0]
            group_parents = Group.objects.get_or_create(name='Responsaveis')[0]

            # 3. Estrutura de Tempo (Bimestres)
            self.stdout.write('📅 Criando Calendário...')
            periods = [
                AcademicPeriod.objects.create(name='1º Bimestre', start_date=date(2025, 2, 3), end_date=date(2025, 4, 18), is_active=False),
                AcademicPeriod.objects.create(name='2º Bimestre', start_date=date(2025, 4, 21), end_date=date(2025, 7, 4), is_active=False),
                AcademicPeriod.objects.create(name='3º Bimestre', start_date=date(2025, 7, 28), end_date=date(2025, 10, 3), is_active=False),
                AcademicPeriod.objects.create(name='4º Bimestre', start_date=date(2025, 10, 6), end_date=date(2025, 12, 19), is_active=True),
            ]

            # 4. Estrutura Acadêmica
            segments = [Segment.objects.create(name=s) for s in ['Educação Infantil', 'Ensino Fundamental I', 'Ensino Fundamental II']]
            subjects = [Subject.objects.create(name=s) for s in ['Matemática', 'Português', 'Artes', 'Inglês', 'História', 'Ciências']]

            # 5. Staff (Coordenadores e Professores)
            self.stdout.write('🧑‍🏫 Criando Staff...')
            
            # Coordenadora Principal
            coord_user = User.objects.create_user(username='livia.coord', email='livia@saintthomas.com', password='123', is_coordinator=True)
            coord_user.groups.add(group_coord)
            
            # 5 Professores
            teachers = []
            for i in range(5):
                name = fake.name()
                user = User.objects.create_user(
                    username=f'teacher{i+1}', 
                    email=fake.email(), 
                    password='123',
                    first_name=name.split()[0],
                    is_teacher=True
                )
                user.groups.add(group_prof)
                teachers.append(user)

            # 6. Turmas e Atribuições
            self.stdout.write('🏫 Criando Turmas e Aulas...')
            classrooms = []
            for s in segments:
                for grade in range(1, 3):
                    cr = ClassRoom.objects.create(name=f'{grade}º Ano {s.name[:3]}', segment=s, year=2025)
                    classrooms.append(cr)
                    
                    # Atribui 3 matérias por turma
                    sampled_subjects = random.sample(subjects, 3)
                    for sub in sampled_subjects:
                        TeacherAssignment.objects.create(
                            teacher=random.choice(teachers),
                            subject=sub,
                            classroom=cr
                        )

            # 7. Alunos e Responsáveis
            self.stdout.write('👨‍👩‍👧‍👦 Matriculando Alunos...')
            all_enrollments = []
            for i in range(30):
                # Aluno
                student = Student.objects.create(
                    name=fake.name(),
                    registration_number=f"2025{i:04d}",
                    birth_date=fake.date_of_birth(minimum_age=5, maximum_age=15),
                    cpf=fake.cpf(),
                    city="Mogi das Cruzes",
                    state="SP",
                    allergies=random.choice(["Nenhuma", "Ametista", "Glúten", "Lactose"]),
                    emergency_contact=f"{fake.name()} - {fake.phone_number()}"
                )
                
                # Responsável (Pai/Mãe)
                guardian_name = fake.name()
                guardian_cpf = fake.cpf()
                u_guardian = User.objects.create_user(
                    username=guardian_cpf.replace('.', '').replace('-', ''),
                    password='123',
                    first_name=guardian_name.split()[0]
                )
                u_guardian.groups.add(group_parents)
                
                guardian = Guardian.objects.create(
                    user=u_guardian,
                    name=guardian_name,
                    cpf=guardian_cpf,
                    phone=fake.phone_number(),
                    email=u_guardian.email
                )
                student.guardians.add(guardian)
                
                # Matrícula
                enr = Enrollment.objects.create(student=student, classroom=random.choice(classrooms))
                all_enrollments.append(enr)

            # 8. Dados Dinâmicos (Notas e Frequência)
            self.stdout.write('📊 Lançando Notas e Presenças...')
            for enr in all_enrollments:
                assignments = TeacherAssignment.objects.filter(classroom=enr.classroom)
                for assign in assignments:
                    # Notas para 2 bimestres
                    for p in periods[:2]:
                        Grade.objects.create(
                            enrollment=enr, subject=assign.subject, period=p,
                            name='Avaliação Mensal', value=random.uniform(6, 10)
                        )
                    
                    # Frequência (últimos 5 dias)
                    for d in range(5):
                        Attendance.objects.create(
                            enrollment=enr,
                            subject=assign.subject,
                            date=date.today() - timedelta(days=d),
                            present=random.choice([True, True, True, False]), # Mais presenças que faltas
                            period=periods[3]
                        )

            # 9. Coordenação e Pedagógico (O QUE FALTAVA)
            self.stdout.write('📝 Gerando Relatórios Pedagógicos...')
            
            # Planejamentos de Aula
            for assign in TeacherAssignment.objects.all():
                LessonPlan.objects.create(
                    assignment=assign,
                    start_date=date.today(),
                    end_date=date.today() + timedelta(days=4),
                    topic="Conteúdo Programático da Semana",
                    description=fake.paragraph(nb_sentences=5),
                    status=random.choice(['APPROVED', 'SUBMITTED', 'DRAFT'])
                )

            # Relatórios Semanais da Coordenação
            for i in range(3):
                WeeklyReport.objects.create(
                    author=coord_user,
                    start_date=date.today() - timedelta(weeks=i),
                    end_date=date.today() - timedelta(weeks=i) + timedelta(days=4),
                    description=f"Semana produtiva. Foco na {fake.word()}.",
                    pending_issues="Nenhuma pendência crítica."
                )

            # Observações de Sala
            for teacher in teachers:
                ClassObservation.objects.create(
                    coordinator=coord_user,
                    assignment=TeacherAssignment.objects.filter(teacher=teacher).first(),
                    date=date.today() - timedelta(days=random.randint(1,10)),
                    strong_points="Ótima didática e controle de turma.",
                    points_to_improve="Utilizar mais recursos tecnológicos."
                )

            # Atas de Reunião
            MeetingMinute.objects.create(
                title="Conselho de Classe 3º Bimestre",
                date=date.today() - timedelta(days=15),
                participants="Livia, Professores do Fundamental",
                content="Discussão sobre o desempenho geral dos alunos.",
                created_by=coord_user
            )

            # Relatórios Individuais de Alunos (StudentReport)
            for enr in random.sample(all_enrollments, 10):
                StudentReport.objects.create(
                    student=enr.student,
                    teacher=random.choice(teachers),
                    date=date.today(),
                    subject="Relatório de Comportamento",
                    content=fake.text(),
                    status='APPROVED',
                    visible_to_family=True
                )

        self.stdout.write(self.style.SUCCESS('✅ Sistema Lumis populado com sucesso em todos os módulos!'))