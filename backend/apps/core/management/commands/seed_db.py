import random
from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker
from apps.core.models import User
from apps.academic.models import Segment, ClassRoom, Subject, Student, Enrollment, TeacherAssignment

class Command(BaseCommand):
    help = 'Popula o banco de dados com dados de teste (Fake)'

    def handle(self, *args, **kwargs):
        fake = Faker('pt_BR') # Nomes em Português
        self.stdout.write(self.style.WARNING('Iniciando o Data Seeding...'))

        # Bloco atômico: ou faz tudo, ou não faz nada (segurança)
        with transaction.atomic():
            # 1. Limpeza (Opcional - CUIDADO EM PRODUÇÃO)
            self.stdout.write('Limpando dados antigos...')
            Enrollment.objects.all().delete()
            TeacherAssignment.objects.all().delete()
            ClassRoom.objects.all().delete()
            Student.objects.all().delete()
            Subject.objects.all().delete()
            Segment.objects.all().delete()
            # Removemos apenas usuários que são professores fake, mantemos o admin
            User.objects.filter(is_teacher=True).delete()

            # 2. Criar Segmentos
            self.stdout.write('Criando Segmentos...')
            segments_list = ['Educação Infantil', 'Fundamental I', 'Fundamental II', 'Ensino Médio']
            segments_objs = [Segment(name=s) for s in segments_list]
            Segment.objects.bulk_create(segments_objs)
            
            # Recupera do banco para ter os IDs
            seg_infantil = Segment.objects.get(name='Educação Infantil')
            seg_fund1 = Segment.objects.get(name='Fundamental I')
            seg_fund2 = Segment.objects.get(name='Fundamental II')
            seg_medio = Segment.objects.get(name='Ensino Médio')

            # 3. Criar Matérias
            self.stdout.write('Criando Matérias...')
            subjects_names = ['Matemática', 'Português', 'História', 'Geografia', 'Ciências', 'Inglês', 'Artes', 'Educação Física']
            subjects_objs = [Subject(name=s) for s in subjects_names]
            Subject.objects.bulk_create(subjects_objs)
            all_subjects = list(Subject.objects.all())

            # 4. Criar Professores (Users)
            self.stdout.write('Criando Professores...')
            teachers = []
            for _ in range(5):
                name = fake.name()
                username = name.lower().replace(' ', '.')
                email = f"{username}@saintthomas.com"
                user = User.objects.create_user(username=username, email=email, password='123', is_teacher=True)
                user.first_name = name.split()[0]
                user.last_name = ' '.join(name.split()[1:])
                user.save()
                teachers.append(user)

            # 5. Criar Turmas
            self.stdout.write('Criando Turmas...')
            classrooms = []
            # Infantil
            classrooms.append(ClassRoom(name='Jardim I', segment=seg_infantil, year=2025))
            classrooms.append(ClassRoom(name='Jardim II', segment=seg_infantil, year=2025))
            # Fund 1
            classrooms.append(ClassRoom(name='1º Ano A', segment=seg_fund1, year=2025))
            classrooms.append(ClassRoom(name='3º Ano B', segment=seg_fund1, year=2025))
            # Fund 2
            classrooms.append(ClassRoom(name='6º Ano A', segment=seg_fund2, year=2025))
            classrooms.append(ClassRoom(name='8º Ano C', segment=seg_fund2, year=2025))
            # Médio
            classrooms.append(ClassRoom(name='1º Série A', segment=seg_medio, year=2025))
            classrooms.append(ClassRoom(name='3º Série B', segment=seg_medio, year=2025))
            
            ClassRoom.objects.bulk_create(classrooms)
            all_classes = list(ClassRoom.objects.all())

            # 6. Criar Alunos e Matrículas
            self.stdout.write('Matriculando Alunos...')
            for _ in range(50): # 50 Alunos
                student = Student.objects.create(
                    name=fake.name(),
                    registration_number=str(fake.unique.random_number(digits=6)),
                    birth_date=fake.date_of_birth(minimum_age=4, maximum_age=17)
                )
                # Matricula o aluno em uma turma aleatória
                random_class = random.choice(all_classes)
                Enrollment.objects.create(student=student, classroom=random_class)

            # 7. Atribuir Aulas (Professor -> Matéria -> Turma)
            self.stdout.write('Atribuindo Aulas...')
            for classroom in all_classes:
                # Para cada turma, adiciona 3 matérias aleatórias com professores aleatórios
                selected_subjects = random.sample(all_subjects, 3)
                for subject in selected_subjects:
                    teacher = random.choice(teachers)
                    TeacherAssignment.objects.create(
                        teacher=teacher,
                        subject=subject,
                        classroom=classroom
                    )

        self.stdout.write(self.style.SUCCESS('✅ Banco de dados populado com sucesso!'))