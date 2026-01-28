from rest_framework import viewsets, permissions, filters
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Avg, Q
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
User = get_user_model()
from .models import Segment, ClassRoom, Guardian, Student, Enrollment, Subject, TeacherAssignment, Grade, Attendance, AcademicPeriod, LessonPlan, AbsenceJustification, ExtraActivity
from .serializers import (
    SegmentSerializer, ClassRoomSerializer, StudentSerializer, 
    EnrollmentSerializer, SubjectSerializer, TeacherAssignmentSerializer,
    GradeSerializer, AttendanceSerializer, AcademicPeriodSerializer,
    GuardianSerializer, LessonPlanSerializer, SimpleUserSerializer, ParentStudentSerializer,
    GuardianProfileUpdateSerializer, StudentHealthUpdateSerializer, AbsenceJustificationSerializer,
    ExtraActivitySerializer
)
from .permissions import IsGuardianOwner, IsGuardianOfStudent

class FlexiblePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size' # Habilita ?page_size=1000
    max_page_size = 5000

class SegmentViewSet(viewsets.ModelViewSet):
    queryset = Segment.objects.all()
    serializer_class = SegmentSerializer

class ClassRoomViewSet(viewsets.ModelViewSet):
    queryset = ClassRoom.objects.all()
    serializer_class = ClassRoomSerializer

class GuardianViewSet(viewsets.ModelViewSet):
    queryset = Guardian.objects.all().order_by('name')
    serializer_class = GuardianSerializer
    pagination_class = FlexiblePagination
    permission_classes = [permissions.IsAuthenticated, IsGuardianOwner]
    search_fields = ['name', 'cpf', 'email']

    def get_serializer_class(self):
        # Se for PUT/PATCH, usa o serializer restrito (só contato)
        if self.action in ['update', 'partial_update']:
            return GuardianProfileUpdateSerializer
        return GuardianSerializer

    # Action para pegar o perfil "Meu Perfil" sem precisar saber o ID
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        if hasattr(request.user, 'guardian_profile'):
            serializer = self.get_serializer(request.user.guardian_profile)
            return Response(serializer.data)
        return Response({"detail": "Perfil não encontrado"}, status=404)

class ExtraActivityViewSet(viewsets.ModelViewSet):
    queryset = ExtraActivity.objects.all()
    serializer_class = ExtraActivitySerializer

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all().order_by('name')
    serializer_class = StudentSerializer
    pagination_class = FlexiblePagination
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['name', 'registration_number', 'cpf']
    filterset_fields = ['period', 'is_full_time']

    def get_permissions(self):
        # Se for editar, exige ser o responsável do aluno
        if self.action in ['update', 'partial_update']:
            return [permissions.IsAuthenticated(), IsGuardianOfStudent()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        # Se for o Pai editando, usa o serializer de Saúde
        if self.action in ['update', 'partial_update']:
            user = self.request.user
            # Se não for staff (admin/coordenação), assume que é Pai
            if not user.is_staff and not user.is_superuser:
                return StudentHealthUpdateSerializer
        return StudentSerializer

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='my-children')
    def my_children(self, request):
        user = request.user
        
        # 1. Verifica se o usuário tem perfil de Responsável
        if not hasattr(user, 'guardian_profile'):
            return Response({"detail": "Usuário não é um responsável vinculado."}, status=403)
            
        # 2. Pega o perfil de Guardian desse usuário
        guardian_profile = user.guardian_profile
        
        # 3. Busca os alunos onde este responsável está na lista de 'guardians'
        # CORREÇÃO: Usamos o filtro direto no Modelo Student, é mais seguro.
        my_kids = Student.objects.filter(guardians=guardian_profile)
        
        # 4. Serializa e retorna
        serializer = ParentStudentSerializer(my_kids, many=True)
        return Response(serializer.data)

    # --- BOLETIM (Notas Agrupadas) ---
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated], url_path='report-card')
    def report_card(self, request, pk=None):
        # 1. Segurança: Verifica se o aluno pertence ao Pai logado
        user = request.user
        if not hasattr(user, 'guardian_profile'):
             return Response({"detail": "Acesso negado."}, status=403)
        
        guardian = user.guardian_profile
        student = self.get_object()
        
        if not student.guardians.filter(id=guardian.id).exists():
            return Response({"detail": "Este aluno não está vinculado a você."}, status=403)

        # 2. Busca Notas e Matrícula
        enrollment = student.enrollment_set.last()
        if not enrollment:
            return Response([])

        grades = Grade.objects.filter(enrollment=enrollment)
        
        # 3. Pivot: Organiza por Matéria
        report = {}

        subjects = Subject.objects.filter(teacherassignment__classroom=enrollment.classroom).distinct()

        for subj in subjects:
            report[subj.name] = {"1": "-", "2": "-", "3": "-", "4": "-", "final": "-"}

        # 4. Preenche Notas
        for g in grades:
            subj_name = None
            
            # Tenta Caminho 1: Ligação direta Grade -> Subject
            if hasattr(g, 'subject') and g.subject:
                subj_name = g.subject.name
            # Tenta Caminho 2: Grade -> Assignment -> Subject
            elif hasattr(g, 'assignment') and g.assignment and hasattr(g.assignment, 'subject') and g.assignment.subject:
                subj_name = g.assignment.subject.name
            
            if not subj_name:
                continue

            # Se a matéria não estava na lista (ex: nota lançada sem atribuição vigente), adiciona
            if subj_name not in report:
                report[subj_name] = {"1": "-", "2": "-", "3": "-", "4": "-", "final": "-"}

            # Lógica de Período (Bimestre)
            if g.period:
                # Pega "1" de "1º Bimestre"
                term_key = str(g.period.name)[0]
                if term_key in report[subj_name]:
                    report[subj_name][term_key] = g.value

        # 5. Formata para Lista
        data = []
        for subject, grades_dict in report.items():
            row = {"subject": subject}
            row.update(grades_dict)
            data.append(row)
            
        return Response(data)

    # --- RELATÓRIO DE FALTAS ---
    @action(detail=True, methods=['get'], url_path='attendance-report')
    def attendance_report(self, request, pk=None):
        student = self.get_object()
        
        # Filtra todas as faltas
        attendances = Attendance.objects.filter(
            enrollment__student=student, 
            present=False
        ).select_related('subject').order_by('-date')

        # --- NOVA LÓGICA DE RESUMO (SUMMARY) ---
        summary_data = []
        subjects = attendances.values('subject__name').annotate(
            total=Count('id'),
            # Conta quantas foram justificadas
            justified_count=Count('id', filter=Q(justified=True)) 
        )

        for s in subjects:
            sub_name = s['subject__name'] or 'Geral'
            summary_data.append({
                'subject': sub_name,
                'count': s['total'],
                'justified': s['justified_count'], # Novo campo
                'effective': s['total'] - s['justified_count'] # Faltas "Reais"
            })
        
        # --- NOVA LÓGICA DE HISTÓRICO ---
        history = []
        for att in attendances:
            last_request = att.justification_request.last()
            
            # Monta a URL completa do arquivo se existir
            file_url = None
            if last_request and last_request.file:
                file_url = request.build_absolute_uri(last_request.file.url)

            history.append({
                'id': att.id,
                'date': att.date,
                'subject': att.subject.name if att.subject else 'Geral',
                'justified': att.justified,
                'justification_status': last_request.status if last_request else None,
                'rejection_reason': last_request.rejection_reason if last_request else None, # Motivo da recusa
                'file_url': file_url, # Link do anexo
                'reason_text': last_request.reason if last_request else None
            })

        return Response({
            'summary': summary_data,
            'history': history
        })

class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.all().order_by('student__name')
    serializer_class = EnrollmentSerializer
    filterset_fields = ['classroom', 'student']
    
    # 3. Adicione esta linha para forçar o uso da nossa paginação
    pagination_class = FlexiblePagination

class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all().order_by('name')
    serializer_class = SubjectSerializer
    search_fields = ['name']

class TeacherAssignmentViewSet(viewsets.ModelViewSet):
    queryset = TeacherAssignment.objects.all().order_by('classroom', 'subject')
    serializer_class = TeacherAssignmentSerializer
    
    # Filtros exatos (Dropdowns)
    filterset_fields = ['teacher', 'classroom', 'subject']
    
    # Busca textual (Barra de Pesquisa)
    # Note que usamos __ para acessar campos de tabelas relacionadas
    search_fields = [
        'teacher__first_name', 
        'teacher__username', 
        'subject__name', 
        'classroom__name'
    ]

    def get_queryset(self):
        user = self.request.user
        queryset = TeacherAssignment.objects.all()

        # Se for Superusuário ou Coordenador (Via Grupo!), vê tudo
        if user.is_superuser or user.groups.filter(name='Coordenacao').exists():
            return queryset
        
        # Se for Professor, só vê as SUAS
        return queryset.filter(teacher=user)

    @action(detail=False, methods=['get'])
    def my_classes(self, request):
        user = request.user
        my_assignments = TeacherAssignment.objects.filter(teacher=user).annotate(
            unread_count=Count(
                'classobservation',
                filter=Q(classobservation__is_read=False, classobservation__feedback_given=True)
            )
        ).order_by('classroom__name')
        serializer = self.get_serializer(my_assignments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_students_options(self, request):
        user = request.user
        
        # Busca todas as atribuições do professor (Ex: Matemática no 6º A, Física no 3º B)
        assignments = TeacherAssignment.objects.filter(teacher=user).select_related('classroom', 'subject')
        
        options = []
        
        for assign in assignments:
            # Para cada atribuição, busca os alunos matriculados naquela turma
            enrollments = Enrollment.objects.filter(classroom=assign.classroom).select_related('student').order_by('student__name')
            
            for enroll in enrollments:
                options.append({
                    'student_id': enroll.student.id,
                    'student_name': enroll.student.name,
                    'classroom_name': assign.classroom.name,
                    'subject_name': assign.subject.name,
                    # Label formatada: "Nome do Aluno - Turma (Matéria)"
                    'label': f"{enroll.student.name} - {assign.classroom.name} ({assign.subject.name})"
                })
        
        return Response(options)

class GradeViewSet(viewsets.ModelViewSet):
    queryset = Grade.objects.all().order_by('date')
    serializer_class = GradeSerializer
    filterset_fields = ['enrollment', 'subject', 'enrollment__classroom', 'period']

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all().order_by('date')
    serializer_class = AttendanceSerializer
    filterset_fields = ['enrollment', 'subject', 'date', 'period']

    @action(detail=False, methods=['post'])
    def bulk_save(self, request):
        """
        Recebe uma lista de frequências e salva todas de uma vez.
        Esperado: {
            "subject": 1,
            "date": "2025-02-20",
            "records": [
                {"enrollment_id": 10, "present": true},
                {"enrollment_id": 11, "present": false}
            ]
        }
        """
        data = request.data
        subject_id = data.get('subject')
        date = data.get('date')
        records = data.get('records', [])

        if not subject_id or not date:
            return Response({"error": "Matéria e Data são obrigatórios"}, status=400)

        # Transaction Atomic: Ou salva tudo, ou não salva nada (segurança)
        with transaction.atomic():
            created_count = 0
            updated_count = 0
            
            for item in records:
                # update_or_create: Se já lançou chamada nesse dia, atualiza. Se não, cria.
                obj, created = Attendance.objects.update_or_create(
                    enrollment_id=item['enrollment_id'],
                    subject_id=subject_id,
                    date=date,
                    defaults={'present': item['present']}
                )
                if created: created_count += 1
                else: updated_count += 1

        return Response({
            "message": "Chamada realizada com sucesso!",
            "created": created_count,
            "updated": updated_count
        })

class AcademicPeriodViewSet(viewsets.ModelViewSet):
    queryset = AcademicPeriod.objects.all().order_by('start_date') 
    serializer_class = AcademicPeriodSerializer
    search_fields = ['name']

class DashboardDataView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {}

        # Lógica para definir "Aluno em Risco" (Ex: > 5 faltas)
        # Nota: Ajuste esse número conforme a regra da escola
        risk_threshold = 5

        # === PERFIL COORDENAÇÃO (ou Superuser) ===
        if user.is_superuser or user.groups.filter(name='Coordenacao').exists():
            # 1. Cards
            total_students = Student.objects.count()
            total_classes = ClassRoom.objects.count()
            total_teachers = User.objects.filter(groups__name='Professores').count()
            
            # Risco: Alunos com muitas faltas
            risk_students = Student.objects.annotate(
                absences=Count('enrollment__attendance', filter=Q(enrollment__attendance__present=False))
            ).filter(absences__gt=risk_threshold).count()

            # 2. Charts
            # Distribuição por Segmento
            students_by_segment = Student.objects.values('enrollment__classroom__segment__name').annotate(total=Count('id')).order_by('total')
            
            # Desempenho por Matéria (Média geral da escola)
            avg_by_subject = Grade.objects.values('subject__name').annotate(avg=Avg('value')).order_by('-avg')[:5]
            
            # Alunos por Turma
            students_per_class = ClassRoom.objects.annotate(total=Count('enrollment')).values('name', 'total').order_by('name')

            data = {
                'role': 'coordinator',
                'cards': {
                    'students': total_students,
                    'classes': total_classes,
                    'teachers': total_teachers,
                    'risk': risk_students
                },
                'charts': {
                    'segment_distribution': list(students_by_segment),
                    'subject_performance': list(avg_by_subject),
                    'students_per_class': list(students_per_class)
                }
            }

        # === PERFIL PROFESSOR ===
        else:
            # Filtra turmas onde o professor dá aula
            my_classrooms = ClassRoom.objects.filter(teacherassignment__teacher=user).distinct()
            
            # 1. Cards
            # Alunos (distintos) que estudam nas turmas desse professor
            total_students = Student.objects.filter(enrollment__classroom__in=my_classrooms).distinct().count()
            active_classes_count = my_classrooms.count()
            
            # Matérias que ele leciona
            my_subjects_count = Subject.objects.filter(teacherassignment__teacher=user).distinct().count()

            # Risco (Apenas alunos das minhas turmas)
            risk_students = Student.objects.filter(enrollment__classroom__in=my_classrooms).annotate(
                absences=Count('enrollment__attendance', filter=Q(enrollment__attendance__present=False))
            ).filter(absences__gt=risk_threshold).distinct().count()

            # 2. Charts
            # Desempenho nas MINHAS matérias
            avg_by_subject = Grade.objects.filter(
                enrollment__classroom__in=my_classrooms
            ).values('subject__name').annotate(avg=Avg('value')).order_by('-avg')[:5]

            # Alunos por Turma (apenas minhas turmas)
            students_per_class = my_classrooms.annotate(total=Count('enrollment')).values('name', 'total').order_by('name')

            data = {
                'role': 'teacher',
                'cards': {
                    'students': total_students,
                    'classes': active_classes_count,
                    'subjects': my_subjects_count,
                    'risk': risk_students
                },
                'charts': {
                    'subject_performance': list(avg_by_subject),
                    'students_per_class': list(students_per_class)
                }
            }

        return Response(data)

class LessonPlanViewSet(viewsets.ModelViewSet):
    serializer_class = LessonPlanSerializer
    filterset_fields = ['assignment', 'status', 'start_date', 'assignment__teacher']
    
    def get_queryset(self):
        user = self.request.user
        queryset = LessonPlan.objects.all().order_by('-start_date')
        
        # Se for Superusuário ou Coordenador, vê tudo
        if user.is_superuser or user.groups.filter(name='Coordenacao').exists():
            return queryset
        
        # Se for Professor, só vê os planos das SUAS atribuições
        if hasattr(user, 'teacher_profile'): # Supondo que usamos is_teacher flag ou checagem similar
             # Filtra planos onde a atribuição pertence ao professor logado
             return queryset.filter(assignment__teacher=user)
        
        # Fallback (se não for nada, não vê nada ou vê tudo dependendo da regra)
        # Por segurança, se não é coord nem super, filtra pelo usuário
        return queryset.filter(assignment__teacher=user)

class CoordinatorViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SimpleUserSerializer
    
    def get_queryset(self):
        # Agora funciona independente de qual tabela de usuário você usa
        return User.objects.filter(groups__name='Coordenacao').order_by('first_name')

class AbsenceJustificationViewSet(viewsets.ModelViewSet):
    queryset = AbsenceJustification.objects.all().order_by('-created_at')
    serializer_class = AbsenceJustificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_queryset(self):
        user = self.request.user
        # Se for Pai, vê apenas os pedidos dos seus filhos
        if hasattr(user, 'guardian_profile'):
            return AbsenceJustification.objects.filter(
                attendance__enrollment__student__guardians=user.guardian_profile
            )
        # Se for Coordenação/Admin, vê tudo
        return super().get_queryset()

    def perform_create(self, serializer):
        attendance_id = self.request.data.get('attendance')
        
        # 1. Verificação de Duplicidade (Mantém o que já fizemos)
        if AbsenceJustification.objects.filter(attendance_id=attendance_id, status='PENDING').exists():
            raise ValidationError(["Já existe uma solicitação em análise para esta falta. Aguarde o retorno da coordenação."])
            
        # 2. SEGURANÇA: Força status PENDING na criação (Pai enviando)
        # Assim, mesmo que ele mande "status": "APPROVED", será ignorado e salvo como PENDING.
        serializer.save(status='PENDING')