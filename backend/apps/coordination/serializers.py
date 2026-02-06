from rest_framework import serializers
from .models import WeeklyReport, ClassObservation, MeetingMinute, StudentReport

class WeeklyReportSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)

    class Meta:
        model = WeeklyReport
        fields = '__all__'
        read_only_fields = ['author', 'created_at'] # O backend define isto automaticamente

class ClassObservationSerializer(serializers.ModelSerializer):
    coordinator_name = serializers.CharField(source='coordinator.get_full_name', read_only=True)
    
    # Campos para mostrar detalhes da aula observada
    teacher_name = serializers.CharField(source='assignment.teacher.get_full_name', read_only=True)
    subject_name = serializers.CharField(source='assignment.subject.name', read_only=True)
    classroom_name = serializers.CharField(source='assignment.classroom.name', read_only=True)

    class Meta:
        model = ClassObservation
        fields = '__all__'
        read_only_fields = ['coordinator'] # Auto-atribuído

class MeetingMinuteSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = MeetingMinute
        fields = '__all__'
        read_only_fields = ['created_by']

class StudentReportSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    
    # Campos para exibição (Read Only)
    type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    level_display = serializers.CharField(source='get_severity_level_display', read_only=True)

    class Meta:
        model = StudentReport
        fields = '__all__'
        read_only_fields = ['teacher', 'created_at']