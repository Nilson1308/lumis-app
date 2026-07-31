from rest_framework import serializers

from .models import SharedDocument, SharedDocumentReadStatus
from .services import is_power_user

MAX_FILE_BYTES = 10 * 1024 * 1024


class SharedDocumentListSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source='get_category_display', read_only=True)
    target_audience_label = serializers.CharField(source='get_target_audience_display', read_only=True)
    uploaded_by_name = serializers.SerializerMethodField()
    classroom_name = serializers.CharField(source='classroom.name', read_only=True, default=None)
    segment_name = serializers.CharField(source='segment.name', read_only=True, default=None)
    file_url = serializers.SerializerMethodField()
    has_file = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()
    read_at = serializers.SerializerMethodField()
    read_stats = serializers.SerializerMethodField()

    class Meta:
        model = SharedDocument
        fields = [
            'id',
            'title',
            'description',
            'category',
            'category_label',
            'target_audience',
            'target_audience_label',
            'classroom',
            'classroom_name',
            'segment',
            'segment_name',
            'file_url',
            'external_link',
            'has_file',
            'uploaded_by',
            'uploaded_by_name',
            'is_active',
            'is_read',
            'read_at',
            'read_stats',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'category_label',
            'target_audience_label',
            'classroom_name',
            'segment_name',
            'file_url',
            'has_file',
            'uploaded_by',
            'uploaded_by_name',
            'is_read',
            'read_at',
            'read_stats',
            'created_at',
            'updated_at',
        ]

    def get_uploaded_by_name(self, obj):
        if not obj.uploaded_by:
            return None
        return obj.uploaded_by.get_full_name() or obj.uploaded_by.username

    def get_file_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url

    def get_has_file(self, obj):
        return bool(obj.file)

    def _get_read_status(self, obj):
        cache = self.context.setdefault('_read_status_cache', {})
        if obj.id not in cache:
            user = self.context.get('request').user
            cache[obj.id] = SharedDocumentReadStatus.objects.filter(
                document_id=obj.id, user=user
            ).first()
        return cache[obj.id]

    def get_is_read(self, obj):
        request = self.context.get('request')
        if not request or is_power_user(request.user):
            return None
        status_obj = self._get_read_status(obj)
        return bool(status_obj and status_obj.read_at)

    def get_read_at(self, obj):
        request = self.context.get('request')
        if not request or is_power_user(request.user):
            return None
        status_obj = self._get_read_status(obj)
        return status_obj.read_at if status_obj else None

    def get_read_stats(self, obj):
        request = self.context.get('request')
        if not request or not is_power_user(request.user):
            return None
        total = obj.read_statuses.count()
        read = obj.read_statuses.filter(read_at__isnull=False).count()
        return {'total': total, 'read': read, 'unread': total - read}


class SharedDocumentWriteSerializer(serializers.ModelSerializer):
    """Arquivo enviado via multipart em SharedDocumentViewSet.perform_create/update."""

    is_active = serializers.BooleanField(required=False)

    class Meta:
        model = SharedDocument
        fields = [
            'title',
            'description',
            'category',
            'target_audience',
            'classroom',
            'segment',
            'external_link',
            'is_active',
        ]

    def validate_title(self, value):
        cleaned = (value or '').strip()
        if not cleaned:
            raise serializers.ValidationError('Informe o título do documento.')
        return cleaned

    def validate(self, attrs):
        target = attrs.get(
            'target_audience',
            getattr(self.instance, 'target_audience', 'ALL'),
        )
        classroom = attrs.get('classroom', getattr(self.instance, 'classroom', None))
        segment = attrs.get('segment', getattr(self.instance, 'segment', None))
        external_link = attrs.get(
            'external_link',
            getattr(self.instance, 'external_link', ''),
        )
        has_existing_file = bool(getattr(self.instance, 'file', None))
        has_new_file = bool(self.context.get('request') and self.context['request'].FILES.get('file'))

        if target == 'CLASSROOM' and not classroom:
            raise serializers.ValidationError({'classroom': 'Selecione a turma.'})
        if target == 'SEGMENT' and not segment:
            raise serializers.ValidationError({'segment': 'Selecione o segmento/série.'})
        if target != 'CLASSROOM':
            attrs['classroom'] = None
        if target != 'SEGMENT':
            attrs['segment'] = None
        if not external_link and not has_existing_file and not has_new_file:
            raise serializers.ValidationError(
                'Informe um arquivo ou um link externo.'
            )
        if external_link and has_new_file:
            raise serializers.ValidationError(
                'Use apenas arquivo ou link externo, não ambos.'
            )
        return attrs
