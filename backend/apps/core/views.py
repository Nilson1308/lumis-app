from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import Group
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.utils.html import strip_tags
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from apps.core.pagination import LargeResultsSetPagination
from .models import SchoolAccount, Notification
from .serializers import UserSerializer, SchoolAccountSerializer, NotificationSerializer

User = get_user_model()

class PasswordResetRequestView(APIView):
    permission_classes = [] 

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'E-mail obrigatório'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()
        if user:
            # 1. Gerar Token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_link = f"https://app.sthomasmogi.com.br/reset-password/{uid}/{token}/"
            
            # 2. Identidade Visual (Copia a lógica do Admin)
            school = SchoolAccount.objects.first()
            if school and school.logo:
                base_url = "https://app.sthomasmogi.com.br" # Ajuste se necessário
                logo_url = f"{base_url}{school.logo.url}"
                primary_color = school.primary_color or "#1e3a8a"
                school_name = school.name
            else:
                logo_url = "https://via.placeholder.com/150x50/6366f1/ffffff?text=Lumis+System" 
                primary_color = "#6366f1"
                school_name = "Lumis Educacional"

            # 3. Template HTML (Adaptado para Recuperação)
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
                        <div class="h1">Olá, {user.first_name}!</div>
                        <div class="p">
                            Recebemos uma solicitação para redefinir a senha da sua conta no portal <strong>{school_name}</strong>.
                        </div>
                        
                        <div class="p">
                            Para criar uma nova senha, clique no botão abaixo:
                        </div>
                        
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{reset_link}" class="btn" style="color: #ffffff;">Redefinir Minha Senha</a>
                        </div>
                        
                        <div class="p" style="font-size: 14px; color: #6b7280; word-break: break-all;">
                            Ou copie o link: <br>
                            {reset_link}
                        </div>

                        <div class="p" style="margin-top: 30px; border-top: 1px solid #eee; padding-top: 20px; font-size: 14px; color: #6b7280;">
                            Se você não solicitou esta alteração, ignore este e-mail. Sua senha permanecerá a mesma.
                        </div>
                    </div>
                    <div class="footer">
                        Enviado automaticamente pelo Sistema {school_name}.
                    </div>
                </div>
            </body>
            </html>
            """
            
            plain_message = strip_tags(html_content)
            subject = f"Recuperação de Senha - {school_name}"
            
            # 4. Enviar
            send_mail(
                subject, 
                plain_message, 
                None, 
                [email], 
                html_message=html_content, # Aqui vai o HTML
                fail_silently=True
            )

        return Response({'message': 'Se o e-mail existir, o link foi enviado.'})

# --- 2. DEFINIR NOVA SENHA (MANTÉM IGUAL) ---
class PasswordResetConfirmView(APIView):
    permission_classes = []

    def post(self, request):
        uidb64 = request.data.get('uid')
        token = request.data.get('token')
        password = request.data.get('password')

        if not uidb64 or not token or not password:
            return Response({'error': 'Dados incompletos'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'error': 'Link inválido'}, status=status.HTTP_400_BAD_REQUEST)

        if default_token_generator.check_token(user, token):
            user.set_password(password)
            user.save()
            return Response({'message': 'Senha alterada com sucesso!'})
        else:
            return Response({'error': 'Token inválido ou expirado'}, status=status.HTTP_400_BAD_REQUEST)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('first_name')
    serializer_class = UserSerializer
    pagination_class = LargeResultsSetPagination 

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtro Genérico por Grupo (ex: ?group=Secretaria)
        group_name = self.request.query_params.get('group')
        if group_name:
            queryset = queryset.filter(groups__name__icontains=group_name)
        
        # Filtro de Papel Específico (usado no dropdown)
        role = self.request.query_params.get('role')
        if role == 'teacher':
             # CORREÇÃO: Removemos o "OR is_staff". Agora é SÓ quem tem "Professor" no grupo.
             queryset = queryset.filter(groups__name__icontains='Professor')

        return queryset

    # Endpoint 'me' para retornar o usuário logado
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

class SchoolConfigView(APIView):
    """
    Retorna a configuração da escola ativa para personalizar o Frontend (White Label).
    Aberto ao público (AllowAny) para carregar na tela de login.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        # Pega a primeira configuração encontrada (Single Tenant)
        # Se no futuro for multi-tenant, aqui entra a lógica de domínios
        config = SchoolAccount.objects.first()
        
        if config:
            serializer = SchoolAccountSerializer(config, context={'request': request})
            return Response(serializer.data)
        
        # Se não houver config, retorna 204 (No Content) ou 404
        # O Frontend entenderá isso e usará o padrão 'Lumis'
        return Response(status=404)

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        # Cada usuário só vê as suas notificações
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=True, methods=['patch'])
    def mark_read(self, request, pk=None):
        notif = self.get_object()
        notif.read = True
        notif.save()
        return Response({'status': 'read'})

    @action(detail=False, methods=['patch'])
    def mark_all_read(self, request):
        self.get_queryset().update(read=True)
        return Response({'status': 'all_read'})