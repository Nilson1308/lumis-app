from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    is_teacher = models.BooleanField(default=False)
    is_coordinator = models.BooleanField(default=False)
    
    class Meta:
        # Isso garante que o Django use a tabela padrão 'auth_user' se quiser,
        # mas recomenda-se deixar o Django gerenciar.
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'

    def __str__(self):
        return self.username