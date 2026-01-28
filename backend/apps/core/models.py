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

class SchoolAccount(models.Model):
    """
    Configurações da Conta (Tenant) para White Label.
    Geralmente haverá apenas 1 registro por instância do sistema.
    """
    name = models.CharField("Nome da Escola", max_length=100)
    slug = models.SlugField(unique=True, help_text="Identificador único (ex: saint-thomas)")
    
    # Identidade Visual
    logo = models.ImageField("Logotipo", upload_to='school_logos/', null=True, blank=True)
    icon = models.ImageField("Ícone (Favicon/Mobile)", upload_to='school_icons/', null=True, blank=True)
    primary_color = models.CharField("Cor Primária (Hex)", max_length=7, default='#6366f1', help_text="Ex: #3B82F6")
    secondary_color = models.CharField("Cor Secundária (Hex)", max_length=7, default='#475569', help_text="Ex: #1E293B")
    
    # Dados Institucionais (Rodapé/Contato)
    email = models.EmailField("Email de Contato", blank=True)
    phone = models.CharField("Telefone", max_length=20, blank=True)
    address = models.TextField("Endereço", blank=True)
    website = models.URLField("Site Oficial", blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Configuração da Escola"
        verbose_name_plural = "Configurações da Escola"