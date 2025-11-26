from rest_framework import serializers
from .models import WeeklyReport, ClassObservation, MeetingMinute

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