from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Count, Avg, Q
from django.contrib.auth import get_user_model
User = get_user_model()
from .models import Segment, ClassRoom, Guardian, Student, Enrollment, Subject, TeacherAssignment, Grade, Attendance, AcademicPeriod, LessonPlan
from .serializers import (
    SegmentSerializer, ClassRoomSerializer, StudentSerializer, 
    EnrollmentSerializer, SubjectSerializer, TeacherAssignmentSerializer,
    GradeSerializer, AttendanceSerializer, AcademicPeriodSerializer,
    GuardianSerializer, LessonPlanSerializer, SimpleUserSerializer
)

class SegmentViewSet(viewsets.ModelViewSet):
    queryset = Segment.objects.all()
    serializer_class = SegmentSerializer

class ClassRoomViewSet(viewsets.ModelViewSet):
    queryset = ClassRoom.objects.all()
    serializer_class = ClassRoomSerializer

class GuardianViewSet(viewsets.ModelViewSet):
    queryset = Guardian.objects.all().order_by('name')
    serializer_class = GuardianSerializer
    search_fields = ['name', 'cpf', 'email']

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all().order_by('name')
    serializer_class = StudentSerializer
    # Habilita busca por nome e matrícula na URL (ex: ?search=Maria)
    search_fields = ['name', 'registration_number'] 

class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.all().order_by('student__name')
    serializer_class = EnrollmentSerializer
    filterset_fields = ['classroom', 'student']

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
        """
        Retorna apenas as atribuições do professor logado.
        URL: /api/assignments/my_classes/
        """
        user = request.user
        # Filtra onde o professor é o usuário logado
        my_assignments = TeacherAssignment.objects.filter(teacher=user)
        
        # Usa o mesmo serializer para formatar os dados
        serializer = self.get_serializer(my_assignments, many=True)
        return Response(serializer.data)

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
        # 1. Cards (KPIs)
        total_students = Student.objects.count()
        total_classes = ClassRoom.objects.count()
        total_teachers = User.objects.filter(is_teacher=True).count() 
        risk_students = 0 
        students_by_segment = Student.objects.values('enrollment__classroom__segment__name').annotate(total=Count('id')).order_by('total')
        avg_by_subject = Grade.objects.values('subject__name').annotate(avg=Avg('value')).order_by('-avg')[:5]

        data = {
            'cards': {
                'students': total_students,
                'classes': total_classes,
                'teachers': total_teachers,
                'risk': risk_students
            },
            'charts': {
                'segment_distribution': students_by_segment,
                'subject_performance': avg_by_subject
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