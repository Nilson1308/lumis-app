from rest_framework import viewsets, permissions, filters, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.db.models import Count, Avg, Q
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.utils import ProgrammingError, OperationalError
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from apps.core.pagination import LargeResultsSetPagination
User = get_user_model()
from .models import (
    Segment, ClassRoom, Guardian, Student, Enrollment, Subject,
    TeacherAssignment, Grade, Attendance, AcademicPeriod, LessonPlan, AbsenceJustification, ExtraActivity,
    ExtraActivityEnrollment, ExtraActivityAttendance,
    TaughtContent, SchoolEvent, ClassSchedule, AcademicHistory, LessonPlan, LessonPlanFile,
    ContraturnoClassroom, ContraturnoAttendance,
    StudentChecklistConfig, StudentDailyChecklist, LessonPlanSubmissionBlock
)
from .serializers import (
    SegmentSerializer, ClassRoomSerializer, StudentSerializer, 
    EnrollmentSerializer, SubjectSerializer, TeacherAssignmentSerializer,
    GradeSerializer, AttendanceSerializer, AcademicPeriodSerializer,
    GuardianSerializer, LessonPlanSerializer, SimpleUserSerializer, ParentStudentSerializer,
    GuardianProfileUpdateSerializer, StudentHealthUpdateSerializer, AbsenceJustificationSerializer,
    ExtraActivitySerializer, ExtraActivityEnrollmentSerializer, ExtraActivityAttendanceSerializer,
    TaughtContentSerializer, SchoolEventSerializer, ClassScheduleSerializer,
    AcademicHistorySerializer, LessonPlanFileSerializer,
    ContraturnoClassroomSerializer, ContraturnoAttendanceSerializer,
    StudentChecklistConfigSerializer, StudentDailyChecklistSerializer
)
from .permissions import IsGuardianOwner, IsGuardianOfStudent
from apps.coordination.models import StudentReport
from apps.core.audit import register_access_audit
from apps.core.models import Notification, SchoolAccount
from . import reports

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
    pagination_class = LargeResultsSetPagination
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    search_fields = ['name', 'year']
    ordering_fields = ['year', 'name']

    @action(detail=True, methods=['get'])
    def dashboard(self, request, pk=None):
        classroom = self.get_object()
        
        # 1. Alunos e Ocorrências
        enrollments = Enrollment.objects.filter(
            classroom=classroom, active=True
        ).select_related('student')
        
        student_ids = [e.student.id for e in enrollments]
        
        # Conta Ocorrências da Turma (Total)
        occurrences_count = StudentReport.objects.filter(
            student__id__in=student_ids,
            report_type='DISCIPLINARY' 
        ).exclude(status='REJECTED').count()

        # 2. Cálculo de Presença (Média da Turma)
        # Pega todas as chamadas feitas para alunos dessa sala
        all_attendance = Attendance.objects.filter(
            enrollment__classroom=classroom
        )
        total_calls = all_attendance.count()
        total_presents = all_attendance.filter(present=True).count()
        
        # Evita divisão por zero
        average_attendance = 0
        if total_calls > 0:
            average_attendance = int((total_presents / total_calls) * 100)

        # 3. Montar Lista de Alunos
        students_data = []
        for enroll in enrollments:
            students_data.append({
                'id': enroll.student.id,
                'name': enroll.student.name,
                'status': 'Ativo' if enroll.active else 'Inativo',
                'photo': request.build_absolute_uri(enroll.student.photo.url) if enroll.student.photo else None,
            })

        # 4. Corpo Docente (Mantém igual)
        assignments = TeacherAssignment.objects.filter(
            classroom=classroom
        ).select_related('teacher', 'subject').order_by('subject__name')
        
        teachers_data = []
        for assign in assignments:
            teachers_data.append({
                'id': assign.id,
                'subject': assign.subject.name,
                'teacher': assign.teacher.get_full_name() or assign.teacher.username,
                'teacher_email': assign.teacher.email
            })

        stats = {
            'total_students': enrollments.count(),
            'total_subjects': assignments.count(),
            'average_attendance': average_attendance, # Valor Real agora!
            'occurrences': occurrences_count
        }

        return Response({
            'classroom': {
                'id': classroom.id,
                'name': classroom.name,
                'year': classroom.year,
                'segment': classroom.segment.name if classroom.segment else 'N/A',
            },
            'stats': stats,
            'students': students_data,
            'faculty': teachers_data
        })

class GuardianViewSet(viewsets.ModelViewSet):
    queryset = Guardian.objects.all().order_by('name')
    serializer_class = GuardianSerializer
    pagination_class = FlexiblePagination
    permission_classes = [permissions.IsAuthenticated, IsGuardianOwner]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'cpf', 'email', 'phone']

    _GUARDIAN_POWER_GROUPS = ['Coordenadores', 'Coordenação', 'Coordenacao', 'Direção', 'Direcao', 'Diretoria', 'Secretaria']

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if user.is_superuser or user.is_staff or user.groups.filter(name__in=self._GUARDIAN_POWER_GROUPS).exists():
            return queryset
        if hasattr(user, 'guardian_profile'):
            return queryset.filter(id=user.guardian_profile.id)
        return queryset.none()

    def get_serializer_class(self):
        user = self.request.user
        
        # Lógica corrigida:
        # Só restringe se for edição E o usuário NÃO for da equipe (Admin/Coord)
        if self.action in ['update', 'partial_update']:
            # Se for um usuário comum (Pai), usa o restrito
            if not (user.is_staff or user.is_superuser or user.groups.filter(name='Coordenacao').exists()):
                return GuardianProfileUpdateSerializer
                
        # Se for Admin/Staff, usa o completo (com Nome, CPF, Secundário...)
        return GuardianSerializer

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        if hasattr(request.user, 'guardian_profile'):
            serializer = self.get_serializer(request.user.guardian_profile)
            return Response(serializer.data)
        return Response({"detail": "Perfil não encontrado"}, status=404)

class ExtraActivityViewSet(viewsets.ModelViewSet):
    queryset = ExtraActivity.objects.all()
    serializer_class = ExtraActivitySerializer


class ExtraActivityEnrollmentViewSet(viewsets.ModelViewSet):
    queryset = ExtraActivityEnrollment.objects.all().select_related('student', 'activity')
    serializer_class = ExtraActivityEnrollmentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['student', 'activity', 'active']


class ExtraActivityAttendanceViewSet(viewsets.ModelViewSet):
    queryset = ExtraActivityAttendance.objects.all().select_related('enrollment', 'enrollment__student', 'enrollment__activity')
    serializer_class = ExtraActivityAttendanceSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['enrollment', 'date']


class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all().order_by('name')
    serializer_class = StudentSerializer
    pagination_class = FlexiblePagination
    parser_classes = (MultiPartParser, FormParser)
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

    def _get_guardian_student_or_403(self, request, student):
        """
        Garante que o usuário autenticado é responsável vinculado ao aluno.
        Reutilizado nos endpoints do Portal da Família para evitar IDOR.
        """
        user = request.user
        if not hasattr(user, 'guardian_profile'):
            return None, Response({"detail": "Acesso negado."}, status=403)

        guardian = user.guardian_profile
        if not student.guardians.filter(id=guardian.id).exists():
            return None, Response({"detail": "Este aluno não está vinculado a você."}, status=403)

        return guardian, None

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
        student = self.get_object()
        _, error_response = self._get_guardian_student_or_403(request, student)
        if error_response:
            return error_response

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

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated], url_path='report-card-pdf')
    def report_card_pdf(self, request, pk=None):
        """
        PDF do boletim para responsáveis, com autorização por vínculo.
        Evita acesso por ID de matrícula fora do escopo do responsável.
        """
        student = self.get_object()
        _, error_response = self._get_guardian_student_or_403(request, student)
        if error_response:
            return error_response

        # Mantém compatibilidade com histórico: tenta matrícula ativa, e se não houver,
        # usa a última matrícula existente para não bloquear geração de boletim.
        enrollment = student.enrollment_set.filter(active=True).select_related('classroom').last()
        if not enrollment:
            enrollment = student.enrollment_set.select_related('classroom').last()
        if not enrollment:
            return Response({"detail": "Aluno sem matrícula ativa."}, status=404)

        register_access_audit(
            request=request,
            action='PARENT_REPORT_CARD_PDF_VIEW',
            resource_type='student_report_card_pdf',
            resource_id=student.id,
            student_id=student.id,
            details={'enrollment_id': enrollment.id}
        )

        return reports.generate_student_report_card(request, enrollment.id)

    # --- RELATÓRIO DE FALTAS ---
    @action(detail=True, methods=['get'], url_path='attendance-report')
    def attendance_report(self, request, pk=None):
        student = self.get_object()
        _, error_response = self._get_guardian_student_or_403(request, student)
        if error_response:
            return error_response

        register_access_audit(
            request=request,
            action='PARENT_ATTENDANCE_REPORT_VIEW',
            resource_type='attendance_report',
            resource_id=student.id,
            student_id=student.id
        )
        
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

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated], url_path='class-diary')
    def class_diary(self, request, pk=None):
        """
        Diário de classe para responsáveis: retorna conteúdos ministrados
        da turma atual do aluno, com filtros opcionais por período e matéria.
        """
        student = self.get_object()
        _, error_response = self._get_guardian_student_or_403(request, student)
        if error_response:
            return error_response

        register_access_audit(
            request=request,
            action='PARENT_CLASS_DIARY_VIEW',
            resource_type='class_diary',
            resource_id=student.id,
            student_id=student.id,
            details={
                'academic_period': request.query_params.get('academic_period'),
                'subject': request.query_params.get('subject')
            }
        )

        enrollment = student.enrollment_set.filter(active=True).select_related('classroom').last()
        if not enrollment:
            return Response([])

        queryset = TaughtContent.objects.filter(
            assignment__classroom=enrollment.classroom
        ).select_related(
            'assignment',
            'assignment__subject',
            'assignment__teacher'
        ).order_by('-date', 'assignment__subject__name')

        subject_id = request.query_params.get('subject')
        if subject_id:
            queryset = queryset.filter(assignment__subject_id=subject_id)

        # NÃO use o nome "period" aqui: conflita com django-filter em StudentViewSet
        # (campo Student.period = turno MORNING/AFTERNOON) e gera 400 antes da action.
        period_id = request.query_params.get('academic_period')
        if period_id:
            try:
                period_id = int(period_id)
            except (TypeError, ValueError):
                # Parâmetro malformado: não quebra a tela; apenas ignora o filtro.
                period_id = None
            if period_id is not None:
                period = AcademicPeriod.objects.filter(id=period_id).first()
                if period:
                    queryset = queryset.filter(
                        date__gte=period.start_date,
                        date__lte=period.end_date
                    )

        serializer = TaughtContentSerializer(queryset, many=True)
        return Response(serializer.data)

class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.select_related('student', 'classroom').all().order_by('student__name')
    serializer_class = EnrollmentSerializer
    filterset_fields = ['classroom', 'student']
    
    # 3. Adicione esta linha para forçar o uso da nossa paginação
    pagination_class = FlexiblePagination

    @action(detail=False, methods=['get'])
    def full_time_by_classroom(self, request):
        """Retorna apenas alunos de período integral de uma turma específica"""
        classroom_id = request.query_params.get('classroom')
        if not classroom_id:
            return Response({"error": "Parâmetro 'classroom' é obrigatório"}, status=400)
        
        enrollments = Enrollment.objects.filter(
            classroom_id=classroom_id,
            active=True,
            student__is_full_time=True
        ).select_related('student', 'classroom')
        
        serializer = self.get_serializer(enrollments, many=True)
        return Response(serializer.data)

class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all().order_by('name')
    serializer_class = SubjectSerializer
    pagination_class = LargeResultsSetPagination
    
    search_fields = ['name']

class TeacherAssignmentViewSet(viewsets.ModelViewSet):
    queryset = TeacherAssignment.objects.all().order_by('classroom', 'subject')
    serializer_class = TeacherAssignmentSerializer
    pagination_class = LargeResultsSetPagination
    
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
        power_groups = ['Coordenadores', 'Coordenação', 'Coordenacao', 'Direção', 'Secretaria']

        # Se for Superusuário ou Coordenador (Via Grupo!), vê tudo
        if user.is_superuser or user.groups.filter(name__in=power_groups).exists():
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
    # Ordenação estável para paginação consistente:
    # quando várias notas têm a mesma data, o "id" desempata e evita
    # itens faltando/duplicando entre páginas.
    queryset = Grade.objects.all().order_by('date', 'id')
    serializer_class = GradeSerializer
    filterset_fields = ['enrollment', 'subject', 'enrollment__classroom', 'period']

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all().order_by('date')
    serializer_class = AttendanceSerializer
    filterset_fields = [
        'enrollment', 
        'subject', 
        'date', 
        'period',
        'enrollment__classroom',
    ]

    _POWER_GROUPS = ['Coordenadores', 'Coordenação', 'Coordenacao', 'Direção', 'Direcao', 'Diretoria', 'Secretaria']

    def _is_power_user(self, user):
        return user.is_superuser or user.groups.filter(name__in=self._POWER_GROUPS).exists()

    def _format_date_br(self, value):
        return value.strftime('%d/%m/%Y')

    def _teacher_can_access_scope(self, user, classroom_id, subject_id=None):
        qs = TeacherAssignment.objects.filter(teacher=user, classroom_id=classroom_id)
        if subject_id:
            qs = qs.filter(subject_id=subject_id)
        return qs.exists()

    def _assert_attendance_scope_access(self, request, classroom_id, subject_id=None):
        user = request.user
        if self._is_power_user(user):
            return
        if self._teacher_can_access_scope(user, classroom_id, subject_id):
            return
        raise PermissionDenied('Sem permissão para consultar dados desta turma/matéria.')

    def _get_non_teaching_event_types(self):
        try:
            school = SchoolAccount.objects.first()
            configured = getattr(school, 'non_teaching_event_types', None) if school else None
        except (ProgrammingError, OperationalError):
            configured = None
        if not configured:
            return ['HOLIDAY']
        allowed_values = {value for value, _ in SchoolEvent.EVENT_TYPES}
        return [event_type for event_type in configured if event_type in allowed_values] or ['HOLIDAY']

    def _non_teaching_dates(self, classroom_id, start_date, end_date):
        range_start = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
        range_end = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
        non_teaching_types = self._get_non_teaching_event_types()

        events = SchoolEvent.objects.filter(
            event_type__in=non_teaching_types,
            start_time__lte=range_end,
        ).filter(
            Q(end_time__gte=range_start) | Q(end_time__isnull=True, start_time__gte=range_start)
        ).filter(
            Q(target_audience='ALL') | Q(target_audience='CLASSROOM', classroom_id=classroom_id)
        )

        blocked_dates = set()
        for event in events:
            event_start = event.start_time.date()
            event_end = event.end_time.date() if event.end_time else event_start
            if event_end < start_date or event_start > end_date:
                continue
            current = max(event_start, start_date)
            last = min(event_end, end_date)
            while current <= last:
                blocked_dates.add(current)
                current += timedelta(days=1)
        return blocked_dates

    @action(detail=False, methods=['get'], url_path='non-teaching-dates')
    def non_teaching_dates(self, request):
        classroom_id = request.query_params.get('classroom')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        if not classroom_id or not start_date_str or not end_date_str:
            return Response(
                {"error": "Parâmetros 'classroom', 'start_date' e 'end_date' são obrigatórios."},
                status=400
            )

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "Formato de data inválido. Use YYYY-MM-DD."}, status=400)

        if end_date < start_date:
            return Response({"error": "'end_date' deve ser maior ou igual a 'start_date'."}, status=400)

        dates = sorted(self._non_teaching_dates(classroom_id, start_date, end_date))
        return Response({
            "event_types": self._get_non_teaching_event_types(),
            "dates": [str(day) for day in dates],
            "dates_br": [self._format_date_br(day) for day in dates],
        })

    def _assignment_pending_dates(self, assignment, start_date, end_date):
        schedule_weekdays = list(
            ClassSchedule.objects.filter(assignment=assignment).values_list('day_of_week', flat=True).distinct()
        )
        if not schedule_weekdays:
            return []

        blocked_dates = self._non_teaching_dates(assignment.classroom_id, start_date, end_date)
        active_enrollments = Enrollment.objects.filter(classroom=assignment.classroom, active=True)
        expected_students = active_enrollments.count()
        if expected_students == 0:
            return []

        pending = []
        current = start_date
        while current <= end_date:
            if current.weekday() in schedule_weekdays and current not in blocked_dates:
                recorded_count = Attendance.objects.filter(
                    enrollment__classroom=assignment.classroom,
                    subject=assignment.subject,
                    date=current
                ).values('enrollment').distinct().count()
                if recorded_count < expected_students:
                    pending.append({
                        'date': str(current),
                        'date_br': self._format_date_br(current),
                        'expected_students': expected_students,
                        'recorded_students': recorded_count,
                        'missing_students': expected_students - recorded_count,
                    })
            current += timedelta(days=1)
        return pending

    @action(detail=False, methods=['get'], url_path='daily-log')
    def daily_log(self, request):
        """
        Retorna a lista COMPLETA de presenças de um dia (SEM PAGINAÇÃO).
        Parâmetros: date (YYYY-MM-DD), classroom, subject.
        Usado pela tela de Chamada para garantir todos os alunos.
        """
        date_str = request.query_params.get('date')
        classroom_id = request.query_params.get('classroom')
        subject_id = request.query_params.get('subject')

        if not date_str or not classroom_id:
            return Response(
                {"error": "Parâmetros 'date' e 'classroom' são obrigatórios"},
                status=400
            )
        self._assert_attendance_scope_access(request, classroom_id, subject_id)

        from datetime import datetime
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "Formato de data inválido. Use YYYY-MM-DD."}, status=400)

        qs = Attendance.objects.filter(
            date=date_obj,
            enrollment__classroom_id=classroom_id
        ).select_related('enrollment', 'subject').order_by('enrollment__student__name')

        if subject_id:
            qs = qs.filter(subject_id=subject_id)

        serializer = AttendanceSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='pending-by-assignment')
    def pending_by_assignment(self, request):
        assignment_id = request.query_params.get('assignment')
        if not assignment_id:
            return Response({"error": "Parâmetro 'assignment' é obrigatório"}, status=400)

        try:
            assignment = TeacherAssignment.objects.select_related('classroom', 'subject', 'teacher').get(pk=assignment_id)
        except TeacherAssignment.DoesNotExist:
            return Response({"error": "Atribuição não encontrada"}, status=404)

        user = request.user
        if not self._is_power_user(user) and assignment.teacher_id != user.id:
            return Response({"error": "Sem permissão para consultar esta atribuição."}, status=403)

        today = datetime.now().date()
        period = AcademicPeriod.objects.filter(
            start_date__lte=today,
            end_date__gte=today
        ).order_by('start_date').first()
        start_date = period.start_date if period else (today - timedelta(days=30))
        pending_dates = self._assignment_pending_dates(assignment, start_date, today)

        return Response({
            "assignment": assignment.id,
            "subject_name": assignment.subject.name,
            "classroom_name": assignment.classroom.name,
            "date_range": {
                "start": str(start_date),
                "end": str(today),
                "start_br": self._format_date_br(start_date),
                "end_br": self._format_date_br(today),
            },
            "pending_count": len(pending_dates),
            "pending_dates": pending_dates,
        })

    @action(detail=False, methods=['get'], url_path='pending-overview')
    def pending_overview(self, request):
        user = request.user
        today = datetime.now().date()
        period = AcademicPeriod.objects.filter(
            start_date__lte=today,
            end_date__gte=today
        ).order_by('start_date').first()
        start_date = period.start_date if period else (today - timedelta(days=30))

        if self._is_power_user(user):
            assignments = TeacherAssignment.objects.all().select_related('classroom', 'subject', 'teacher')
        else:
            assignments = TeacherAssignment.objects.filter(teacher=user).select_related('classroom', 'subject', 'teacher')

        overview = []
        for assignment in assignments:
            pending_dates = self._assignment_pending_dates(assignment, start_date, today)
            if not pending_dates:
                continue
            overview.append({
                "assignment": assignment.id,
                "teacher_id": assignment.teacher_id,
                "teacher_name": assignment.teacher.get_full_name() or assignment.teacher.username,
                "subject_name": assignment.subject.name,
                "classroom_name": assignment.classroom.name,
                "pending_count": len(pending_dates),
                "first_pending_date": pending_dates[0]['date'],
                "first_pending_date_br": pending_dates[0]['date_br'],
                "link": f"/teacher/classes/{assignment.id}/attendance",
            })

        # Gera notificações resumidas para professores logados
        if not self._is_power_user(user):
            active_links = {item['link'] for item in overview}
            Notification.objects.filter(
                recipient=user,
                title__startswith='Pendência de Frequência'
            ).exclude(link__in=active_links).delete()
            for item in overview:
                title = f"Pendência de Frequência - {item['subject_name']}"
                message = (
                    f"{item['classroom_name']}: {item['pending_count']} chamada(s) pendente(s) "
                    f"desde {item['first_pending_date_br']}."
                )
                notif, created = Notification.objects.get_or_create(
                    recipient=user,
                    title=title,
                    link=item['link'],
                    defaults={
                        'message': message,
                        'read': False,
                    }
                )
                if not created and notif.message != message:
                    notif.message = message
                    notif.read = False
                    notif.save(update_fields=['message', 'read'])

        return Response({
            "date_range": {
                "start": str(start_date),
                "end": str(today),
                "start_br": self._format_date_br(start_date),
                "end_br": self._format_date_br(today),
            },
            "total_assignments_with_pending": len(overview),
            "items": overview,
        })

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
        assignment_id = data.get('assignment')
        classroom_id = data.get('classroom')
        date = data.get('date')
        records = data.get('records', [])

        if not subject_id or not date:
            return Response({"error": "Matéria e Data são obrigatórios"}, status=400)
        if not classroom_id:
            return Response({"error": "Turma é obrigatória"}, status=400)

        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "Formato de data inválido. Use YYYY-MM-DD."}, status=400)

        if date_obj in self._non_teaching_dates(classroom_id, date_obj, date_obj):
            return Response(
                {"error": "A data informada é não letiva (feriado/recesso). Não é necessário lançar chamada."},
                status=400
            )

        user = request.user
        power_groups = ['Coordenadores', 'Coordenação', 'Coordenacao', 'Direção', 'Direcao', 'Diretoria', 'Secretaria']
        is_power_user = user.is_superuser or user.groups.filter(name__in=power_groups).exists()

        assignment = None
        if assignment_id:
            assignment = TeacherAssignment.objects.filter(
                id=assignment_id,
                subject_id=subject_id,
                classroom_id=classroom_id,
            ).first()
            if not assignment:
                return Response(
                    {"error": "Atribuição inválida para a matéria/turma informadas."},
                    status=400
                )

        # Para professor comum, exigimos consistência da atribuição e restrição de dia pela grade.
        if not is_power_user:
            if not assignment:
                assignment = TeacherAssignment.objects.filter(
                    teacher=user,
                    subject_id=subject_id,
                    classroom_id=classroom_id,
                ).first()
                if not assignment:
                    return Response(
                        {"error": "Você não possui atribuição para esta matéria/turma."},
                        status=403
                    )
            elif assignment.teacher_id != user.id:
                return Response(
                    {"error": "Você não pode registrar chamada para atribuição de outro professor."},
                    status=403
                )

            schedule_qs = ClassSchedule.objects.filter(
                assignment=assignment,
                classroom_id=classroom_id
            )
            if schedule_qs.exists():
                allowed_weekdays = set(schedule_qs.values_list('day_of_week', flat=True))
                if date_obj.weekday() not in allowed_weekdays:
                    return Response(
                        {
                            "error": (
                                "Data fora da grade horária desta matéria/turma. "
                                "Selecione um dia em que a aula está programada."
                            )
                        },
                        status=400
                    )

        # Garante que os registros pertencem à turma informada
        enrollment_ids = [item.get('enrollment_id') for item in records if item.get('enrollment_id')]
        valid_enrollment_ids = set(
            Enrollment.objects.filter(
                id__in=enrollment_ids,
                classroom_id=classroom_id,
                active=True
            ).values_list('id', flat=True)
        )
        if enrollment_ids and len(valid_enrollment_ids) != len(set(enrollment_ids)):
            return Response(
                {"error": "Há alunos inválidos para a turma selecionada."},
                status=400
            )

        try:
            # Atualiza automaticamente o período ativo antes de buscar
            AcademicPeriod.update_active_period()

            # Busca o período acadêmico que contém a data informada
            period = AcademicPeriod.objects.filter(
                start_date__lte=date_obj,
                end_date__gte=date_obj
            ).first()

            # Se não encontrou período específico, tenta o período ativo
            if not period:
                period = AcademicPeriod.objects.filter(is_active=True).first()
        except Exception as e:
            return Response(
                {"error": f"Erro ao determinar o período acadêmico: {str(e)}"},
                status=400
            )

        # Se ainda assim não houver período, retorna erro claro em vez de seguir silenciosamente
        if not period:
            return Response(
                {"error": "Nenhum período acadêmico encontrado para a data informada."},
                status=400
            )

        try:
            with transaction.atomic():
                created_count = 0
                updated_count = 0

                for item in records:
                    obj, created = Attendance.objects.update_or_create(
                        enrollment_id=item['enrollment_id'],
                        subject_id=subject_id,
                        date=date,
                        defaults={
                            'present': item['present'],
                            'period': period
                        }
                    )
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

            register_access_audit(
                request=request,
                action='ATTENDANCE_BULK_SAVE',
                resource_type='attendance',
                resource_id=f'{classroom_id}:{subject_id}:{date}',
                details={
                    'classroom_id': classroom_id,
                    'subject_id': subject_id,
                    'date': date,
                    'created': created_count,
                    'updated': updated_count,
                    'records_count': len(records),
                }
            )

            return Response({
                "message": "Chamada realizada com sucesso!",
                "created": created_count,
                "updated": updated_count
            })
        except Exception:
            return Response(
                {"error": "Erro interno ao salvar chamada."},
                status=500
            )

    @action(detail=False, methods=['get'])
    def weekly_dates(self, request):
        """
        Retorna as datas em que houve chamada para uma turma/matéria.
        - Se 'month' e 'year' forem informados em query_params, retorna TODAS as datas desse mês.
        - Caso contrário, retorna as datas da semana atual (comportamento original).
        """
        subject_id = request.query_params.get('subject')
        classroom_id = request.query_params.get('classroom')
        month = request.query_params.get('month')
        year = request.query_params.get('year')

        if not subject_id or not classroom_id:
            return Response({"error": "Parâmetros 'subject' e 'classroom' são obrigatórios"}, status=400)
        self._assert_attendance_scope_access(request, classroom_id, subject_id)

        from datetime import datetime, timedelta, date as date_cls
        import calendar

        # Filtro base
        qs = Attendance.objects.filter(
            subject_id=subject_id,
            enrollment__classroom_id=classroom_id,
        )

        # 1) Filtro por mês/ano (histórico completo do mês)
        if month and year:
            try:
                month_int = int(month)
                year_int = int(year)
                first_day = date_cls(year_int, month_int, 1)
                last_day = date_cls(year_int, month_int, calendar.monthrange(year_int, month_int)[1])
            except ValueError:
                return Response({"error": "Parâmetros 'month' e 'year' inválidos."}, status=400)

            qs = qs.filter(date__gte=first_day, date__lte=last_day)
        else:
            # 2) Fallback: semana atual (comportamento anterior)
            today = datetime.now().date()
            monday = today - timedelta(days=today.weekday())
            sunday = monday + timedelta(days=6)
            qs = qs.filter(date__gte=monday, date__lte=sunday)

        dates = qs.values_list('date', flat=True).distinct().order_by('date')

        # Converte para strings YYYY-MM-DD
        date_strings = [str(d) for d in dates]

        return Response(date_strings)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Retorna estatísticas de frequência por período para um aluno/matéria"""
        enrollment_id = request.query_params.get('enrollment')
        subject_id = request.query_params.get('subject')
        
        if not enrollment_id or not subject_id:
            return Response({"error": "Parâmetros 'enrollment' e 'subject' são obrigatórios"}, status=400)

        enrollment = Enrollment.objects.filter(id=enrollment_id).select_related('classroom').first()
        if not enrollment:
            return Response({"error": "Matrícula não encontrada."}, status=404)
        self._assert_attendance_scope_access(request, enrollment.classroom_id, subject_id)
        
        from django.db.models import Count, Q
        from .models import AcademicPeriod
        
        # Busca todas as frequências do aluno nesta matéria
        attendances = Attendance.objects.filter(
            enrollment_id=enrollment_id,
            subject_id=subject_id
        )
        
        # Estatísticas por período
        periods_data = []
        all_periods = AcademicPeriod.objects.all().order_by('start_date')
        
        for period in all_periods:
            period_attendances = attendances.filter(period=period)
            total = period_attendances.count()
            presences = period_attendances.filter(present=True).count()
            absences = total - presences
            
            periods_data.append({
                'period_name': period.name,
                'presences': presences,
                'absences': absences,
                'total': total
            })
        
        # Estatísticas totais
        total_count = attendances.count()
        total_presences = attendances.filter(present=True).count()
        total_absences = total_count - total_presences
        
        return Response({
            'periods': periods_data,
            'total': {
                'presences': total_presences,
                'absences': total_absences,
                'total': total_count
            }
        })

class ContraturnoClassroomViewSet(viewsets.ModelViewSet):
    queryset = ContraturnoClassroom.objects.all().order_by('classroom__name')
    serializer_class = ContraturnoClassroomSerializer
    filterset_fields = ['classroom', 'teacher', 'contraturno_period', 'active']
    pagination_class = LargeResultsSetPagination

    def get_queryset(self):
        user = self.request.user
        queryset = ContraturnoClassroom.objects.all()
        power_groups = ['Coordenadores', 'Coordenação', 'Coordenacao', 'Direção', 'Secretaria']

        if user.is_superuser or user.groups.filter(name__in=power_groups).exists():
            return queryset
        
        # Se for Professor, só vê os contraturnos onde ele é responsável
        return queryset.filter(teacher=user)

    @action(detail=False, methods=['get'])
    def my_contraturnos(self, request):
        """Lista os contraturnos onde o professor logado é responsável"""
        user = request.user
        contraturnos = ContraturnoClassroom.objects.filter(teacher=user, active=True).order_by('classroom__name')
        serializer = self.get_serializer(contraturnos, many=True)
        return Response(serializer.data)

class ContraturnoAttendanceViewSet(viewsets.ModelViewSet):
    queryset = ContraturnoAttendance.objects.all().order_by('-date')
    serializer_class = ContraturnoAttendanceSerializer
    filterset_fields = [
        'enrollment',
        'date',
        'enrollment__classroom',
        'enrollment__student',
    ]

    def get_queryset(self):
        user = self.request.user
        queryset = ContraturnoAttendance.objects.all()
        power_groups = ['Coordenadores', 'Coordenação', 'Coordenacao', 'Direção', 'Secretaria']

        if user.is_superuser or user.groups.filter(name__in=power_groups).exists():
            return queryset
        
        # Se for Professor, só vê frequências dos contraturnos onde ele é responsável
        contraturno_classrooms = ContraturnoClassroom.objects.filter(teacher=user, active=True).values_list('classroom', flat=True)
        return queryset.filter(enrollment__classroom__in=contraturno_classrooms)

    @action(detail=False, methods=['post'])
    def bulk_save(self, request):
        """
        Recebe uma lista de frequências do contraturno e salva todas de uma vez.
        Esperado: {
            "contraturno_classroom": 1,  # ID do ContraturnoClassroom
            "date": "2025-02-20",
            "records": [
                {"enrollment_id": 10, "present": true},
                {"enrollment_id": 11, "present": false}
            ]
        }
        """
        data = request.data
        contraturno_id = data.get('contraturno_classroom')
        date = data.get('date')
        records = data.get('records', [])

        if not contraturno_id or not date:
            return Response({"error": "Contraturno e Data são obrigatórios"}, status=400)

        try:
            contraturno = ContraturnoClassroom.objects.get(pk=contraturno_id, active=True)
        except ContraturnoClassroom.DoesNotExist:
            return Response({"error": "Contraturno não encontrado ou inativo"}, status=404)

        # Verifica permissão: só o professor responsável pode salvar
        user = request.user
        power_groups = ['Coordenadores', 'Coordenação', 'Coordenacao', 'Direção', 'Secretaria']
        if not (user.is_superuser or user.groups.filter(name__in=power_groups).exists() or contraturno.teacher == user):
            return Response({"error": "Você não tem permissão para registrar frequência neste contraturno"}, status=403)

        # Filtra apenas alunos de período integral da turma
        classroom = contraturno.classroom
        enrollments = Enrollment.objects.filter(
            classroom=classroom,
            active=True,
            student__is_full_time=True
        )

        # Transaction Atomic: Ou salva tudo, ou não salva nada (segurança)
        with transaction.atomic():
            created_count = 0
            updated_count = 0
            
            for item in records:
                enrollment_id = item['enrollment_id']
                
                # Verifica se a matrícula pertence à turma do contraturno
                if not enrollments.filter(pk=enrollment_id).exists():
                    continue
                
                # update_or_create: Se já lançou chamada nesse dia, atualiza. Se não, cria.
                obj, created = ContraturnoAttendance.objects.update_or_create(
                    enrollment_id=enrollment_id,
                    date=date,
                    defaults={
                        'present': item['present'],
                        'justified': item.get('justified', False),
                        'observation': item.get('observation', '')
                    }
                )
                if created: created_count += 1
                else: updated_count += 1

        return Response({
            "message": "Chamada do contraturno realizada com sucesso!",
            "created": created_count,
            "updated": updated_count
        })

    @action(detail=False, methods=['get'])
    def by_contraturno(self, request):
        """Lista frequências de um contraturno específico em uma data"""
        contraturno_id = request.query_params.get('contraturno_classroom')
        date = request.query_params.get('date')

        if not contraturno_id or not date:
            return Response({"error": "Parâmetros contraturno_classroom e date são obrigatórios"}, status=400)

        try:
            contraturno = ContraturnoClassroom.objects.get(pk=contraturno_id, active=True)
        except ContraturnoClassroom.DoesNotExist:
            return Response({"error": "Contraturno não encontrado"}, status=404)

        # Busca frequências existentes
        enrollments = Enrollment.objects.filter(
            classroom=contraturno.classroom,
            active=True,
            student__is_full_time=True
        )
        
        attendances = ContraturnoAttendance.objects.filter(
            enrollment__in=enrollments,
            date=date
        )

        serializer = self.get_serializer(attendances, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def weekly_dates(self, request):
        """Retorna as datas da semana atual onde houve chamada do contraturno"""
        contraturno_id = request.query_params.get('contraturno_classroom')
        
        if not contraturno_id:
            return Response({"error": "Parâmetro 'contraturno_classroom' é obrigatório"}, status=400)
        
        try:
            contraturno = ContraturnoClassroom.objects.get(pk=contraturno_id, active=True)
        except ContraturnoClassroom.DoesNotExist:
            return Response({"error": "Contraturno não encontrado"}, status=404)
        
        from datetime import datetime, timedelta
        today = datetime.now().date()
        # Segunda-feira da semana atual
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        
        enrollments = Enrollment.objects.filter(
            classroom=contraturno.classroom,
            active=True,
            student__is_full_time=True
        )
        
        dates = ContraturnoAttendance.objects.filter(
            enrollment__in=enrollments,
            date__gte=monday,
            date__lte=sunday
        ).values_list('date', flat=True).distinct()
        
        # Converte para strings YYYY-MM-DD
        date_strings = [str(d) for d in dates]
        
        return Response(date_strings)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Retorna estatísticas de frequência do contraturno por período"""
        enrollment_id = request.query_params.get('enrollment')
        
        if not enrollment_id:
            return Response({"error": "Parâmetro 'enrollment' é obrigatório"}, status=400)
        
        from django.db.models import Count, Q
        from .models import AcademicPeriod
        
        # Busca todas as frequências do aluno no contraturno
        attendances = ContraturnoAttendance.objects.filter(enrollment_id=enrollment_id)
        
        # Estatísticas por período (simplificado - contraturno não tem período acadêmico vinculado)
        # Vamos agrupar por mês/trimestre
        from collections import defaultdict
        from datetime import datetime
        
        periods_data = []
        monthly_stats = defaultdict(lambda: {'presences': 0, 'absences': 0, 'total': 0})
        
        for att in attendances:
            month_key = att.date.strftime('%Y-%m')
            monthly_stats[month_key]['total'] += 1
            if att.present:
                monthly_stats[month_key]['presences'] += 1
            else:
                monthly_stats[month_key]['absences'] += 1
        
        # Mapeamento de meses em português
        month_names = {
            '01': 'Janeiro', '02': 'Fevereiro', '03': 'Março', '04': 'Abril',
            '05': 'Maio', '06': 'Junho', '07': 'Julho', '08': 'Agosto',
            '09': 'Setembro', '10': 'Outubro', '11': 'Novembro', '12': 'Dezembro'
        }
        
        for month_key, stats in sorted(monthly_stats.items()):
            year, month = month_key.split('-')
            month_name = f"{month_names.get(month, month)}/{year}"
            periods_data.append({
                'period_name': month_name,
                'presences': stats['presences'],
                'absences': stats['absences'],
                'total': stats['total']
            })
        
        # Estatísticas totais
        total_count = attendances.count()
        total_presences = attendances.filter(present=True).count()
        total_absences = total_count - total_presences
        
        return Response({
            'periods': periods_data,
            'total': {
                'presences': total_presences,
                'absences': total_absences,
                'total': total_count
            }
        })

class AcademicPeriodViewSet(viewsets.ModelViewSet):
    queryset = AcademicPeriod.objects.all().order_by('start_date') 
    serializer_class = AcademicPeriodSerializer
    search_fields = ['name']
    
    def get_queryset(self):
        # Atualiza automaticamente o período ativo antes de retornar a lista
        AcademicPeriod.update_active_period()
        return super().get_queryset()
    
    @action(detail=False, methods=['post'])
    def update_active(self, request):
        """Endpoint para atualizar manualmente o período ativo"""
        period = AcademicPeriod.update_active_period()
        if period:
            serializer = self.get_serializer(period)
            return Response({
                'message': f'Período {period.name} ativado automaticamente',
                'period': serializer.data
            })
        return Response({'message': 'Nenhum período encontrado para a data atual'}, status=404)

class StudentChecklistConfigViewSet(viewsets.ModelViewSet):
    queryset = StudentChecklistConfig.objects.all().select_related('segment')
    serializer_class = StudentChecklistConfigSerializer
    pagination_class = LargeResultsSetPagination
    filterset_fields = ['segment', 'requires_checklist']

class StudentDailyChecklistViewSet(viewsets.ModelViewSet):
    queryset = StudentDailyChecklist.objects.all().order_by('-date')
    serializer_class = StudentDailyChecklistSerializer
    filterset_fields = [
        'enrollment',
        'date',
        'enrollment__classroom',
        'enrollment__student',
    ]

    def get_queryset(self):
        user = self.request.user
        queryset = StudentDailyChecklist.objects.all()
        power_groups = ['Coordenadores', 'Coordenação', 'Coordenacao', 'Direção', 'Secretaria']

        if user.is_superuser or user.groups.filter(name__in=power_groups).exists():
            return queryset
        
        # Se for Professor, só vê checklists das turmas onde ele está atribuído
        assignments = TeacherAssignment.objects.filter(teacher=user).values_list('classroom', flat=True)
        return queryset.filter(enrollment__classroom__in=assignments)

    def perform_create(self, serializer):
        """Salva automaticamente quem registrou"""
        serializer.save(registered_by=self.request.user)

    def perform_update(self, serializer):
        """Atualiza quem registrou"""
        serializer.save(registered_by=self.request.user)

    @action(detail=False, methods=['post'])
    def bulk_save(self, request):
        """
        Salva múltiplos checklists de uma vez.
        Esperado: {
            "classroom": 1,
            "date": "2025-02-20",
            "records": [
                {
                    "enrollment_id": 10,
                    "had_lunch": true,
                    "had_snack": false,
                    "checkin_time": "07:30:00",
                    "checkout_time": "17:00:00"
                }
            ]
        }
        """
        data = request.data
        classroom_id = data.get('classroom')
        date = data.get('date')
        records = data.get('records', [])

        if not classroom_id or not date:
            return Response({"error": "Turma e Data são obrigatórios"}, status=400)

        # Verifica se a turma requer checklist
        try:
            classroom = ClassRoom.objects.get(pk=classroom_id)
            config = StudentChecklistConfig.objects.filter(segment=classroom.segment, requires_checklist=True).first()
            
            if not config:
                return Response({"error": "Este segmento não requer checklist diário"}, status=400)
        except ClassRoom.DoesNotExist:
            return Response({"error": "Turma não encontrada"}, status=404)

        # Verifica permissão: só professores atribuídos à turma podem registrar
        user = request.user
        power_groups = ['Coordenadores', 'Coordenação', 'Coordenacao', 'Direção', 'Secretaria']
        has_assignment = TeacherAssignment.objects.filter(teacher=user, classroom=classroom).exists()
        
        if not (user.is_superuser or user.groups.filter(name__in=power_groups).exists() or has_assignment):
            return Response({"error": "Você não tem permissão para registrar checklist nesta turma"}, status=403)

        enrollments = Enrollment.objects.filter(classroom=classroom, active=True)

        # Transaction Atomic
        with transaction.atomic():
            created_count = 0
            updated_count = 0
            
            for item in records:
                enrollment_id = item.get('enrollment_id')
                
                # Verifica se a matrícula pertence à turma
                if not enrollments.filter(pk=enrollment_id).exists():
                    continue
                
                # Prepara os dados do checklist
                checklist_data = {
                    'had_lunch': item.get('had_lunch'),
                    'had_snack': item.get('had_snack'),
                    'checkin_time': item.get('checkin_time'),
                    'checkout_time': item.get('checkout_time'),
                    'observation': item.get('observation', ''),
                    'registered_by': user
                }
                
                # Remove campos None/vazios se não são obrigatórios
                if not config.requires_lunch:
                    checklist_data.pop('had_lunch', None)
                if not config.requires_snack:
                    checklist_data.pop('had_snack', None)
                if not config.requires_checkin:
                    checklist_data.pop('checkin_time', None)
                if not config.requires_checkout:
                    checklist_data.pop('checkout_time', None)
                
                obj, created = StudentDailyChecklist.objects.update_or_create(
                    enrollment_id=enrollment_id,
                    date=date,
                    defaults=checklist_data
                )
                if created: created_count += 1
                else: updated_count += 1

        return Response({
            "message": "Checklist salvo com sucesso!",
            "created": created_count,
            "updated": updated_count
        })

    @action(detail=False, methods=['get'])
    def by_classroom_date(self, request):
        """Lista checklists de uma turma em uma data específica"""
        classroom_id = request.query_params.get('classroom')
        date = request.query_params.get('date')

        if not classroom_id or not date:
            return Response({"error": "Parâmetros 'classroom' e 'date' são obrigatórios"}, status=400)

        enrollments = Enrollment.objects.filter(classroom_id=classroom_id, active=True)
        checklists = StudentDailyChecklist.objects.filter(
            enrollment__in=enrollments,
            date=date
        )

        serializer = self.get_serializer(checklists, many=True)
        return Response(serializer.data)

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


class DashboardRiskStudentsView(APIView):
    """
    Lista alunos em risco (+5 faltas).
    Coordenadores: todas as turmas.
    Professores: apenas turmas onde lecionam.
    """
    permission_classes = [permissions.IsAuthenticated]
    risk_threshold = 5

    def get(self, request):
        from django.db.models import Prefetch

        user = request.user
        is_coordinator = user.is_superuser or user.groups.filter(name='Coordenacao').exists()

        if is_coordinator:
            qs = Student.objects.annotate(
                absences=Count('enrollment__attendance', filter=Q(enrollment__attendance__present=False))
            ).filter(absences__gt=self.risk_threshold).prefetch_related(
                Prefetch('enrollment_set', queryset=Enrollment.objects.filter(active=True).select_related('classroom'))
            )
        else:
            my_classrooms = ClassRoom.objects.filter(teacherassignment__teacher=user).distinct()
            qs = Student.objects.filter(enrollment__classroom__in=my_classrooms).annotate(
                absences=Count('enrollment__attendance', filter=Q(enrollment__attendance__present=False))
            ).filter(absences__gt=self.risk_threshold).distinct().prefetch_related(
                Prefetch('enrollment_set', queryset=Enrollment.objects.filter(active=True, classroom__in=my_classrooms).select_related('classroom'))
            )

        result = []
        for s in qs:
            enr = s.enrollment_set.first()
            classroom_name = enr.classroom.name if enr else '-'
            result.append({
                'id': s.id,
                'name': s.name,
                'registration_number': s.registration_number,
                'classroom_name': classroom_name,
                'classroom_id': enr.classroom_id if enr else None,
                'enrollment_id': enr.id if enr else None,
                'absences': s.absences
            })

        return Response(result)


class ReportDiaryPDFView(APIView):
    """Diário de classe em PDF. Professor: suas turmas. Coordenador: escolhe turma."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return reports.generate_diary_report(request)


class ReportAttendancePDFView(APIView):
    """Relatório de Frequências em PDF. Professor: suas turmas. Coordenador: escolhe turma."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return reports.generate_attendance_report(request)


class LessonPlanViewSet(viewsets.ModelViewSet):
    serializer_class = LessonPlanSerializer
    # Importante para aceitar uploads
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = [
        'assignment', 'assignment__teacher', 'assignment__classroom', 
        'assignment__subject', 'status', 'start_date'
    ]
    search_fields = ['topic', 'assignment__teacher__first_name']

    _PLAN_GUARD_POWER_GROUPS = ['Coordenadores', 'Coordenação', 'Coordenacao', 'Direção', 'Direcao', 'Diretoria', 'Secretaria']

    def _is_power_user(self, user):
        return user.is_superuser or user.groups.filter(name__in=self._PLAN_GUARD_POWER_GROUPS).exists()

    def _is_plan_guard_enabled(self):
        school = SchoolAccount.objects.first()
        return bool(school and getattr(school, 'enforce_lesson_plan_submission_guard', False))

    def _teacher_overdue_items(self, teacher):
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        previous_week_start = week_start - timedelta(days=7)
        previous_week_end = week_start - timedelta(days=1)

        assignments = TeacherAssignment.objects.filter(teacher=teacher).select_related('subject', 'classroom')
        overdue = []
        for assignment in assignments:
            has_submitted = LessonPlan.objects.filter(
                assignment=assignment,
                start_date__lte=previous_week_end,
                end_date__gte=previous_week_start,
                status__in=['SUBMITTED', 'APPROVED']
            ).exists()
            if not has_submitted:
                overdue.append({
                    'assignment': assignment.id,
                    'subject_name': assignment.subject.name,
                    'classroom_name': assignment.classroom.name,
                    'week_start': previous_week_start.strftime('%d/%m/%Y'),
                    'week_end': previous_week_end.strftime('%d/%m/%Y'),
                })
        return overdue

    def _ensure_teacher_block_if_overdue(self, teacher):
        overdue = self._teacher_overdue_items(teacher)
        active_block = LessonPlanSubmissionBlock.objects.filter(teacher=teacher, active=True).first()
        if overdue and not active_block:
            reason = (
                f"Atraso no envio do planejamento da semana {overdue[0]['week_start']} a "
                f"{overdue[0]['week_end']}. Aguarde liberação da coordenação."
            )
            LessonPlanSubmissionBlock.objects.create(
                teacher=teacher,
                active=True,
                reason=reason,
            )
            Notification.objects.create(
                recipient=teacher,
                title='Envio de Planejamento Bloqueado',
                message=reason,
                link='/teacher/lesson-plans',
                read=False,
            )
        return overdue

    def _check_submission_block_or_raise(self, request, status_value):
        if status_value != 'SUBMITTED':
            return
        if not self._is_plan_guard_enabled():
            return

        user = request.user
        if self._is_power_user(user):
            return

        overdue = self._ensure_teacher_block_if_overdue(user)
        block = LessonPlanSubmissionBlock.objects.filter(teacher=user, active=True).first()
        if block:
            register_access_audit(
                request=request,
                action='LESSON_PLAN_SUBMISSION_BLOCKED',
                resource_type='lesson_plan_submission',
                resource_id='new_or_update',
                details={
                    'teacher_id': user.id,
                    'reason': block.reason,
                    'overdue_items_count': len(overdue),
                }
            )
            raise ValidationError({
                'status': (
                    'Envio bloqueado por atraso de planejamento. '
                    'A coordenação/admin precisa liberar seu fluxo.'
                ),
                'detail': block.reason or 'Envio bloqueado por atraso.'
            })

    def get_queryset(self):
        """
        Regras de visibilidade:
        - view_mode='teacher': contexto de professor (ex.: "Meus Planejamentos") – retorna ESTRITAMENTE
          os planos do professor, ignorando superuser/coordenação.
        - Caso contrário: superuser vê tudo; power_groups vê recipients; professor vê os seus.
        """
        user = self.request.user
        queryset = LessonPlan.objects.all().order_by('-start_date')
        power_groups = ['Coordenadores', 'Coordenação', 'Coordenacao', 'Direção', 'Secretaria']
        view_mode = self.request.query_params.get('view_mode')

        # Isolamento de contexto: "Meus Planejamentos" ( professor )
        if view_mode == 'teacher':
            return queryset.filter(assignment__teacher=user)

        # 1) Superusuário tem acesso total
        if user.is_superuser:
            return queryset

        # 2) Coordenação / Direção / Secretaria
        if user.groups.filter(name__in=power_groups).exists():
            return queryset.filter(recipients=user)

        # 3) Professor (sem view_mode): isolamento – só vê seus planejamentos
        return queryset.filter(assignment__teacher=user)

    def perform_create(self, serializer):
        requested_status = self.request.data.get('status', 'DRAFT')
        self._check_submission_block_or_raise(self.request, requested_status)
        # 1. Salva os dados básicos e Recipients
        plan = serializer.save()
        if requested_status == 'SUBMITTED':
            register_access_audit(
                request=self.request,
                action='LESSON_PLAN_SUBMITTED',
                resource_type='lesson_plan',
                resource_id=plan.id,
                details={'assignment_id': plan.assignment_id}
            )
        
        # 2. Processa os Arquivos (attachments) vindo do Frontend
        self._handle_attachments(plan)

    def perform_update(self, serializer):
        requested_status = self.request.data.get('status')
        if requested_status is None:
            requested_status = serializer.instance.status
        self._check_submission_block_or_raise(self.request, requested_status)
        plan = serializer.save()
        if requested_status == 'SUBMITTED':
            register_access_audit(
                request=self.request,
                action='LESSON_PLAN_RESUBMITTED',
                resource_type='lesson_plan',
                resource_id=plan.id,
                details={'assignment_id': plan.assignment_id}
            )
        self._handle_attachments(plan)

    def _handle_attachments(self, plan):
        # Pega a lista de arquivos enviada com a chave 'attachments'
        files = self.request.FILES.getlist('attachments')
        
        for f in files:
            LessonPlanFile.objects.create(
                plan=plan, 
                file=f,
                name=f.name # Salva o nome original
            )

    @action(detail=True, methods=['post'])
    def unsubscribe(self, request, pk=None):
        """Permite que um coordenador se remova da lista de destinatários."""
        plan = self.get_object()
        user = request.user
        
        if user in plan.recipients.all():
            plan.recipients.remove(user)
            return Response({'status': 'unsubscribed', 'message': 'Você foi removido da lista de destinatários.'})
        
        return Response({'status': 'ignored', 'message': 'Você não estava na lista.'}, status=200)

    @action(detail=False, methods=['get'], url_path='submission-guard')
    def submission_guard(self, request):
        user = request.user
        target_teacher = user
        teacher_id = request.query_params.get('teacher_id')
        if teacher_id and self._is_power_user(user):
            target_teacher = User.objects.filter(id=teacher_id).first() or user

        enabled = self._is_plan_guard_enabled()
        overdue = self._teacher_overdue_items(target_teacher) if enabled else []
        active_block = LessonPlanSubmissionBlock.objects.filter(teacher=target_teacher, active=True).first()

        return Response({
            'enabled': enabled,
            'teacher_id': target_teacher.id,
            'blocked': bool(active_block),
            'block_reason': active_block.reason if active_block else '',
            'overdue_items': overdue,
        })

    @action(detail=False, methods=['post'], url_path='release-submission-guard')
    def release_submission_guard(self, request):
        if not self._is_power_user(request.user):
            return Response({'error': 'Sem permissão.'}, status=403)

        teacher_id = request.data.get('teacher_id')
        if not teacher_id:
            return Response({'error': 'teacher_id é obrigatório.'}, status=400)

        teacher = User.objects.filter(id=teacher_id).first()
        if not teacher:
            return Response({'error': 'Professor não encontrado.'}, status=404)

        block = LessonPlanSubmissionBlock.objects.filter(teacher=teacher, active=True).first()
        if block:
            block.active = False
            block.released_by = request.user
            block.released_at = timezone.now()
            block.save(update_fields=['active', 'released_by', 'released_at'])
            register_access_audit(
                request=request,
                action='LESSON_PLAN_GUARD_RELEASE',
                resource_type='lesson_plan_submission_block',
                resource_id=block.id,
                details={'teacher_id': teacher.id, 'reason': block.reason}
            )

        Notification.objects.create(
            recipient=teacher,
            title='Envio de Planejamento Liberado',
            message='Seu fluxo de envio de planejamento foi liberado pela coordenação/admin.',
            link='/teacher/lesson-plans',
            read=False,
        )

        return Response({'message': 'Fluxo de envio liberado com sucesso.'})

    @action(detail=False, methods=['get'], url_path='blocked-teachers')
    def blocked_teachers(self, request):
        if not self._is_power_user(request.user):
            return Response({'error': 'Sem permissão.'}, status=403)

        active_param = request.query_params.get('active', 'true').lower()
        is_active = active_param != 'false'
        query = (request.query_params.get('q') or '').strip().lower()

        blocks = (
            LessonPlanSubmissionBlock.objects.filter(active=is_active)
            .select_related('teacher', 'blocked_by')
            .order_by('-created_at' if is_active else '-released_at')
        )
        data = []
        for block in blocks:
            teacher_name = block.teacher.get_full_name() or block.teacher.username
            if query and query not in teacher_name.lower() and query not in block.teacher.username.lower():
                continue
            overdue = self._teacher_overdue_items(block.teacher) if self._is_plan_guard_enabled() else []
            data.append({
                'block_id': block.id,
                'teacher_id': block.teacher_id,
                'teacher_name': teacher_name,
                'teacher_username': block.teacher.username,
                'blocked_at': block.created_at,
                'blocked_at_br': timezone.localtime(block.created_at).strftime('%d/%m/%Y %H:%M'),
                'released_at': block.released_at,
                'released_at_br': (
                    timezone.localtime(block.released_at).strftime('%d/%m/%Y %H:%M')
                    if block.released_at else ''
                ),
                'active': block.active,
                'reason': block.reason or '',
                'blocked_by': (
                    block.blocked_by.get_full_name() or block.blocked_by.username
                    if block.blocked_by else 'Sistema'
                ),
                'overdue_items': overdue,
            })
        return Response({
            'enabled': self._is_plan_guard_enabled(),
            'count': len(data),
            'items': data,
        })

    @action(detail=False, methods=['post'], url_path='block-submission-guard')
    def block_submission_guard(self, request):
        if not self._is_power_user(request.user):
            return Response({'error': 'Sem permissão.'}, status=403)

        teacher_id = request.data.get('teacher_id')
        reason = (request.data.get('reason') or '').strip()
        if not teacher_id:
            return Response({'error': 'teacher_id é obrigatório.'}, status=400)
        teacher = User.objects.filter(id=teacher_id).first()
        if not teacher:
            return Response({'error': 'Professor não encontrado.'}, status=404)

        block, created = LessonPlanSubmissionBlock.objects.get_or_create(
            teacher=teacher,
            active=True,
            defaults={
                'reason': reason or 'Bloqueio manual pela coordenação/admin.',
                'blocked_by': request.user,
            }
        )
        if not created:
            block.reason = reason or block.reason or 'Bloqueio manual pela coordenação/admin.'
            block.blocked_by = request.user
            block.save(update_fields=['reason', 'blocked_by'])

        Notification.objects.create(
            recipient=teacher,
            title='Envio de Planejamento Bloqueado',
            message=block.reason,
            link='/teacher/lesson-plans',
            read=False,
        )
        register_access_audit(
            request=request,
            action='LESSON_PLAN_GUARD_BLOCK',
            resource_type='lesson_plan_submission_block',
            resource_id=block.id,
            details={'teacher_id': teacher.id, 'reason': block.reason}
        )
        return Response({'message': 'Professor bloqueado com sucesso.'})

    @action(detail=False, methods=['post'], url_path='release-all-submission-guard')
    def release_all_submission_guard(self, request):
        if not self._is_power_user(request.user):
            return Response({'error': 'Sem permissão.'}, status=403)

        blocks = LessonPlanSubmissionBlock.objects.filter(active=True)
        teacher_ids = list(blocks.values_list('teacher_id', flat=True))
        updated = blocks.update(active=False, released_by=request.user, released_at=timezone.now())
        if updated:
            register_access_audit(
                request=request,
                action='LESSON_PLAN_GUARD_RELEASE_ALL',
                resource_type='lesson_plan_submission_block',
                resource_id='bulk',
                details={'updated': updated, 'teacher_ids': teacher_ids}
            )
        return Response({'message': f'{updated} bloqueio(s) liberado(s).', 'updated': updated})

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
        attendance = Attendance.objects.filter(id=attendance_id).select_related(
            'enrollment__student'
        ).first()
        if not attendance:
            raise ValidationError(["Frequência não encontrada para justificar."])

        user = self.request.user
        if hasattr(user, 'guardian_profile'):
            if not attendance.enrollment.student.guardians.filter(id=user.guardian_profile.id).exists():
                raise PermissionDenied('Sem permissão para justificar falta de outro aluno.')
        
        # 1. Verificação de Duplicidade (Mantém o que já fizemos)
        if AbsenceJustification.objects.filter(attendance_id=attendance_id, status='PENDING').exists():
            raise ValidationError(["Já existe uma solicitação em análise para esta falta. Aguarde o retorno da coordenação."])
            
        # 2. SEGURANÇA: Força status PENDING na criação (Pai enviando)
        # Assim, mesmo que ele mande "status": "APPROVED", será ignorado e salvo como PENDING.
        justification = serializer.save(status='PENDING')
        register_access_audit(
            request=self.request,
            action='ABSENCE_JUSTIFICATION_CREATE',
            resource_type='absence_justification',
            resource_id=justification.id,
            student_id=getattr(justification.attendance.enrollment.student, 'id', None),
            details={'attendance_id': attendance_id}
        )

    def perform_update(self, serializer):
        user = self.request.user
        if hasattr(user, 'guardian_profile') and 'status' in self.request.data:
            raise PermissionDenied('Responsáveis não podem alterar o status da justificativa.')

        previous_status = serializer.instance.status if serializer.instance else None
        justification = serializer.save()
        if previous_status != justification.status:
            register_access_audit(
                request=self.request,
                action='ABSENCE_JUSTIFICATION_STATUS_CHANGE',
                resource_type='absence_justification',
                resource_id=justification.id,
                student_id=getattr(justification.attendance.enrollment.student, 'id', None),
                details={
                    'previous_status': previous_status,
                    'new_status': justification.status,
                    'attendance_id': justification.attendance_id,
                }
            )

class TaughtContentViewSet(viewsets.ModelViewSet):
    queryset = TaughtContent.objects.all()
    serializer_class = TaughtContentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['assignment', 'date'] # Permite filtrar por ID da atribuição ou data na URL

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        # Se for professor, filtra apenas os conteúdos vinculados às suas atribuições
        if user.groups.filter(name='Professores').exists():
            return queryset.filter(assignment__teacher=user)
        
        return queryset

class SchoolEventViewSet(viewsets.ModelViewSet):
    serializer_class = SchoolEventSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    _POWER_GROUPS = ['Coordenadores', 'Coordenação', 'Coordenacao', 'Direção', 'Direcao', 'Diretoria', 'Secretaria']

    def get_queryset(self):
        user = self.request.user
        
        queryset = SchoolEvent.objects.all().order_by('start_time')

        start = self.request.query_params.get('start')
        end = self.request.query_params.get('end')
        if start and end:
            queryset = queryset.filter(start_time__range=[start, end])

        # 1. COORDENADORES / DIREÇÃO / SECRETARIA
        power_groups = self._POWER_GROUPS
        
        # Verifica se tem intersecção entre os grupos do usuário e a lista de poder
        user_groups = set(user.groups.values_list('name', flat=True))
        is_power_user = user.is_superuser or bool(set(power_groups) & user_groups)

        if is_power_user:
            return queryset 

        # 2. PROFESSORES
        if user.groups.filter(name='Professores').exists():
            return queryset.filter(target_audience__in=['ALL', 'TEACHERS', 'CLASSROOM'])

        # 3. RESPONSÁVEIS
        if user.groups.filter(name__in=['Responsáveis', 'Responsaveis', 'Pais']).exists():
            guardian = Guardian.objects.filter(user=user).first()
            if not guardian:
                return queryset.filter(target_audience='ALL')

            student_ids = guardian.students.values_list('id', flat=True)
            my_classrooms_ids = Enrollment.objects.filter(
                student__id__in=student_ids
            ).values_list('classroom_id', flat=True).distinct()
            
            return queryset.filter(
                Q(target_audience='ALL') | 
                Q(target_audience='CLASSROOM', classroom__id__in=my_classrooms_ids)
            ).distinct()

        # 4. PADRÃO
        return queryset.filter(target_audience='ALL')

    def create(self, request, *args, **kwargs):
        user = request.user
        can_create = (
            user.is_superuser
            or user.groups.filter(name__in=self._POWER_GROUPS).exists()
            or user.groups.filter(name='Professores').exists()
        )
        if not can_create:
            return Response({'error': 'Ação não permitida.'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    # --- REGISTRA O AUTOR ---
    def perform_create(self, serializer):
        event = serializer.save(created_by=self.request.user)
        register_access_audit(
            request=self.request,
            action='SCHOOL_EVENT_CREATE',
            resource_type='school_event',
            resource_id=event.id,
            details={
                'event_type': event.event_type,
                'target_audience': event.target_audience,
                'classroom_id': event.classroom_id,
            }
        )

    # --- CONTROLE DE EDIÇÃO ---
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self.can_edit(request.user, instance):
             return Response({'error': 'Ação não permitida.'}, status=status.HTTP_403_FORBIDDEN)
        response = super().update(request, *args, **kwargs)
        register_access_audit(
            request=request,
            action='SCHOOL_EVENT_UPDATE',
            resource_type='school_event',
            resource_id=instance.id,
            details={'event_type': instance.event_type, 'target_audience': instance.target_audience}
        )
        return response

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self.can_edit(request.user, instance):
             return Response({'error': 'Ação não permitida.'}, status=status.HTTP_403_FORBIDDEN)
        instance_id = instance.id
        event_type = instance.event_type
        response = super().destroy(request, *args, **kwargs)
        register_access_audit(
            request=request,
            action='SCHOOL_EVENT_DELETE',
            resource_type='school_event',
            resource_id=instance_id,
            details={'event_type': event_type}
        )
        return response

    def can_edit(self, user, event):
        # 1. Admin / Coordenação / Direção -> MEXE EM TUDO
        # Adicionei 'Coordenacao' e 'Direcao' (sem acento)
        power_editors = ['Coordenadores', 'Coordenação', 'Coordenacao', 'Direção', 'Direcao', 'Diretoria']
        
        if user.is_superuser or user.groups.filter(name__in=power_editors).exists():
            return True
        
        # 2. Secretaria -> MEXE NO PÚBLICO, BLOQUEIA PROVAS ALHEIAS
        if user.groups.filter(name='Secretaria').exists():
            if event.event_type in ['EXAM', 'ASSIGNMENT'] and event.created_by != user:
                return False
            return True 
        
        # 3. Professores -> SÓ MEXE NO QUE ELE CRIOU
        if user.groups.filter(name='Professores').exists():
            return event.created_by == user
            
        return False

class ClassScheduleViewSet(viewsets.ModelViewSet):
    queryset = ClassSchedule.objects.all().order_by('day_of_week', 'start_time')
    serializer_class = ClassScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = LargeResultsSetPagination

    _SCHEDULE_POWER_GROUPS = (
        'Coordenadores',
        'Coordenação',
        'Coordenacao',
        'Direção',
        'Direcao',
        'Diretoria',
        'Secretaria',
    )

    # Permite filtrar por turma: /api/schedules/?classroom=1
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    filterset_fields = ['classroom', 'day_of_week']

    def _can_manage_schedule(self, user):
        if user.is_superuser:
            return True
        return user.groups.filter(name__in=self._SCHEDULE_POWER_GROUPS).exists()

    def _assert_can_manage(self):
        if not self._can_manage_schedule(self.request.user):
            raise PermissionDenied('Sem permissão para alterar a grade horária.')

    def create(self, request, *args, **kwargs):
        self._assert_can_manage()
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self._assert_can_manage()
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        self._assert_can_manage()
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._assert_can_manage()
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        qs = (
            ClassSchedule.objects.select_related(
                'classroom',
                'assignment',
                'assignment__subject',
                'assignment__teacher',
            )
            .order_by('day_of_week', 'start_time')
        )
        if user.is_superuser or user.groups.filter(name__in=self._SCHEDULE_POWER_GROUPS).exists():
            return qs

        if user.groups.filter(name='Professores').exists():
            classroom_ids = TeacherAssignment.objects.filter(teacher=user).values_list(
                'classroom_id', flat=True
            )
            return qs.filter(classroom_id__in=classroom_ids)

        if hasattr(user, 'guardian_profile'):
            classroom_ids = (
                Enrollment.objects.filter(
                    student__guardians=user.guardian_profile,
                    active=True,
                )
                .values_list('classroom_id', flat=True)
                .distinct()
            )
            return qs.filter(classroom_id__in=classroom_ids)

        return qs.none()

class AcademicHistoryViewSet(viewsets.ModelViewSet):
    queryset = AcademicHistory.objects.all().order_by('-year')
    serializer_class = AcademicHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['student']

    def list(self, request, *args, **kwargs):
        """
        Sobrescreve a listagem para mesclar o Histórico Gravado 
        com a Matrícula Ativa (Enrollment) se solicitado.
        """
        response = super().list(request, *args, **kwargs)
        
        # Se estiver filtrando por aluno, vamos tentar injetar a matrícula atual visualmente
        student_id = request.query_params.get('student')
        if student_id:
            # Pega matrículas ativas desse aluno
            active_enrollments = Enrollment.objects.filter(student_id=student_id, active=True)
            
            for enroll in active_enrollments:
                # Verifica se já não existe um histórico gravado para este ano (evita duplicata)
                exists = self.get_queryset().filter(student_id=student_id, year=enroll.classroom.year).exists()
                
                if not exists:
                    # Cria um objeto "fake" de histórico apenas para visualização
                    current_data = {
                        'id': f"curr_{enroll.id}", # ID falso
                        'year': enroll.classroom.year,
                        'classroom_name': f"{enroll.classroom.name} ({enroll.classroom.segment})",
                        'school_name': 'Lumis School', # Escola atual
                        'status': 'IN_PROGRESS',
                        'status_display': 'Cursando (Atual)',
                        'final_grade': '-',
                        'observation': 'Matrícula Ativa no Sistema',
                        'is_virtual': True # Flag para o front saber que é dados vivo
                    }
                    # Adiciona no topo da lista (já que é o ano atual)
                    if isinstance(response.data, list):
                         response.data.insert(0, current_data)
                    elif 'results' in response.data:
                         response.data['results'].insert(0, current_data)
        
        return response