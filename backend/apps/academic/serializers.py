from rest_framework import serializers
from .models import Segment, ClassRoom, Subject, Student, Enrollment, TeacherAssignment, Grade, Attendance, AcademicPeriod

class SegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Segment
        fields = '__all__'

class ClassRoomSerializer(serializers.ModelSerializer):
    # Para mostrar o nome do segmento em vez do ID, usamos um truque simples:
    segment_name = serializers.CharField(source='segment.name', read_only=True)

    class Meta:
        model = ClassRoom
        fields = ['id', 'name', 'year', 'segment', 'segment_name']

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = '__all__'

class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    classroom_name = serializers.CharField(source='classroom.name', read_only=True)
    classroom_year = serializers.IntegerField(source='classroom.year', read_only=True) # Para mostrar no erro se precisar

    class Meta:
        model = Enrollment
        fields = ['id', 'student', 'student_name', 'classroom', 'classroom_name', 'classroom_year', 'date_enrolled', 'active']

    def validate(self, data):
        """
        Regra: Um aluno não pode ter matrícula ATIVA em duas turmas 
        do MESMO ANO LETIVO.
        """
        student = data.get('student')
        classroom = data.get('classroom')
        
        # Se for edição, precisamos pegar os dados atuais caso não venham no request
        if self.instance:
            student = student or self.instance.student
            classroom = classroom or self.instance.classroom

        # Verifica se já existe matrícula ativa para este aluno, neste ano, excluindo a própria (em caso de edição)
        # classroom__year -> Acessa o ano da turma relacionada
        existing_enrollment = Enrollment.objects.filter(
            student=student,
            classroom__year=classroom.year,
            active=True
        )

        if self.instance:
            existing_enrollment = existing_enrollment.exclude(pk=self.instance.pk)

        if existing_enrollment.exists():
            # Pega o nome da turma onde ele já está para mostrar no erro
            current_class = existing_enrollment.first().classroom.name
            raise serializers.ValidationError(
                f"Conflito: O aluno {student.name} já está matriculado na turma '{current_class}' neste ano letivo ({classroom.year})."
            )

        return data

class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'

class TeacherAssignmentSerializer(serializers.ModelSerializer):
    # Campos de leitura (para mostrar nomes na tabela)
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    classroom_name = serializers.CharField(source='classroom.name', read_only=True)
    classroom_year = serializers.IntegerField(source='classroom.year', read_only=True)

    class Meta:
        model = TeacherAssignment
        fields = ['id', 'teacher', 'teacher_name', 'subject', 'subject_name', 'classroom', 'classroom_name', 'classroom_year']

class GradeSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='enrollment.student.name', read_only=True)
    
    class Meta:
        model = Grade
        fields = '__all__'

class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='enrollment.student.name', read_only=True)

    class Meta:
        model = Attendance
        fields = '__all__'

class AcademicPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicPeriod
        fields = '__all__'