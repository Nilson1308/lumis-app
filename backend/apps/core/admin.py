from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Adiciona nossos campos personalizados na tela de edição
    fieldsets = UserAdmin.fieldsets + (
        ('Cargos do Lumis', {'fields': ('is_teacher', 'is_coordinator')}),
    )
    
    # Colunas que aparecem na lista de usuários
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_teacher', 'is_coordinator', 'is_staff')
    
    # Filtros laterais
    list_filter = ('is_teacher', 'is_coordinator', 'is_staff', 'is_superuser')