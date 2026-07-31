from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import RequestFactory, SimpleTestCase
from rest_framework.test import APITestCase

from apps.academic.models import AcademicPeriod, ClassRoom, Segment
from apps.academic.report_filters import resolve_classroom_report_window

User = get_user_model()


class ReportFilterUnitTests(SimpleTestCase):
    def test_intersects_period_with_requested_range(self):
        factory = RequestFactory()
        period = AcademicPeriod(
            name='1º Bim',
            start_date=date(2026, 2, 1),
            end_date=date(2026, 4, 30),
        )
        period.pk = 1

        classroom = ClassRoom(name='6A', year=2026)
        classroom.pk = 10

        request = factory.get(
            '/api/reports/diary-pdf/',
            {
                'classroom': '10',
                'period': '1',
                'start_date': '2026-03-01',
                'end_date': '2026-03-31',
            },
        )

        with self.settings(ROOT_URLCONF='setup.urls'):
            from unittest.mock import patch

            with patch('apps.academic.report_filters.ClassRoom.objects.get', return_value=classroom), patch(
                'apps.academic.report_filters.AcademicPeriod.objects.get', return_value=period
            ):
                payload, error = resolve_classroom_report_window(request)

        self.assertIsNone(error)
        self.assertEqual(payload['date_start'], date(2026, 3, 1))
        self.assertEqual(payload['date_end'], date(2026, 3, 31))


class ReportPdfFilterApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='report_coord', password='pass12345')
        coord_group, _ = Group.objects.get_or_create(name='Coordenadores')
        self.user.groups.add(coord_group)

        segment = Segment.objects.create(name='Fundamental')
        self.classroom = ClassRoom.objects.create(name='7A', year=2026, segment=segment)
        self.period = AcademicPeriod.objects.create(
            name='1º Bimestre',
            start_date=date(2026, 2, 1),
            end_date=date(2026, 4, 30),
            is_active=True,
        )

    def test_diary_pdf_requires_period(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            '/api/reports/diary-pdf/',
            {'classroom': self.classroom.id},
        )
        self.assertEqual(response.status_code, 400)

    def test_diary_pdf_rejects_non_overlapping_range(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            '/api/reports/diary-pdf/',
            {
                'classroom': self.classroom.id,
                'period': self.period.id,
                'start_date': '2025-01-01',
                'end_date': '2025-01-31',
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('intervalo', str(response.content).lower())
