from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import WeeklyReport, ClassObservation, MeetingMinute, StudentReport

User = get_user_model()

class WeeklyReportSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    # Campo para selecionar coordenadores destinatários
    recipient_ids = serializers.PrimaryKeyRelatedField(
        source='recipients',
        many=True,
        queryset=User.objects.filter(groups__name='Coordenacao'),
        required=True,
        help_text="Selecione pelo menos um coordenador"
    )

    class Meta:
        model = WeeklyReport
        fields = '__all__'
        read_only_fields = ['author', 'created_at'] # O backend define isto automaticamente
    
    def validate_recipient_ids(self, value):
        """Valida que pelo menos um coordenador foi selecionado"""
        if not value or len(value) == 0:
            raise serializers.ValidationError("É obrigatório selecionar pelo menos um coordenador para envio.")
        return value
    
    def validate_start_date(self, value):
        """Permite criar relatórios semanários futuros"""
        # Removida validação que bloqueava datas futuras
        return value
    
    def validate_end_date(self, value):
        """Permite criar relatórios semanários futuros"""
        # Removida validação que bloqueava datas futuras
        return value
    
    def validate(self, data):
        """Validações adicionais"""
        print("=== DEBUG: Serializer.validate ===")
        print("data recebido:", data)
        
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        recipients = data.get('recipients', [])
        
        print("recipients no validate:", recipients)
        print("recipients type:", type(recipients))
        print("recipients is None:", recipients is None)
        print("recipients is list:", isinstance(recipients, list))
        print("recipients length:", len(recipients) if recipients else 0)
        
        # Validação CRÍTICA: pelo menos um coordenador deve ser selecionado
        # Verifica tanto se está vazio quanto se é None
        if recipients is None or (isinstance(recipients, list) and len(recipients) == 0):
            print("DEBUG: BLOQUEANDO no serializer - Sem recipients")
            raise serializers.ValidationError({
                'recipient_ids': ['É obrigatório selecionar pelo menos um coordenador para envio.']
            })
        
        # Validação: end_date deve ser maior ou igual a start_date
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                'end_date': ['A data de fim deve ser maior ou igual à data de início.']
            })
        
        print("DEBUG: Validação serializer passou")
        return data

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