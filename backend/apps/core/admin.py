from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import User, SchoolAccount

# --- FUNÇÃO AUXILIAR: GERAR HTML DO EMAIL ---
def montar_email_credenciais(user, password, school):
    # 1. Definição da Identidade Visual
    if school and school.logo:
        # Identidade da ESCOLA
        # Ajuste a URL base conforme seu domínio real
        base_url = "https://app.sthomasmogi.com.br"
        logo_url = f"{base_url}{school.logo.url}"
        primary_color = school.primary_color or "#1e3a8a" # Azul padrão se não tiver cor
        school_name = school.name
    else:
        # Identidade LUMIS (Fallback)
        # Usei uma URL de placeholder para o logo da Lumis, depois você pode trocar
        logo_url = "https://via.placeholder.com/150x50/6366f1/ffffff?text=Lumis+System" 
        primary_color = "#6366f1" # Roxo Lumis
        school_name = "Lumis Educacional"

    # 2. Template HTML (CSS Inline é obrigatório para emails)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f4f4f5; }}
            .container {{ max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .header {{ background-color: {primary_color}; padding: 30px; text-align: center; }}
            .header img {{ max-height: 60px; max-width: 200px; object-fit: contain; background: rgba(255,255,255,0.9); padding: 5px; border-radius: 4px; }}
            .content {{ padding: 40px 30px; color: #374151; }}
            .h1 {{ font-size: 24px; font-weight: bold; margin-bottom: 20px; color: #1f2937; }}
            .p {{ font-size: 16px; line-height: 1.6; margin-bottom: 20px; }}
            .box {{ background-color: #f3f4f6; border-left: 5px solid {primary_color}; padding: 20px; border-radius: 4px; margin: 20px 0; }}
            .label {{ font-weight: bold; font-size: 12px; text-transform: uppercase; color: #6b7280; display: block; margin-bottom: 4px; }}
            .value {{ font-size: 18px; font-weight: bold; color: #111827; display: block; margin-bottom: 12px; font-family: monospace; }}
            .btn {{ display: inline-block; background-color: {primary_color}; color: #ffffff; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: bold; text-align: center; margin-top: 10px; }}
            .footer {{ background-color: #f9fafb; padding: 20px; text-align: center; font-size: 12px; color: #9ca3af; border-top: 1px solid #e5e7eb; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="{logo_url}" alt="{school_name}">
            </div>
            <div class="content">
                <div class="h1">Bem-vindo(a), {user.first_name}!</div>
                <div class="p">
                    Seu cadastro no portal <strong>{school_name}</strong> foi realizado com sucesso.
                    Abaixo estão suas credenciais exclusivas de acesso.
                </div>
                
                <div class="box">
                    <span class="label">Link de Acesso</span>
                    <span class="value" style="font-size: 14px;">https://app.sthomasmogi.com.br</span>
                    
                    <span class="label">Usuário</span>
                    <span class="value">{user.username}</span>
                    
                    <span class="label">Senha Provisória</span>
                    <span class="value">{password}</span>
                </div>
                
                <div style="text-align: center;">
                    <a href="https://app.sthomasmogi.com.br" class="btn" style="color: #ffffff;">Acessar Portal Agora</a>
                </div>
            </div>
            <div class="footer">
                Enviado automaticamente pelo Sistema {school_name}.<br>
                Não responda a este e-mail.
            </div>
        </div>
    </body>
    </html>
    """
    return html_content, school_name

# --- AÇÃO PERSONALIZADA: GERAR SENHA E ENVIAR ---
@admin.action(description='✉️ Gerar Nova Senha e Enviar por Email')
def enviar_credenciais(modeladmin, request, queryset):
    count = 0
    ignored = 0
    
    # Busca dados da escola (Identidade Visual)
    school = SchoolAccount.objects.first()
    
    # Caracteres amigáveis para senha
    chars = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'

    for user in queryset:
        # 1. Validação
        if not user.email or "@lumis.com" in user.email or "@pais.com" in user.email:
            ignored += 1
            continue

        # 2. Gerar Senha
        new_password = get_random_string(length=8, allowed_chars=chars)
        
        # 3. Salvar
        user.set_password(new_password)
        user.save()

        # 4. Montar E-mail (HTML)
        html_content, school_name = montar_email_credenciais(user, new_password, school)
        plain_message = strip_tags(html_content) # Versão texto puro para clientes antigos
        
        subject = f"Acesso Liberado - {school_name}"
        
        # 5. Enviar
        try:
            send_mail(
                subject,
                plain_message, # Mensagem texto puro (obrigatório)
                None,
                [user.email],
                html_message=html_content, # Mensagem HTML (opcional mas é o que queremos)
                fail_silently=False,
            )
            count += 1
        except Exception as e:
            modeladmin.message_user(request, f"Erro ao enviar para {user.username}: {e}", level='ERROR')

    # Feedback
    if count > 0:
        modeladmin.message_user(request, f"{count} credenciais enviadas com sucesso!", level='SUCCESS')
    if ignored > 0:
        modeladmin.message_user(request, f"{ignored} ignorados (email inválido/fake).", level='WARNING')

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'first_name', 'email', 'is_staff', 'is_active')
    search_fields = ('username', 'first_name', 'email')
    list_filter = ('is_staff', 'is_superuser', 'groups')
    
    # Adiciona o botão na lista de ações
    actions = [enviar_credenciais]

@admin.register(SchoolAccount)
class SchoolAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'primary_color')
    fieldsets = (
        ('Identificação', {'fields': ('name', 'slug', 'logo', 'icon')}),
        ('Cores do Sistema', {'fields': ('primary_color', 'secondary_color')}),
        ('Contato', {'fields': ('email', 'phone', 'address', 'website')}),
    )