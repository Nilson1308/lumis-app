from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from .models import Segment, ClassRoom, Student, Enrollment, Subject, TeacherAssignment, Grade, Attendance
from .serializers import (
    SegmentSerializer, ClassRoomSerializer, StudentSerializer, 
    EnrollmentSerializer, SubjectSerializer, TeacherAssignmentSerializer,
    GradeSerializer, AttendanceSerializer
)

class SegmentViewSet(viewsets.ModelViewSet):
    queryset = Segment.objects.all()
    serializer_class = SegmentSerializer

class ClassRoomViewSet(viewsets.ModelViewSet):
    queryset = ClassRoom.objects.all()
    serializer_class = ClassRoomSerializer

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
    filterset_fields = ['enrollment', 'subject', 'enrollment__classroom'] 

class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all().order_by('date')
    serializer_class = AttendanceSerializer
    filterset_fields = ['enrollment', 'subject', 'date']

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