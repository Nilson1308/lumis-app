from django.db import models
from django.conf import settings

class Announcement(models.Model):
    PRIORITY_CHOICES = [
        ('NORMAL', 'Normal'),
        ('HIGH', 'Alta / Urgente'),
    ]

    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_announcements')
    title = models.CharField("Assunto", max_length=200)
    message = models.TextField("Mensagem")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='NORMAL')
    
    created_at = models.DateTimeField(auto_now_add=True)

    # Relação ManyToMany com tabela intermediária para controlar a leitura
    recipients = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        through='AnnouncementReadStatus',
        related_name='inbox_announcements'
    )

    class Meta:
        ordering = ['-created_at']

class AnnouncementReadStatus(models.Model):
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    read_at = models.DateTimeField(null=True, blank=True) # Se null, não leu.

    class Meta:
        unique_together = ('announcement', 'user') # Um usuário só recebe o mesmo aviso uma vez