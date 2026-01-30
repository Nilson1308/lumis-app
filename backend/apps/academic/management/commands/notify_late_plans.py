from django.core.management.base import BaseCommand
from django.core.mail import send_mass_mail
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from apps.academic.models import TeacherAssignment, LessonPlan
from apps.core.models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Notifica atrasos (MODO DEBUG)'

    def handle(self, *args, **options):
        self.stdout.write("--- 🔍 INICIANDO DIAGNÓSTICO (V2) ---")
        
        today = timezone.now().date()
        # Calcula próxima segunda-feira
        days_ahead = 0 - today.weekday()
        if days_ahead <= 0: days_ahead += 7
        next_monday = today + timedelta(days=days_ahead)
        
        self.stdout.write(f"📅 Hoje: {today}")
        self.stdout.write(f"📅 Semana Alvo (Segunda): {next_monday}")

        # 1. Checa Atribuições
        assignments = TeacherAssignment.objects.all()
        count = assignments.count()
        self.stdout.write(f"📊 Total de Atribuições encontradas: {count}")

        if count == 0:
            self.stdout.write("❌ NENHUMA atribuição de aula encontrada. O script não tem o que verificar.")
            return

        teachers_status = {}
        missing_plans_coord = []
        emails_to_send = []

        self.stdout.write("\n--- Processando Atribuições ---")

        for assignment in assignments:
            # O campo 'teacher' é uma instância de User
            teacher_user = assignment.teacher
            
            # CORREÇÃO: User não tem .name, usamos get_full_name() ou username
            teacher_name = teacher_user.get_full_name()
            if not teacher_name:
                teacher_name = teacher_user.username

            subject_name = assignment.subject.name
            class_name = assignment.classroom.name
            
            # DEBUG: Verifica se tem email (mas não pula, para gerar notificação no sistema)
            if not teacher_user.email:
                self.stdout.write(f"⚠️ AVISO: Usuário '{teacher_name}' não tem e-mail. Apenas notificação visual será gerada.")

            # Checa se o plano existe
            # Status que contam como ENTREGUE: SUBMITTED ou APPROVED
            is_done = LessonPlan.objects.filter(
                assignment=assignment, 
                start_date=next_monday,
                status__in=['SUBMITTED', 'APPROVED']
            ).exists()
            
            status_debug = "✅ OK (Enviado)" if is_done else "❌ PENDENTE"
            self.stdout.write(f"   > Prof: {teacher_name} | Turma: {class_name} | {status_debug}")

            if not is_done:
                if teacher_user not in teachers_status:
                    teachers_status[teacher_user] = []
                teachers_status[teacher_user].append(f"{subject_name} ({class_name})")

        self.stdout.write("\n--- Gerando Notificações ---")

        # Processar Professores com Pendências
        for teacher_user, missing_subjects in teachers_status.items():
            t_name = teacher_user.get_full_name() or teacher_user.username
            self.stdout.write(f"🔔 Notificando: {t_name}")
            
            subject_txt = ", ".join(missing_subjects)
            
            # 1. Prepara E-mail (se tiver endereço)
            if teacher_user.email:
                msg_email = (
                    f"Olá {t_name},\n\n"
                    f"Consta pendência de envio do Planejamento para a semana de {next_monday.strftime('%d/%m')} "
                    f"nas turmas: {subject_txt}.\n"
                    f"Por favor, acesse o sistema e regularize."
                )
                emails_to_send.append((
                    "[Lumis] Alerta de Planejamento Pendente",
                    msg_email,
                    settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'sistema@lumis.com',
                    [teacher_user.email]
                ))
            
            # 2. Gera Notificação no Sistema (Sino)
            try:
                Notification.objects.create(
                    recipient=teacher_user,
                    title="Planejamento Pendente",
                    message=f"Falta enviar: {subject_txt} para {next_monday.strftime('%d/%m')}.",
                    link="/teacher/planning" # Verifique se a rota do frontend bate com essa
                )
            except Exception as e:
                self.stdout.write(f"Erro ao criar notificação: {e}")
            
            missing_plans_coord.append(f"{t_name}: {subject_txt}")

        # Enviar E-mails em Massa
        if emails_to_send:
            try:
                send_mass_mail(emails_to_send, fail_silently=False)
                self.stdout.write(f"📧 {len(emails_to_send)} e-mails enviados.")
            except Exception as e:
                self.stdout.write(f"❌ Erro ao enviar e-mails (Verifique settings.py): {e}")
        else:
            self.stdout.write("ℹ️ Nenhum e-mail enviado (lista vazia ou sem endereços).")

        # Processar Coordenação
        if missing_plans_coord:
            coords = User.objects.filter(groups__name='Coordenacao')
            if not coords.exists():
                self.stdout.write("⚠️ Nenhum usuário no grupo 'Coordenacao'. Usando Superusers.")
                coords = User.objects.filter(is_superuser=True)

            msg_coord = f"{len(missing_plans_coord)} professores com pendência para semana que vem."
            
            for coord in coords:
                Notification.objects.create(
                    recipient=coord,
                    title="Alerta de Atrasos",
                    message=msg_coord,
                    link="/coordination/planning"
                )
            self.stdout.write(f"📢 {coords.count()} coordenadores notificados.")

        self.stdout.write("--- Concluído ---")