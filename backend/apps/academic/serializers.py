from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Segment, ClassRoom, Subject, Guardian, Student, Enrollment,
    TeacherAssignment, Grade, Attendance, AcademicPeriod, LessonPlan, AbsenceJustification, ExtraActivity,
    TaughtContent, SchoolEvent, ClassSchedule, AcademicHistory, LessonPlan, LessonPlanFile
)
User = get_user_model()

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

class GuardianSerializer(serializers.ModelSerializer):
    # Redefinimos explicitamente para garantir que não sejam read_only
    phone = serializers.CharField(required=False)
    secondary_phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Guardian
        fields = [
            'id', 'name', 'cpf', 'rg', 
            'email', 'phone', 'secondary_phone', 
            'profession', 'user'
        ]

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.cpf = validated_data.get('cpf', instance.cpf)
        instance.rg = validated_data.get('rg', instance.rg)
        instance.phone = validated_data.get('phone', instance.phone)
        instance.secondary_phone = validated_data.get('secondary_phone', instance.secondary_phone)
        instance.email = validated_data.get('email', instance.email)
        instance.profession = validated_data.get('profession', instance.profession)
        
        instance.save()
        
        # BÔNUS: Se houver usuário vinculado, sincroniza o email dele também
        if instance.user and instance.email:
            instance.user.email = instance.email
            instance.user.save()
            
        return instance

class ExtraActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtraActivity
        fields = '__all__'

class StudentSerializer(serializers.ModelSerializer):
    guardians_details = GuardianSerializer(source='guardians', many=True, read_only=True)
    guardians = serializers.PrimaryKeyRelatedField(many=True, queryset=Guardian.objects.all(), required=False)
    
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
    unread_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = TeacherAssignment
        fields = ['id', 'teacher', 'teacher_name', 'subject', 'subject_name', 'classroom', 'classroom_name', 'classroom_year', 'unread_count']

    def get_teacher_name(self, obj):
        if obj.teacher:
            return obj.teacher.get_full_name() or obj.teacher.username
        return "Não atribuído"

class GradeSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='enrollment.student.name', read_only=True)
    
    class Meta:
        model = Grade
        fields = '__all__'

class AbsenceJustificationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='attendance.enrollment.student.name', read_only=True)
    classroom_name = serializers.CharField(source='attendance.enrollment.classroom.name', read_only=True)
    absence_date = serializers.DateField(source='attendance.date', read_only=True)
    
    class Meta:
        model = AbsenceJustification
        fields = '__all__'
        read_only_fields = ['reviewed_by', 'created_at']

class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='enrollment.student.name', read_only=True)
    # Mostra o status do pedido se houver
    justification_status = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = ['id', 'date', 'present', 'justified', 'student_name', 'justification_status', 'enrollment',]

    def get_justification_status(self, obj):
        last_request = obj.justification_request.last()
        return last_request.status if last_request else None

class AcademicPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicPeriod
        fields = '__all__'

class LessonPlanFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonPlanFile
        fields = ['id', 'file', 'name', 'uploaded_at']

class LessonPlanSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='assignment.teacher.get_full_name', read_only=True)
    subject_name = serializers.CharField(source='assignment.subject.name', read_only=True)
    classroom_name = serializers.CharField(source='assignment.classroom.name', read_only=True)

    # 1. ATIVAR RECIPIENTS (Permite escrever e ler)
    recipients = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(groups__name='Coordenacao'),
        many=True, 
        required=False,
        help_text="Selecione pelo menos um coordenador"
    )

    # 2. ATIVAR MÚLTIPLOS ANEXOS (Leitura)
    attachments = LessonPlanFileSerializer(many=True, read_only=True)

    class Meta:
        model = LessonPlan
        fields = [
            'id', 'assignment', 'topic', 'description', 
            'start_date', 'end_date', 'status', 
            'recipients', 'attachments', 'attachment', # Mantemos 'attachment' para ler os antigos se precisar
            'coordinator_note', 'teacher_name', 'subject_name', 
            'classroom_name', 'created_at'
        ]
    
    def validate_start_date(self, value):
        """Permite criar planejamentos semanários futuros"""
        # Removida validação que bloqueava datas futuras
        return value
    
    def validate_end_date(self, value):
        """Permite criar planejamentos semanários futuros"""
        # Removida validação que bloqueava datas futuras
        return value
    
    def validate(self, data):
        """Validações adicionais"""
        recipients = data.get('recipients', [])
        status = data.get('status', self.instance.status if self.instance else 'DRAFT')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        # Validação: Coordenadores obrigatórios quando status é SUBMITTED
        if status == 'SUBMITTED':
            # Se está editando e não veio recipients no data, pega do instance
            if not recipients and self.instance:
                recipients = list(self.instance.recipients.all())
            
            if not recipients or len(recipients) == 0:
                raise serializers.ValidationError({
                    'recipients': ['É obrigatório selecionar pelo menos um coordenador para enviar o planejamento.']
                })
        
        # Validação: end_date deve ser maior ou igual a start_date
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                'end_date': ['A data de fim deve ser maior ou igual à data de início.']
            })
        
        return data

class SimpleUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        # ADICIONE 'first_name' AQUI:
        fields = ['id', 'username', 'first_name', 'full_name', 'email'] 

    def get_full_name(self, obj):
        name = obj.get_full_name()
        if name:
            return f"{name} ({obj.username})"
        return obj.username

class ParentStudentSerializer(serializers.ModelSerializer):
    # Usamos SerializerMethodField para ter controle total da busca
    classroom_name = serializers.SerializerMethodField()
    segment_name = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            'id', 'name', 'registration_number', 'classroom_name', 'segment_name', 'birth_date',
            'emergency_contact', 'allergies', 'medications', # Já usamos antes
            # Novos campos de endereço:
            'zip_code', 'street', 'number', 'complement', 'neighborhood', 'city', 'state'
        ]

    def get_classroom_name(self, obj):
        # Tenta pegar via 'enrollment_set' (padrão) ou 'enrollments' (se foi customizado)
        enrolls = getattr(obj, 'enrollment_set', getattr(obj, 'enrollments', None))
        
        if enrolls:
            last_enrollment = enrolls.last() # Pega a última matrícula
            if last_enrollment and last_enrollment.classroom:
                return last_enrollment.classroom.name
        return "Sem Turma"

    def get_segment_name(self, obj):
        enrolls = getattr(obj, 'enrollment_set', getattr(obj, 'enrollments', None))
        
        if enrolls:
            last_enrollment = enrolls.last()
            if last_enrollment and last_enrollment.classroom and last_enrollment.classroom.segment:
                return last_enrollment.classroom.segment.name
        return "-"

class GuardianProfileUpdateSerializer(serializers.ModelSerializer):
    """ Permite ao pai editar apenas seus dados de contato """
    class Meta:
        model = Guardian
        fields = ['email', 'phone', 'email', 'secondary_phone']

class StudentHealthUpdateSerializer(serializers.ModelSerializer):
    """ Permite ao pai editar apenas saúde e emergência do filho """
    class Meta:
        model = Student
        fields = [
            'emergency_contact', 
            'allergies', 
            'medications',
            'zip_code', 'street', 'number', 'complement', 'neighborhood', 'city', 'state' 
        ]

class TaughtContentSerializer(serializers.ModelSerializer):
    # Campos auxiliares apenas para leitura (display)
    subject_name = serializers.CharField(source='assignment.subject.name', read_only=True)
    classroom_name = serializers.CharField(source='assignment.classroom.name', read_only=True)

    class Meta:
        model = TaughtContent
        fields = ['id', 'assignment', 'date', 'content', 'homework', 'created_at', 'subject_name', 'classroom_name']
    
    def validate_date(self, value):
        """Permite registrar aulas em qualquer data (passado, presente ou futuro)"""
        # Removida validação que bloqueava datas futuras
        # Professores podem planejar e registrar aulas futuras
        return value

class SchoolEventSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source='classroom.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)

    class Meta:
        model = SchoolEvent
        fields = '__all__'

class ClassScheduleSerializer(serializers.ModelSerializer):
    # Campos de Leitura (Para mostrar no calendário)
    subject_name = serializers.CharField(source='assignment.subject.name', read_only=True)
    teacher_name = serializers.CharField(source='assignment.teacher.get_full_name', read_only=True)
    color = serializers.CharField(source='assignment.subject.color', read_only=True, default='#3788d8') # Futuro: cor da matéria

    class Meta:
        model = ClassSchedule
        fields = '__all__'

    def validate(self, data):
        """
        Validação de Segurança:
        Garante que a Atribuição (Assignment) selecionada pertence 
        realmente à Turma (Classroom) que está sendo agendada.
        """
        if 'assignment' in data and 'classroom' in data:
            if data['assignment'].classroom != data['classroom']:
                raise serializers.ValidationError(
                    "Esta atribuição (Matéria/Professor) não pertence a esta turma."
                )
        return data

class AcademicHistorySerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = AcademicHistory
        fields = '__all__'