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
    help = 'Notifica atrasos individualmente (MODO DEBUG)'

    def handle(self, *args, **options):
        self.stdout.write("--- 🔍 INICIANDO DIAGNÓSTICO (V3 - Individual) ---")
        
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
        
        if count == 0:
            self.stdout.write("❌ NENHUMA atribuição encontrada.")
            return

        # Busca Coordenadores (para notificar)
        coords = User.objects.filter(groups__name='Coordenacao')
        if not coords.exists():
            coords = User.objects.filter(is_superuser=True)

        emails_to_send = []
        notifications_created = 0

        self.stdout.write("\n--- Processando Pendências ---")

        for assignment in assignments:
            teacher_user = assignment.teacher
            teacher_name = teacher_user.get_full_name() or teacher_user.username
            subject_name = assignment.subject.name
            class_name = assignment.classroom.name
            
            # Checa se o plano existe (SUBMITTED ou APPROVED)
            is_done = LessonPlan.objects.filter(
                assignment=assignment, 
                start_date=next_monday,
                status__in=['SUBMITTED', 'APPROVED']
            ).exists()
            
            if not is_done:
                # DETECTOU PENDÊNCIA INDIVIDUAL
                self.stdout.write(f"❌ Pendência: {teacher_name} - {subject_name} ({class_name})")
                
                week_fmt = next_monday.strftime('%d/%m')
                iso_date = next_monday.strftime('%Y-%m-%d') # Formato para URL (ex: 2026-02-02)

                # 1. Notificação para o PROFESSOR (Com Link Inteligente)
                teacher_link = f"/teacher/lesson-plans?assignment={assignment.id}"
                
                try:
                    Notification.objects.create(
                        recipient=teacher_user,
                        title="Planejamento Pendente",
                        message=f"Falta enviar: {subject_name} ({class_name}) para a semana de {week_fmt}.",
                        link=teacher_link 
                    )
                    notifications_created += 1
                except Exception as e:
                    self.stdout.write(f"Erro ao criar notif professor: {e}")

                # 2. Notificação para COORDENADORES (Link com Filtro)
                coord_link = f"/coordination/planning?assignment={assignment.id}"

                msg_coord = f"{teacher_name}: Pendente {subject_name} ({class_name}) - Semana {week_fmt}"
                for coord in coords:
                    Notification.objects.create(
                        recipient=coord,
                        title="Atraso no Planejamento",
                        message=msg_coord,
                        link=coord_link
                    )
                    notifications_created += 1

        self.stdout.write(f"\n✅ Total de notificações geradas no sistema: {notifications_created}")
        
        # NOTA: O envio de e-mails em massa foi removido neste bloco simplificado para focar nas notificações visuais.
        # Se quiser os e-mails, o ideal é reintroduzir a lógica de agrupamento (dict) APENAS para os e-mails,
        # mantendo o loop acima para as notificações visuais.

        self.stdout.write("--- Concluído ---")