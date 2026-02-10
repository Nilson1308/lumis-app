from rest_framework import serializers
from django.contrib.auth import get_user_model # <--- IMPORTAÇÃO CORRETA
from .models import Announcement, AnnouncementReadStatus

# Pega o modelo de usuário configurado no settings.py (core.User)
User = get_user_model() 

class AnnouncementReadStatusSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = AnnouncementReadStatus
        fields = ['user_name', 'read_at']

class AnnouncementSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender_id = serializers.PrimaryKeyRelatedField(read_only=True, source='sender')
    is_read = serializers.SerializerMethodField()
    read_stats = serializers.SerializerMethodField()
    
    # Campo para selecionar destinatários (agora usando o User correto)
    recipient_ids = serializers.PrimaryKeyRelatedField(
        source='recipients', 
        many=True, 
        queryset=User.objects.all(), # <--- AGORA VAI FUNCIONAR
        write_only=False
    )

    class Meta:
        model = Announcement
        fields = ['id', 'sender_id', 'sender_name', 'title', 'message', 'priority', 'created_at', 'is_read', 'read_stats', 'recipient_ids']

    def get_is_read(self, obj):
        user = self.context['request'].user
        if not user.is_authenticated:
            return False
        try:
            status = obj.announcementreadstatus_set.get(user=user)
            return status.read_at is not None
        except:
            return False

    def get_read_stats(self, obj):
        user = self.context['request'].user
        # Lógica para mostrar stats apenas para quem enviou ou admins
        if user == obj.sender or user.is_superuser:
            total = obj.recipients.count()
            read = obj.announcementreadstatus_set.filter(read_at__isnull=False).count()
            return f"{read}/{total}"
        return None