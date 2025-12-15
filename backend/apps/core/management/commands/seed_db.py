import random
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth.models import Group # Importa apenas Group daqui
from django.contrib.auth import get_user_model # O JEITO CERTO de pegar o User
from faker import Faker
from apps.academic.models import (
    Segment, ClassRoom, Subject, Student, Enrollment, 
    TeacherAssignment, Grade, AcademicPeriod, Guardian, LessonPlan
)
from datetime import date, timedelta

# Pega a classe de usuário ativa no projeto (core.User)
User = get_user_model()

class Command(BaseCommand):
    help = 'Popula o banco de dados com dados de teste (Fake)'

    def handle(self, *args, **kwargs):
        fake = Faker('pt_BR')
        self.stdout.write(self.style.WARNING('Iniciando o Data Seeding...'))

        with transaction.atomic():
            # 1. Limpeza
            self.stdout.write('Limpando dados antigos...')
            LessonPlan.objects.all().delete()
            Grade.objects.all().delete()
            TeacherAssignment.objects.all().delete()
            Enrollment.objects.all().delete()
            Student.objects.all().delete()
            Guardian.objects.all().delete()
            ClassRoom.objects.all().delete()
            Subject.objects.all().delete()
            Segment.objects.all().delete()
            AcademicPeriod.objects.all().delete()
            
            # Limpa usuários que não são superusers
            User.objects.filter(is_superuser=False).delete()

            # 2. Criar Grupos (Essencial para a nova lógica)
            self.stdout.write('Criando Grupos...')
            group_prof, _ = Group.objects.get_or_create(name='Professores')
            group_coord, _ = Group.objects.get_or_create(name='Coordenacao')
            group_parents, _ = Group.objects.get_or_create(name='Responsaveis')

            # 3. Criar Períodos
            self.stdout.write('Criando Bimestres...')
            p1 = AcademicPeriod.objects.create(name='1º Bimestre', start_date=date(2025, 2, 1), end_date=date(2025, 4, 30), is_active=False)
            p2 = AcademicPeriod.objects.create(name='2º Bimestre', start_date=date(2025, 5, 1), end_date=date(2025, 7, 15), is_active=False)
            p3 = AcademicPeriod.objects.create(name='3º Bimestre', start_date=date(2025, 8, 1), end_date=date(2025, 9, 30), is_active=False)
            p4 = AcademicPeriod.objects.create(name='4º Bimestre', start_date=date(2025, 10, 1), end_date=date(2025, 12, 15), is_active=True)
            all_periods = [p1, p2, p3, p4]

            # 4. Criar Segmentos e Matérias
            self.stdout.write('Criando Estrutura Acadêmica...')
            segments_list = ['Educação Infantil', 'Fundamental I', 'Fundamental II', 'Ensino Médio']
            segments_objs = [Segment.objects.create(name=s) for s in segments_list]
            
            subjects_names = ['Matemática', 'Português', 'História', 'Geografia', 'Ciências', 'Inglês', 'Artes', 'Educação Física']
            all_subjects = [Subject.objects.create(name=s) for s in subjects_names]

            # 5. Criar Professores e Coordenadores (Com Grupos!)
            self.stdout.write('Criando Staff...')
            teachers = []
            
            # 5 Professores
            for _ in range(5):
                name = fake.name()
                username = name.split()[0].lower() + str(random.randint(1,99))
                email = f"{username}@saintthomas.com"
                user = User.objects.create_user(username=username, email=email, password='123')
                user.first_name = name.split()[0]
                user.last_name = ' '.join(name.split()[1:])
                user.groups.add(group_prof) # Adiciona ao grupo
                user.save()
                teachers.append(user)

            # 1 Coordenadora
            # Verifica se já existe para não dar erro de unique
            if not User.objects.filter(username='livia.coord').exists():
                coord = User.objects.create_user(username='livia.coord', email='livia@saintthomas.com', password='123')
                coord.first_name = 'Livia'
                coord.last_name = 'Coordenadora'
                coord.groups.add(group_coord)
                coord.save()

            # 6. Criar Turmas
            self.stdout.write('Criando Turmas...')
            classrooms = []
            classrooms.append(ClassRoom.objects.create(name='Jardim II', segment=segments_objs[0], year=2025))
            classrooms.append(ClassRoom.objects.create(name='1º Ano A', segment=segments_objs[1], year=2025))
            classrooms.append(ClassRoom.objects.create(name='6º Ano A', segment=segments_objs[2], year=2025))
            classrooms.append(ClassRoom.objects.create(name='3º Série B', segment=segments_objs[3], year=2025))
            
            # 7. Criar Alunos e Responsáveis
            self.stdout.write('Matriculando Alunos e Criando Pais...')
            for _ in range(40):
                # Cria Aluno com dados completos
                student = Student.objects.create(
                    name=fake.name(),
                    registration_number=str(fake.unique.random_number(digits=6)),
                    birth_date=fake.date_of_birth(minimum_age=4, maximum_age=17),
                    cpf=fake.cpf(),
                    street=fake.street_name(),
                    neighborhood=fake.bairro(),
                    city=fake.city(),
                    state=fake.state_abbr()
                )
                
                # --- LÓGICA NOVA PARA O PAI ---
                guardian_name = fake.name()
                guardian_cpf = fake.cpf()
                guardian_email = fake.email()
                
                # 1. Cria o Usuário de Login (Username = CPF limpo)
                cpf_limpo = guardian_cpf.replace('.', '').replace('-', '')
                
                # Verifica se user já existe para evitar erro em loops
                if not User.objects.filter(username=cpf_limpo).exists():
                    user_parent = User.objects.create_user(
                        username=cpf_limpo,
                        email=guardian_email,
                        password='123'
                    )
                    user_parent.first_name = guardian_name.split()[0]
                    user_parent.groups.add(group_parents)
                    user_parent.save()

                    # 2. Cria o Perfil Guardian vinculado
                    guardian = Guardian.objects.create(
                        user=user_parent, # Vínculo feito!
                        name=guardian_name,
                        cpf=guardian_cpf,
                        phone=fake.phone_number(),
                        email=guardian_email
                    )
                    student.guardians.add(guardian)

                # Matricula
                random_class = random.choice(classrooms)
                Enrollment.objects.create(student=student, classroom=random_class)

            # 8. Atribuições e Planejamentos
            self.stdout.write('Gerando Atribuições e Planejamentos...')
            for classroom in classrooms:
                selected_subjects = random.sample(all_subjects, 3)
                for subject in selected_subjects:
                    teacher = random.choice(teachers)
                    assignment = TeacherAssignment.objects.create(
                        teacher=teacher,
                        subject=subject,
                        classroom=classroom
                    )

                    # Cria 2 Planejamentos para cada atribuição
                    LessonPlan.objects.create(
                        assignment=assignment,
                        start_date=date.today(),
                        end_date=date.today() + timedelta(days=4),
                        topic=f"Introdução a {subject.name}",
                        description=f"Conteúdo de teste para {subject.name}...",
                        status='SUBMITTED'
                    )

            # 9. Notas Fakes
            self.stdout.write('Lançando Notas...')
            for enroll in Enrollment.objects.all():
                # Pega as atribuições da turma desse aluno
                assignments = TeacherAssignment.objects.filter(classroom=enroll.classroom)
                for assign in assignments:
                    # Lança nota no 1º Bimestre
                    Grade.objects.create(
                        enrollment=enroll,
                        subject=assign.subject,
                        period=p1,
                        name='Prova P1',
                        value=random.uniform(5.0, 10.0),
                        weight=1
                    )

        self.stdout.write(self.style.SUCCESS('✅ Banco de dados populado com sucesso (V2)!'))