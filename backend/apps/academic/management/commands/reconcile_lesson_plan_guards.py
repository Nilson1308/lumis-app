from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.academic.models import TeacherAssignment, LessonPlan, LessonPlanSubmissionBlock
from apps.core.models import SchoolAccount, Notification


User = get_user_model()


class Command(BaseCommand):
    help = "Reconcilia bloqueios de envio de planejamento semanal por atraso."

    @staticmethod
    def _parse_week_start(raw_date):
        if not raw_date:
            today = timezone.localdate()
            return today - timedelta(days=today.weekday())
        return timezone.datetime.strptime(raw_date, "%Y-%m-%d").date()

    @staticmethod
    def _already_notified_for_week(teacher, week_label):
        return Notification.objects.filter(
            recipient=teacher,
            title="Envio de Planejamento Bloqueado",
            link="/teacher/lesson-plans",
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
            help="Simula a execução sem persistir bloqueios/notificações.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        school = SchoolAccount.objects.first()
        guard_enabled = bool(school and getattr(school, "enforce_lesson_plan_submission_guard", False))

        if not guard_enabled:
            self.stdout.write(self.style.WARNING("Política de bloqueio está desativada. Nenhuma ação aplicada."))
            return

        week_start = self._parse_week_start(options.get("week_start"))
        previous_week_start = week_start - timedelta(days=7)
        previous_week_end = week_start - timedelta(days=1)
        week_label = f"{previous_week_start.strftime('%d/%m/%Y')} a {previous_week_end.strftime('%d/%m/%Y')}"

        teachers = User.objects.filter(assignments__isnull=False, is_active=True).distinct()
        blocked_now = 0
        already_blocked = 0
        skipped_already_notified = 0

        for teacher in teachers:
            assignments = TeacherAssignment.objects.filter(teacher=teacher).select_related("subject", "classroom")
            if not assignments.exists():
                continue

            has_overdue = False
            first_overdue = None

            for assignment in assignments:
                submitted = LessonPlan.objects.filter(
                    assignment=assignment,
                    start_date__lte=previous_week_end,
                    end_date__gte=previous_week_start,
                    status__in=["SUBMITTED", "APPROVED"],
                ).exists()
                if not submitted:
                    has_overdue = True
                    if first_overdue is None:
                        first_overdue = assignment

            if not has_overdue:
                continue

            active_block = LessonPlanSubmissionBlock.objects.filter(teacher=teacher, active=True).first()
            if active_block:
                already_blocked += 1
                continue

            reason = f"Atraso no envio do planejamento da semana {week_label}."
            block = None
            if not dry_run:
                with transaction.atomic():
                    block = LessonPlanSubmissionBlock.objects.create(
                        teacher=teacher,
                        active=True,
                        reason=reason,
                    )
                    if not self._already_notified_for_week(teacher, week_label):
                        Notification.objects.create(
                            recipient=teacher,
                            title="Envio de Planejamento Bloqueado",
                            message=(
                                f"{reason} O envio definitivo está bloqueado até liberação da coordenação/admin."
                            ),
                            link="/teacher/lesson-plans",
                            read=False,
                        )
                    else:
                        skipped_already_notified += 1
            elif self._already_notified_for_week(teacher, week_label):
                skipped_already_notified += 1

            blocked_now += 1
            block_id = block.id if block else "dry-run"
            self.stdout.write(
                self.style.WARNING(
                    f"Bloqueado: {teacher.get_full_name() or teacher.username} "
                    f"(bloco #{block_id}, exemplo de pendência: "
                    f"{first_overdue.subject.name if first_overdue else '-'} / "
                    f"{first_overdue.classroom.name if first_overdue else '-'})"
                )
            )

        mode_label = "SIMULAÇÃO" if dry_run else "EXECUÇÃO"
        self.stdout.write(
            self.style.SUCCESS(
                f"{mode_label} concluída. Semana analisada: {week_label}. "
                f"Novos bloqueios: {blocked_now}. "
                f"Já bloqueados previamente: {already_blocked}. "
                f"Notificações já existentes (sem duplicar): {skipped_already_notified}."
            )
        )
