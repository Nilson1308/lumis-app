from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.academic.models import ClassRoom, Enrollment, Guardian, TeacherAssignment
from apps.core.audit import register_access_audit

from .models import SharedDocument, SharedDocumentReadStatus
from .serializers import MAX_FILE_BYTES, SharedDocumentListSerializer, SharedDocumentWriteSerializer
from .services import (
    is_guardian,
    is_power_user,
    is_teacher,
    publish_document,
)


class SharedDocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return SharedDocumentWriteSerializer
        return SharedDocumentListSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = SharedDocument.objects.select_related(
            'classroom', 'classroom__segment', 'segment', 'uploaded_by'
        )

        if is_power_user(user):
            return self._apply_filters(queryset)

        queryset = queryset.filter(is_active=True)
        return self._apply_filters(self._filter_by_audience(user, queryset))

    def _apply_filters(self, queryset):
        params = self.request.query_params
        search = (params.get('search') or '').strip()
        category = (params.get('category') or '').strip()
        target_audience = (params.get('target_audience') or '').strip()
        classroom_id = params.get('classroom')
        segment_id = params.get('segment')
        is_active = params.get('is_active')
        unread_only = params.get('unread_only')

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        if category:
            queryset = queryset.filter(category=category)
        if target_audience:
            queryset = queryset.filter(target_audience=target_audience)
        if classroom_id:
            queryset = queryset.filter(classroom_id=classroom_id)
        if segment_id:
            queryset = queryset.filter(
                Q(segment_id=segment_id) | Q(classroom__segment_id=segment_id)
            )
        if is_active in ('true', 'false') and is_power_user(self.request.user):
            queryset = queryset.filter(is_active=(is_active == 'true'))
        if unread_only in ('true', '1') and not is_power_user(self.request.user):
            read_ids = SharedDocumentReadStatus.objects.filter(
                user=self.request.user,
                read_at__isnull=False,
            ).values_list('document_id', flat=True)
            queryset = queryset.exclude(id__in=read_ids)
        return queryset.distinct()

    def _filter_by_audience(self, user, queryset):
        if is_teacher(user):
            classroom_ids = list(
                TeacherAssignment.objects.filter(teacher=user).values_list('classroom_id', flat=True)
            )
            segment_ids = list(
                ClassRoom.objects.filter(id__in=classroom_ids).values_list('segment_id', flat=True)
            )
            return queryset.filter(
                Q(target_audience='ALL') |
                Q(target_audience='TEACHERS') |
                Q(target_audience='CLASSROOM', classroom_id__in=classroom_ids) |
                Q(target_audience='SEGMENT', segment_id__in=segment_ids)
            ).distinct()

        if is_guardian(user):
            guardian = Guardian.objects.filter(user=user).first()
            if not guardian:
                return queryset.filter(target_audience__in=['ALL', 'GUARDIANS'])

            classroom_ids = list(
                Enrollment.objects.filter(student__guardians=guardian).values_list('classroom_id', flat=True)
            )
            segment_ids = list(
                ClassRoom.objects.filter(id__in=classroom_ids).values_list('segment_id', flat=True)
            )

            return queryset.filter(
                Q(target_audience='ALL') |
                Q(target_audience='GUARDIANS') |
                Q(target_audience='CLASSROOM', classroom_id__in=classroom_ids) |
                Q(target_audience='SEGMENT', segment_id__in=segment_ids)
            ).distinct()

        return queryset.filter(target_audience='ALL')

    def _assert_can_manage(self):
        if not is_power_user(self.request.user):
            return Response({'error': 'Ação não permitida.'}, status=status.HTTP_403_FORBIDDEN)
        return None

    def create(self, request, *args, **kwargs):
        denied = self._assert_can_manage()
        if denied:
            return denied
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        denied = self._assert_can_manage()
        if denied:
            return denied
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        denied = self._assert_can_manage()
        if denied:
            return denied
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        denied = self._assert_can_manage()
        if denied:
            return denied
        instance = self.get_object()
        doc_id = instance.id
        title = instance.title
        response = super().destroy(request, *args, **kwargs)
        register_access_audit(
            request=request,
            action='SHARED_DOCUMENT_DELETE',
            resource_type='shared_document',
            resource_id=doc_id,
            details={'title': title},
        )
        return response

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        document = self.get_object()
        if is_power_user(request.user):
            return Response({'error': 'Ação não disponível para gestores.'}, status=status.HTTP_403_FORBIDDEN)

        status_obj, _ = SharedDocumentReadStatus.objects.get_or_create(
            document=document,
            user=request.user,
        )
        if not status_obj.read_at:
            status_obj.read_at = timezone.now()
            status_obj.save(update_fields=['read_at'])
        return Response({'status': 'read', 'read_at': status_obj.read_at})

    @action(detail=True, methods=['get'], url_path='read-report')
    def read_report(self, request, pk=None):
        if not is_power_user(request.user):
            return Response({'error': 'Ação não permitida.'}, status=status.HTTP_403_FORBIDDEN)

        document = self.get_object()
        statuses = (
            SharedDocumentReadStatus.objects.filter(document=document)
            .select_related('user')
            .order_by('user__first_name', 'user__username')
        )
        data = []
        for item in statuses:
            user = item.user
            data.append({
                'user_id': user.id,
                'name': user.get_full_name() or user.username,
                'read': item.read_at is not None,
                'read_at': item.read_at,
            })
        return Response(data)

    def _file_from_request(self):
        upload = self.request.FILES.get('file')
        if not upload:
            return None
        if not hasattr(upload, 'read'):
            raise ValidationError({'file': ['Arquivo inválido.']})
        if upload.size > MAX_FILE_BYTES:
            raise ValidationError({'file': ['O arquivo deve ter no máximo 10 MB.']})
        return upload

    def perform_create(self, serializer):
        upload = self._file_from_request()
        doc = serializer.save(uploaded_by=self.request.user, file=upload)
        if doc.is_active:
            publish_document(doc, self.request.user)
        register_access_audit(
            request=self.request,
            action='SHARED_DOCUMENT_CREATE',
            resource_type='shared_document',
            resource_id=doc.id,
            details={
                'title': doc.title,
                'target_audience': doc.target_audience,
                'classroom_id': doc.classroom_id,
                'segment_id': doc.segment_id,
            },
        )

    def perform_update(self, serializer):
        upload = self._file_from_request()
        instance = self.get_object()
        was_active = instance.is_active
        extra = {}
        if upload:
            if instance.file:
                instance.file.delete(save=False)
            extra['file'] = upload
            extra['external_link'] = ''
        doc = serializer.save(**extra)
        if doc.is_active and not was_active:
            publish_document(doc, self.request.user)
        register_access_audit(
            request=self.request,
            action='SHARED_DOCUMENT_UPDATE',
            resource_type='shared_document',
            resource_id=doc.id,
            details={'title': doc.title, 'is_active': doc.is_active},
        )
