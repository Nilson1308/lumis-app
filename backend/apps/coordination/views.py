from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from apps.core.audit import register_access_audit
from .models import WeeklyReport, ClassObservation, MeetingMinute, StudentReport
from .serializers import WeeklyReportSerializer, ClassObservationSerializer, MeetingMinuteSerializer, StudentReportSerializer

class WeeklyReportViewSet(viewsets.ModelViewSet):
    queryset = WeeklyReport.objects.all().order_by('-start_date')
    serializer_class = WeeklyReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser, JSONParser)  # Permite upload de arquivos
    filterset_fields = ['author', 'start_date']

    # Auto-atribui o autor ao criar
    def perform_create(self, serializer):
        # Debug: verificar dados recebidos
        print("=== DEBUG: perform_create ===")
        print("request.data:", self.request.data)
        print("request.data type:", type(self.request.data))
        
        # Validação adicional de segurança: garante que recipient_ids foi enviado
        # Tenta getlist primeiro (FormData), depois get normal (JSON)
        recipient_ids = self.request.data.getlist('recipient_ids') if hasattr(self.request.data, 'getlist') else self.request.data.get('recipient_ids', [])
        
        print("recipient_ids recebido:", recipient_ids)
        print("recipient_ids type:", type(recipient_ids))
        print("recipient_ids length:", len(recipient_ids) if recipient_ids else 0)
        
        # Se for string única, converte para lista
        if isinstance(recipient_ids, str):
            recipient_ids = [recipient_ids]
        
        if not recipient_ids or len(recipient_ids) == 0:
            print("DEBUG: BLOQUEANDO - Sem recipient_ids")
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'recipient_ids': ['É obrigatório selecionar pelo menos um coordenador para envio.']})
        
        print("DEBUG: Validação passou, salvando...")
        report = serializer.save(author=self.request.user)
        register_access_audit(
            request=self.request,
            action='WEEKLY_REPORT_CREATE',
            resource_type='weekly_report',
            resource_id=report.id,
            details={'start_date': str(report.start_date), 'end_date': str(report.end_date)}
        )

    def perform_update(self, serializer):
        report = serializer.save()
        register_access_audit(
            request=self.request,
            action='WEEKLY_REPORT_UPDATE',
            resource_type='weekly_report',
            resource_id=report.id,
            details={'start_date': str(report.start_date), 'end_date': str(report.end_date)}
        )

    def perform_destroy(self, instance):
        report_id = instance.id
        super().perform_destroy(instance)
        register_access_audit(
            request=self.request,
            action='WEEKLY_REPORT_DELETE',
            resource_type='weekly_report',
            resource_id=report_id
        )

class ClassObservationViewSet(viewsets.ModelViewSet):
    queryset = ClassObservation.objects.all().order_by('-date')
    serializer_class = ClassObservationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['assignment__teacher', 'assignment__classroom', 'coordinator']

    def perform_create(self, serializer):
        serializer.save(coordinator=self.request.user)

    def perform_create(self, serializer):
        instance = serializer.save(coordinator=self.request.user)
        register_access_audit(
            request=self.request,
            action='CLASS_OBSERVATION_CREATE',
            resource_type='class_observation',
            resource_id=instance.id,
            details={'assignment_id': instance.assignment_id, 'feedback_given': instance.feedback_given}
        )
        
        if instance.feedback_given:
            self.notify_teacher(instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        register_access_audit(
            request=self.request,
            action='CLASS_OBSERVATION_UPDATE',
            resource_type='class_observation',
            resource_id=instance.id,
            details={'assignment_id': instance.assignment_id, 'feedback_given': instance.feedback_given}
        )
        
        if instance.feedback_given:
            self.notify_teacher(instance)

    def perform_destroy(self, instance):
        obs_id = instance.id
        super().perform_destroy(instance)
        register_access_audit(
            request=self.request,
            action='CLASS_OBSERVATION_DELETE',
            resource_type='class_observation',
            resource_id=obs_id
        )

    def notify_teacher(self, observation):
        """
        Método placeholder para lógica futura de notificação.
        Aqui você poderá:
        1. Criar um registro na tabela 'Notification'
        2. Enviar e-mail
        3. Enviar WebSocket msg
        """
        teacher = observation.assignment.teacher
        print(f" TODO: Enviar notificação para o professor {teacher.first_name} sobre a observação {observation.id}")

    def get_queryset(self):
        user = self.request.user
        queryset = ClassObservation.objects.all().order_by('-date')

        # Se for professor, vê apenas as observações das SUAS aulas e que o feedback foi LIBERADO
        if hasattr(user, 'teacher_profile') or not (user.is_superuser or user.groups.filter(name='Coordenacao').exists()):
             return queryset.filter(
                 assignment__teacher=user, 
                 feedback_given=True
             )
        
        return queryset

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        observation = self.get_object()
        if not observation.is_read:
            observation.is_read = True
            observation.save()
        return Response({'status': 'marked as read'})

class MeetingMinuteViewSet(viewsets.ModelViewSet):
    queryset = MeetingMinute.objects.all().order_by('-date')
    serializer_class = MeetingMinuteSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['title', 'content'] # Busca textual no conteúdo da ata

    def perform_create(self, serializer):
        minute = serializer.save(created_by=self.request.user)
        register_access_audit(
            request=self.request,
            action='MEETING_MINUTE_CREATE',
            resource_type='meeting_minute',
            resource_id=minute.id,
            details={'date': str(minute.date), 'title': minute.title}
        )

    def perform_update(self, serializer):
        minute = serializer.save()
        register_access_audit(
            request=self.request,
            action='MEETING_MINUTE_UPDATE',
            resource_type='meeting_minute',
            resource_id=minute.id,
            details={'date': str(minute.date), 'title': minute.title}
        )

    def perform_destroy(self, instance):
        minute_id = instance.id
        super().perform_destroy(instance)
        register_access_audit(
            request=self.request,
            action='MEETING_MINUTE_DELETE',
            resource_type='meeting_minute',
            resource_id=minute_id
        )

class StudentReportViewSet(viewsets.ModelViewSet):
    queryset = StudentReport.objects.all().order_by('-date')
    serializer_class = StudentReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = StudentReport.objects.all().order_by('-date')

        # 1. Pais: Verão apenas APROVADOS e VISÍVEIS dos seus filhos
        if hasattr(user, 'guardian_profile'):
            queryset = queryset.filter(
                student__guardians=user.guardian_profile,
                status='APPROVED',
                visible_to_family=True
            )
        
        # 2. Professores: Veem os seus
        elif not (user.is_superuser or user.groups.filter(name='Coordenacao').exists()):
            queryset = queryset.filter(teacher=user)

        # --- FILTRO POR ALUNO (Query Param) ---
        # Permite ?student=5 na URL
        student_id = self.request.query_params.get('student')
        if student_id:
            try:
                student_id = int(student_id)
            except (TypeError, ValueError):
                return queryset.none()
            queryset = queryset.filter(student_id=student_id)
            
        return queryset

    def perform_create(self, serializer):
        # SEGURANÇA: Ao criar, força PENDING e associa o professor logado
        report = serializer.save(teacher=self.request.user, status='PENDING', visible_to_family=False)
        register_access_audit(
            request=self.request,
            action='STUDENT_REPORT_CREATE',
            resource_type='student_report',
            resource_id=report.id,
            student_id=report.student_id,
            details={'status': report.status}
        )

    def perform_update(self, serializer):
        user = self.request.user
        
        # Verifica se é Coordenação ou Admin
        is_coordination = user.is_superuser or user.groups.filter(name='Coordenacao').exists()
        
        if is_coordination:
            # Coordenação pode alterar tudo (Status, Visibilidade, Comentário)
            previous_status = serializer.instance.status if serializer.instance else None
            report = serializer.save()
            if previous_status != report.status:
                register_access_audit(
                    request=self.request,
                    action='STUDENT_REPORT_STATUS_CHANGE',
                    resource_type='student_report',
                    resource_id=report.id,
                    student_id=report.student_id,
                    details={'previous_status': previous_status, 'new_status': report.status}
                )
        else:
            # Professor: Se editar o texto, o status volta (ou mantém) como PENDING e esconde da família
            # Isso impede que o professor edite um relatório Aprovado e mude o conteúdo sem nova revisão
            report = serializer.save(status='PENDING', visible_to_family=False)
            register_access_audit(
                request=self.request,
                action='STUDENT_REPORT_EDIT_BY_TEACHER',
                resource_type='student_report',
                resource_id=report.id,
                student_id=report.student_id,
                details={'status_forced': 'PENDING'}
            )

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if hasattr(request.user, 'guardian_profile'):
            register_access_audit(
                request=request,
                action='PARENT_STUDENT_REPORT_LIST_VIEW',
                resource_type='student_report_list',
                resource_id=request.query_params.get('student', ''),
                student_id=request.query_params.get('student'),
                details={'query_student': request.query_params.get('student')}
            )
        return response

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        if hasattr(request.user, 'guardian_profile'):
            report = self.get_object()
            register_access_audit(
                request=request,
                action='PARENT_STUDENT_REPORT_DETAIL_VIEW',
                resource_type='student_report',
                resource_id=report.id,
                student_id=report.student_id
            )
        return response