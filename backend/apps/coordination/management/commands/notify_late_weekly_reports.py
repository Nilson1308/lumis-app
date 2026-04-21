from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.academic.models import TeacherAssignment
from apps.coordination.models import WeeklyReport
from apps.core.models import Notification


User = get_user_model()


class Command(BaseCommand):
    help = "Notifica pendências de envio de relatório semanal (sem bloqueio)."

    @staticmethod
    def _parse_week_start(raw_date):
        if not raw_date:
            today = timezone.localdate()
            return today - timedelta(days=today.weekday())
        return timezone.datetime.strptime(raw_date, "%Y-%m-%d").date()

    @staticmethod
    def _notification_exists(recipient, title, link, week_label):
        return Notification.objects.filter(
            recipient=recipient,
            title=title,
            link=link,
            message__contains=week_label,
        ).exists()

    def add_arguments(self, parser):
        parser.add_argument(
            "--week-start",
            type=str,
            help="Início da semana de referência no formato YYYY-MM-DD. Padrão: semana atual.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula a execução sem persistir notificações.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        week_start = self._parse_week_start(options.get("week_start"))
        previous_week_start = week_start - timedelta(days=7)
        previous_week_end = week_start - timedelta(days=1)
        week_label = f"{previous_week_start.strftime('%d/%m/%Y')} a {previous_week_end.strftime('%d/%m/%Y')}"

        teachers = User.objects.filter(assignments__isnull=False, is_active=True).distinct()
        coordinators = User.objects.filter(
            groups__name__in=['Coordenadores', 'Coordenação', 'Coordenacao']
        , is_active=True).distinct()
        if not coordinators.exists():
            coordinators = User.objects.filter(is_superuser=True, is_active=True)

        late_count = 0
        notifications_count = 0
        skipped_duplicates = 0

        for teacher in teachers:
            has_report = WeeklyReport.objects.filter(
                author=teacher,
                start_date__lte=previous_week_end,
                end_date__gte=previous_week_start,
            ).exists()
            if has_report:
                continue

            late_count += 1
            teacher_name = teacher.get_full_name() or teacher.username

            first_assignment = (
                TeacherAssignment.objects.filter(teacher=teacher)
                .select_related('subject', 'classroom')
                .first()
            )
            context_label = ''
            if first_assignment:
                context_label = f" ({first_assignment.subject.name} - {first_assignment.classroom.name})"

            if dry_run:
                if self._notification_exists(
                    teacher, 'Relatório Semanal Pendente', '/teacher/weekly-reports', week_label
                ):
                    skipped_duplicates += 1
                for coordinator in coordinators:
                    if self._notification_exists(
                        coordinator, 'Atraso no Relatório Semanal', '/coordination/weekly-reports', week_label
                    ):
                        skipped_duplicates += 1
            else:
                with transaction.atomic():
                    if not self._notification_exists(
                        teacher, 'Relatório Semanal Pendente', '/teacher/weekly-reports', week_label
                    ):
                        Notification.objects.create(
                            recipient=teacher,
                            title='Relatório Semanal Pendente',
                            message=f'Você não enviou o relatório semanal do período {week_label}.',
                            link='/teacher/weekly-reports',
                            read=False,
                        )
                        notifications_count += 1
                    else:
                        skipped_duplicates += 1

                    for coordinator in coordinators:
                        if not self._notification_exists(
                            coordinator, 'Atraso no Relatório Semanal', '/coordination/weekly-reports', week_label
                        ):
                            Notification.objects.create(
                                recipient=coordinator,
                                title='Atraso no Relatório Semanal',
                                message=f'{teacher_name}{context_label} está sem relatório semanal ({week_label}).',
                                link='/coordination/weekly-reports',
                                read=False,
                            )
                            notifications_count += 1
                        else:
                            skipped_duplicates += 1

            self.stdout.write(
                self.style.WARNING(f'Pendência detectada: {teacher_name} - semana {week_label}')
            )

        mode_label = "SIMULAÇÃO" if dry_run else "EXECUÇÃO"
        self.stdout.write(
            self.style.SUCCESS(
                f'{mode_label} concluída. Semana analisada: {week_label}. '
                f'Professores em atraso: {late_count}. '
                f'Notificações criadas: {notifications_count}. '
                f'Registros já existentes (sem duplicar): {skipped_duplicates}.'
            )
        )
