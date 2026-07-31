from datetime import date

from django.test import SimpleTestCase

from apps.academic.schedule_utils import schedule_day_of_week


class ScheduleDayOfWeekTests(SimpleTestCase):
    def test_matches_javascript_get_day(self):
        # Terça-feira
        self.assertEqual(schedule_day_of_week(date(2026, 3, 10)), 2)
        # Domingo
        self.assertEqual(schedule_day_of_week(date(2026, 3, 8)), 0)
        # Sábado
        self.assertEqual(schedule_day_of_week(date(2026, 3, 14)), 6)
