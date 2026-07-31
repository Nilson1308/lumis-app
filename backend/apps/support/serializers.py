from rest_framework import serializers

from .models import SupportTicket, SupportTicketReply

MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024


class SupportTicketReplySerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicketReply
        fields = [
            'id',
            'author',
            'author_name',
            'message',
            'created_at',
        ]
        read_only_fields = fields

    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.username


class SupportTicketListSerializer(serializers.ModelSerializer):
    requester_name = serializers.SerializerMethodField()
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    has_attachment = serializers.SerializerMethodField()
    replies_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            'id',
            'occurred_date',
            'occurred_time',
            'description',
            'status',
            'status_label',
            'has_attachment',
            'replies_count',
            'requester',
            'requester_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'status',
            'status_label',
            'has_attachment',
            'replies_count',
            'requester',
            'requester_name',
            'created_at',
            'updated_at',
        ]

    def get_requester_name(self, obj):
        return obj.requester.get_full_name() or obj.requester.username

    def get_has_attachment(self, obj):
        return bool(obj.attachment)


class SupportTicketDetailSerializer(SupportTicketListSerializer):
    attachment = serializers.FileField(read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta(SupportTicketListSerializer.Meta):
        fields = SupportTicketListSerializer.Meta.fields + ['attachment', 'replies']

    def get_replies(self, obj):
        qs = obj.replies.filter(is_internal=False).select_related('author')
        return SupportTicketReplySerializer(qs, many=True).data


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    """Anexo é tratado em SupportTicketViewSet.perform_create via request.FILES."""

    class Meta:
        model = SupportTicket
        fields = [
            'occurred_date',
            'occurred_time',
            'description',
        ]

    def validate_description(self, value):
        cleaned = (value or '').strip()
        if not cleaned:
            raise serializers.ValidationError('Informe a descrição do chamado.')
        return cleaned
