from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import User, SchoolAccount, Notification, AccessAuditLog

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    # Transforma os objetos Group em uma lista de strings: ['Professores', 'Coordenacao']
    groups = serializers.SlugRelatedField(
        many=True, 
        read_only=True, 
        slug_field='name'
    )

    class Meta:
        model = User
        # Garanta que 'groups' está na lista, além dos campos padrão
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'groups', 'is_superuser']

class SchoolAccountSerializer(serializers.ModelSerializer):
    def validate_non_teaching_event_types(self, value):
        from apps.academic.models import SchoolEvent

        if value is None:
            return ['HOLIDAY']
        if not isinstance(value, list):
            raise serializers.ValidationError(
                'Informe uma lista de tipos de evento (ex: ["HOLIDAY", "MEETING"]).'
            )

        allowed = {item for item, _ in SchoolEvent.EVENT_TYPES}
        normalized = []
        invalid = []
        for raw in value:
            item = str(raw).strip().upper()
            if item in allowed and item not in normalized:
                normalized.append(item)
            elif item not in allowed:
                invalid.append(item)

        if invalid:
            raise serializers.ValidationError(
                f"Tipos inválidos: {', '.join(invalid)}. Permitidos: {', '.join(sorted(allowed))}."
            )

        return normalized or ['HOLIDAY']

    class Meta:
        model = SchoolAccount
        fields = [
            'name', 
            'logo',
            'icon',
            'primary_color', 
            'secondary_color', 
            'non_teaching_event_types',
            'enforce_lesson_plan_submission_guard',
            'email', 
            'phone', 
            'address', 
            'website'
        ]

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'link', 'read', 'created_at']


class AccessAuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.SerializerMethodField()
    severity = serializers.SerializerMethodField()

    class Meta:
        model = AccessAuditLog
        fields = [
            'id', 'created_at', 'action', 'resource_type', 'resource_id',
            'student_id', 'ip_address', 'user_agent', 'details',
            'user', 'username', 'full_name', 'severity'
        ]

    def get_full_name(self, obj):
        if not obj.user:
            return ''
        return obj.user.get_full_name() or obj.user.username

    def get_severity(self, obj):
        action = (obj.action or '').upper()
        high_keywords = ('DELETE', 'BLOCK', 'REJECTED', 'CRITICAL', 'STATUS_CHANGE')
        medium_keywords = ('UPDATE', 'SUBMITTED', 'CREATE', 'BULK_SAVE', 'RELEASE')
        if any(keyword in action for keyword in high_keywords):
            return 'HIGH'
        if any(keyword in action for keyword in medium_keywords):
            return 'MEDIUM'
        return 'LOW'