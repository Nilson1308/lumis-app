from rest_framework import viewsets
from .models import Segment, ClassRoom, Student, Enrollment, Subject, TeacherAssignment
from .serializers import (
    SegmentSerializer, ClassRoomSerializer, StudentSerializer, 
    EnrollmentSerializer, SubjectSerializer, TeacherAssignmentSerializer
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