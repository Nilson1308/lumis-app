from datetime import date
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase

from apps.academic.models import ClassRoom, Segment, Subject, TeacherAssignment
from apps.core.models import Notification


User = get_user_model()


class NotifyLateWeeklyReportsCommandTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='weekly_teacher', password='pass12345')
        segment = Segment.objects.create(name='Fundamental')
        classroom = ClassRoom.objects.create(name='6A', year=2026, segment=segment)
        subject = Subject.objects.create(name='História')
        TeacherAssignment.objects.create(
            teacher=self.teacher,
            subject=subject,
            classroom=classroom,
        )

        self.coordinator = User.objects.create_user(username='weekly_coord', password='pass12345')
        coord_group, _ = Group.objects.get_or_create(name='Coordenacao')
        self.coordinator.groups.add(coord_group)

    def test_command_is_idempotent_for_same_week(self):
        output = StringIO()
        call_command(
            'notify_late_weekly_reports',
            week_start='2026-04-20',
            stdout=output,
        )
        first_count = Notification.objects.count()
        self.assertEqual(first_count, 2)

        call_command(
            'notify_late_weekly_reports',
            week_start='2026-04-20',
            stdout=StringIO(),
        )
        second_count = Notification.objects.count()
        self.assertEqual(second_count, first_count)

    def test_command_dry_run_does_not_create_notifications(self):
        call_command(
            'notify_late_weekly_reports',
            week_start='2026-04-20',
            dry_run=True,
            stdout=StringIO(),
        )
        self.assertEqual(Notification.objects.count(), 0)
