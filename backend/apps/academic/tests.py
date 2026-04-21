from datetime import date, time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from apps.core.models import SchoolAccount
from apps.academic.models import (
    AcademicPeriod,
    Attendance,
    ClassRoom,
    ClassSchedule,
    Enrollment,
    Guardian,
    Segment,
    Student,
    Subject,
    TeacherAssignment,
    TaughtContent,
    LessonPlan,
    LessonPlanSubmissionBlock,
    AbsenceJustification,
    SchoolEvent,
)
from apps.coordination.models import StudentReport


User = get_user_model()


class ParentPortalSecurityTests(APITestCase):
    def setUp(self):
        self.guardian_user_1 = User.objects.create_user(username='guardian1', password='123')
        self.guardian_user_2 = User.objects.create_user(username='guardian2', password='123')
        self.teacher_user = User.objects.create_user(username='teacher1', password='123')

        self.guardian_1 = Guardian.objects.create(
            user=self.guardian_user_1,
            name='Resp Um',
            cpf='111.111.111-11',
            phone='11999999999',
            email='resp1@example.com',
        )
        self.guardian_2 = Guardian.objects.create(
            user=self.guardian_user_2,
            name='Resp Dois',
            cpf='222.222.222-22',
            phone='11988888888',
            email='resp2@example.com',
        )

        segment = Segment.objects.create(name='Fundamental I')
        classroom = ClassRoom.objects.create(name='5A', year=2026, segment=segment)
        subject = Subject.objects.create(name='Matemática')
        self.period = AcademicPeriod.objects.create(
            name='1º Bimestre',
            start_date=date(2026, 2, 1),
            end_date=date(2026, 4, 30),
            is_active=True,
        )
        assignment = TeacherAssignment.objects.create(
            teacher=self.teacher_user,
            subject=subject,
            classroom=classroom,
        )

        self.student_1 = Student.objects.create(name='Aluno 1', registration_number='A001')
        self.student_2 = Student.objects.create(name='Aluno 2', registration_number='A002')
        self.student_1.guardians.add(self.guardian_1)
        self.student_2.guardians.add(self.guardian_2)

        self.enrollment_1 = Enrollment.objects.create(student=self.student_1, classroom=classroom, active=True)
        self.enrollment_2 = Enrollment.objects.create(student=self.student_2, classroom=classroom, active=True)

        Attendance.objects.create(
            enrollment=self.enrollment_1,
            subject=subject,
            date=date(2026, 3, 10),
            present=False,
            justified=False,
            period=self.period,
        )
        Attendance.objects.create(
            enrollment=self.enrollment_2,
            subject=subject,
            date=date(2026, 3, 10),
            present=False,
            justified=False,
            period=self.period,
        )

        TaughtContent.objects.create(
            assignment=assignment,
            date=date(2026, 3, 10),
            content='<p>Frações e problemas</p>',
            homework='Lista 1',
        )

        StudentReport.objects.create(
            student=self.student_1,
            teacher=self.teacher_user,
            date=date(2026, 3, 10),
            subject='Acompanhamento',
            content='<script>alert(1)</script><p>Bom progresso</p>',
            status='APPROVED',
            visible_to_family=True,
        )
        StudentReport.objects.create(
            student=self.student_2,
            teacher=self.teacher_user,
            date=date(2026, 3, 10),
            subject='Outro aluno',
            content='Conteúdo restrito',
            status='APPROVED',
            visible_to_family=True,
        )

    def test_guardian_cannot_access_other_student_attendance_report(self):
        self.client.force_authenticate(user=self.guardian_user_1)
        response = self.client.get(f'/api/students/{self.student_2.id}/attendance-report/')
        self.assertEqual(response.status_code, 403)

    def test_guardian_can_access_own_student_class_diary(self):
        self.client.force_authenticate(user=self.guardian_user_1)
        response = self.client.get(f'/api/students/{self.student_1.id}/class-diary/')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)

    def test_guardian_class_diary_invalid_period_does_not_error(self):
        """Período inexistente não deve quebrar o portal (evita 400)."""
        self.client.force_authenticate(user=self.guardian_user_1)
        response = self.client.get(
            f'/api/students/{self.student_1.id}/class-diary/',
            {'academic_period': 999999}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)

    def test_guardian_cannot_access_other_student_report_card_pdf(self):
        self.client.force_authenticate(user=self.guardian_user_1)
        response = self.client.get(f'/api/students/{self.student_2.id}/report-card-pdf/')
        self.assertEqual(response.status_code, 403)

    def test_guardian_reports_filter_does_not_leak_other_student(self):
        self.client.force_authenticate(user=self.guardian_user_1)
        response = self.client.get(f'/api/student-reports/?student={self.student_2.id}')
        self.assertEqual(response.status_code, 200)
        data = response.data.get('results', response.data)
        self.assertEqual(len(data), 0)


class ClassScheduleAccessTests(APITestCase):
    """Grade horária: leitura por professor/responsável; escrita só coordenação/secretaria etc."""

    def setUp(self):
        self.teacher = User.objects.create_user(username='sch_teacher', password='pass12345')
        prof_group, _ = Group.objects.get_or_create(name='Professores')
        self.teacher.groups.add(prof_group)

        self.coord = User.objects.create_user(username='sch_coord', password='pass12345')
        coord_group, _ = Group.objects.get_or_create(name='Coordenadores')
        self.coord.groups.add(coord_group)

        segment = Segment.objects.create(name='Ensino Fundamental')
        self.classroom_a = ClassRoom.objects.create(name='6A', year=2026, segment=segment)
        self.classroom_b = ClassRoom.objects.create(name='7B', year=2026, segment=segment)
        subject = Subject.objects.create(name='Português')
        self.assignment = TeacherAssignment.objects.create(
            teacher=self.teacher, subject=subject, classroom=self.classroom_a
        )
        ClassSchedule.objects.create(
            classroom=self.classroom_a,
            assignment=self.assignment,
            day_of_week=1,
            start_time=time(8, 0),
            end_time=time(9, 0),
        )

    def test_coordinator_can_create_schedule(self):
        self.client.force_authenticate(user=self.coord)
        resp = self.client.post(
            '/api/schedules/',
            {
                'classroom': self.classroom_a.id,
                'assignment': self.assignment.id,
                'day_of_week': 2,
                'start_time': '10:00:00',
                'end_time': '11:00:00',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, 201)

    def test_teacher_cannot_create_schedule(self):
        self.client.force_authenticate(user=self.teacher)
        resp = self.client.post(
            '/api/schedules/',
            {
                'classroom': self.classroom_a.id,
                'assignment': self.assignment.id,
                'day_of_week': 3,
                'start_time': '14:00:00',
                'end_time': '15:00:00',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, 403)

    def test_teacher_can_list_own_classroom_schedule(self):
        self.client.force_authenticate(user=self.teacher)
        resp = self.client.get(f'/api/schedules/?classroom={self.classroom_a.id}')
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get('results', resp.data)
        self.assertGreaterEqual(len(results), 1)

    def test_teacher_list_other_classroom_is_empty(self):
        self.client.force_authenticate(user=self.teacher)
        resp = self.client.get(f'/api/schedules/?classroom={self.classroom_b.id}')
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get('results', resp.data)
        self.assertEqual(len(results), 0)

    def test_guardian_can_list_child_classroom_schedule(self):
        gu_user = User.objects.create_user(username='sch_guard', password='pass12345')
        guardian = Guardian.objects.create(
            user=gu_user,
            name='Resp Schedule',
            cpf='333.333.333-33',
            phone='11777777777',
            email='gschedule@example.com',
        )
        student = Student.objects.create(name='Aluno Sched', registration_number='SCH001')
        student.guardians.add(guardian)
        Enrollment.objects.create(student=student, classroom=self.classroom_a, active=True)
        self.client.force_authenticate(user=gu_user)
        resp = self.client.get(f'/api/schedules/?classroom={self.classroom_a.id}')
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get('results', resp.data)
        self.assertGreaterEqual(len(results), 1)

    def test_guardian_list_unrelated_classroom_is_empty(self):
        gu_user = User.objects.create_user(username='sch_guard2', password='pass12345')
        guardian = Guardian.objects.create(
            user=gu_user,
            name='Resp Dois Sched',
            cpf='444.444.444-44',
            phone='11666666666',
            email='g2schedule@example.com',
        )
        student = Student.objects.create(name='Aluno Sched 2', registration_number='SCH002')
        student.guardians.add(guardian)
        Enrollment.objects.create(student=student, classroom=self.classroom_a, active=True)
        self.client.force_authenticate(user=gu_user)
        resp = self.client.get(f'/api/schedules/?classroom={self.classroom_b.id}')
        self.assertEqual(resp.status_code, 200)
        results = resp.data.get('results', resp.data)
        self.assertEqual(len(results), 0)


class AttendanceScheduleRulesTests(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='att_teacher', password='pass12345')
        prof_group, _ = Group.objects.get_or_create(name='Professores')
        self.teacher.groups.add(prof_group)

        segment = Segment.objects.create(name='Fundamental II')
        self.classroom = ClassRoom.objects.create(name='8A', year=2026, segment=segment)
        self.subject = Subject.objects.create(name='Inglês')
        self.assignment = TeacherAssignment.objects.create(
            teacher=self.teacher,
            subject=self.subject,
            classroom=self.classroom,
        )
        self.student = Student.objects.create(name='Aluno Inglês', registration_number='ING001')
        self.enrollment = Enrollment.objects.create(student=self.student, classroom=self.classroom, active=True)

        # Terça-feira
        ClassSchedule.objects.create(
            classroom=self.classroom,
            assignment=self.assignment,
            day_of_week=1,
            start_time=time(7, 0),
            end_time=time(7, 50),
        )

        self.period = AcademicPeriod.objects.create(
            name='1º Bimestre',
            start_date=date(2026, 2, 1),
            end_date=date(2026, 4, 30),
            is_active=True,
        )

    def test_teacher_cannot_save_attendance_outside_schedule_day(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            '/api/attendance/bulk_save/',
            {
                'assignment': self.assignment.id,
                'classroom': self.classroom.id,
                'subject': self.subject.id,
                'date': '2026-03-11',  # Quarta-feira
                'records': [
                    {'enrollment_id': self.enrollment.id, 'present': True},
                ],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('grade horária', str(response.data))

    def test_teacher_can_save_attendance_on_schedule_day(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            '/api/attendance/bulk_save/',
            {
                'assignment': self.assignment.id,
                'classroom': self.classroom.id,
                'subject': self.subject.id,
                'date': '2026-03-10',  # Terça-feira
                'records': [
                    {'enrollment_id': self.enrollment.id, 'present': True},
                ],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Attendance.objects.filter(
                enrollment=self.enrollment,
                subject=self.subject,
                date=date(2026, 3, 10),
            ).count(),
            1,
        )

    def test_pending_by_assignment_ignores_holiday_dates(self):
        from datetime import datetime
        from apps.academic.models import SchoolEvent

        # Aula é de terça; dia 17/03/2026 é terça e será feriado.
        SchoolEvent.objects.create(
            title='Feriado Municipal',
            event_type='HOLIDAY',
            target_audience='ALL',
            start_time=datetime(2026, 3, 17, 0, 0),
            end_time=datetime(2026, 3, 17, 23, 59),
            created_by=self.teacher,
        )

        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(
            '/api/attendance/pending-by-assignment/',
            {'assignment': self.assignment.id}
        )
        self.assertEqual(response.status_code, 200)
        pending_dates = [item['date'] for item in response.data['pending_dates']]
        self.assertNotIn('2026-03-17', pending_dates)

    def test_teacher_cannot_save_attendance_on_holiday(self):
        from datetime import datetime
        from apps.academic.models import SchoolEvent

        SchoolEvent.objects.create(
            title='Feriado Municipal',
            event_type='HOLIDAY',
            target_audience='ALL',
            start_time=datetime(2026, 3, 10, 0, 0),
            end_time=datetime(2026, 3, 10, 23, 59),
            created_by=self.teacher,
        )

        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            '/api/attendance/bulk_save/',
            {
                'assignment': self.assignment.id,
                'classroom': self.classroom.id,
                'subject': self.subject.id,
                'date': '2026-03-10',
                'records': [
                    {'enrollment_id': self.enrollment.id, 'present': True},
                ],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('não letiva', str(response.data))

    def test_pending_by_assignment_returns_br_date_fields(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(
            '/api/attendance/pending-by-assignment/',
            {'assignment': self.assignment.id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('start_br', response.data['date_range'])
        if response.data['pending_dates']:
            self.assertIn('date_br', response.data['pending_dates'][0])

    def test_pending_overview_updates_notification_without_duplicates(self):
        self.client.force_authenticate(user=self.teacher)
        first = self.client.get('/api/attendance/pending-overview/')
        self.assertEqual(first.status_code, 200)
        first_count = self.teacher.notifications.filter(
            title__startswith='Pendência de Frequência'
        ).count()
        self.assertGreaterEqual(first_count, 1)

        second = self.client.get('/api/attendance/pending-overview/')
        self.assertEqual(second.status_code, 200)
        second_count = self.teacher.notifications.filter(
            title__startswith='Pendência de Frequência'
        ).count()
        self.assertEqual(first_count, second_count)

    def test_teacher_cannot_read_daily_log_from_other_teacher_classroom(self):
        other_teacher = User.objects.create_user(username='att_other', password='pass12345')
        prof_group, _ = Group.objects.get_or_create(name='Professores')
        other_teacher.groups.add(prof_group)
        other_assignment = TeacherAssignment.objects.create(
            teacher=other_teacher,
            subject=self.subject,
            classroom=self.classroom,
        )
        ClassSchedule.objects.create(
            classroom=self.classroom,
            assignment=other_assignment,
            day_of_week=2,
            start_time=time(9, 0),
            end_time=time(9, 50),
        )

        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(
            '/api/attendance/daily-log/',
            {'date': '2026-03-10', 'classroom': self.classroom.id, 'subject': self.subject.id},
        )
        self.assertEqual(response.status_code, 200)

        outsider = User.objects.create_user(username='att_outsider', password='pass12345')
        outsider.groups.add(prof_group)
        self.client.force_authenticate(user=outsider)
        forbidden = self.client.get(
            '/api/attendance/daily-log/',
            {'date': '2026-03-10', 'classroom': self.classroom.id, 'subject': self.subject.id},
        )
        self.assertEqual(forbidden.status_code, 403)


class LessonPlanSubmissionGuardTests(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='lp_teacher', password='pass12345')
        prof_group, _ = Group.objects.get_or_create(name='Professores')
        self.teacher.groups.add(prof_group)

        self.coordinator = User.objects.create_user(username='lp_coord', password='pass12345')
        coord_group, _ = Group.objects.get_or_create(name='Coordenacao')
        self.coordinator.groups.add(coord_group)

        SchoolAccount.objects.create(
            name='Escola Guard',
            slug='escola-guard',
            enforce_lesson_plan_submission_guard=True,
        )

        segment = Segment.objects.create(name='Fundamental')
        classroom = ClassRoom.objects.create(name='9A', year=2026, segment=segment)
        subject = Subject.objects.create(name='Ciências')
        self.assignment = TeacherAssignment.objects.create(
            teacher=self.teacher,
            subject=subject,
            classroom=classroom,
        )

    def test_teacher_submit_is_blocked_when_overdue(self):
        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            '/api/lesson-plans/',
            {
                'assignment': self.assignment.id,
                'topic': 'Plano da semana',
                'description': 'Conteúdo',
                'start_date': '2026-03-10',
                'end_date': '2026-03-14',
                'status': 'SUBMITTED',
                'recipients': [self.coordinator.id],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(
            LessonPlanSubmissionBlock.objects.filter(teacher=self.teacher, active=True).exists()
        )

    def test_coordinator_can_release_teacher_submission_guard(self):
        LessonPlanSubmissionBlock.objects.create(
            teacher=self.teacher,
            active=True,
            reason='Atraso de envio',
            blocked_by=self.coordinator,
        )
        self.client.force_authenticate(user=self.coordinator)
        response = self.client.post(
            '/api/lesson-plans/release-submission-guard/',
            {'teacher_id': self.teacher.id},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            LessonPlanSubmissionBlock.objects.filter(teacher=self.teacher, active=True).exists()
        )

    def test_coordinator_can_fetch_active_and_history_blocks(self):
        block = LessonPlanSubmissionBlock.objects.create(
            teacher=self.teacher,
            active=True,
            reason='Teste',
            blocked_by=self.coordinator,
        )
        self.client.force_authenticate(user=self.coordinator)
        active_resp = self.client.get('/api/lesson-plans/blocked-teachers/?active=true')
        self.assertEqual(active_resp.status_code, 200)
        self.assertEqual(active_resp.data['count'], 1)

        block.active = False
        block.released_by = self.coordinator
        from django.utils import timezone
        block.released_at = timezone.now()
        block.save(update_fields=['active', 'released_by', 'released_at'])

        history_resp = self.client.get('/api/lesson-plans/blocked-teachers/?active=false')
        self.assertEqual(history_resp.status_code, 200)
        self.assertEqual(history_resp.data['count'], 1)

    def test_coordinator_can_apply_manual_block(self):
        self.client.force_authenticate(user=self.coordinator)
        response = self.client.post(
            '/api/lesson-plans/block-submission-guard/',
            {'teacher_id': self.teacher.id, 'reason': 'Bloqueio manual de teste'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            LessonPlanSubmissionBlock.objects.filter(teacher=self.teacher, active=True).exists()
        )

    def test_teacher_cannot_save_attendance_on_configured_non_teaching_type(self):
        from datetime import datetime
        from apps.academic.models import SchoolEvent

        SchoolAccount.objects.create(
            name='Escola Teste',
            slug='escola-teste',
            non_teaching_event_types=['HOLIDAY', 'MEETING'],
        )
        SchoolEvent.objects.create(
            title='Reunião Pedagógica',
            event_type='MEETING',
            target_audience='ALL',
            start_time=datetime(2026, 3, 10, 0, 0),
            end_time=datetime(2026, 3, 10, 23, 59),
            created_by=self.teacher,
        )

        self.client.force_authenticate(user=self.teacher)
        response = self.client.post(
            '/api/attendance/bulk_save/',
            {
                'assignment': self.assignment.id,
                'classroom': self.classroom.id,
                'subject': self.subject.id,
                'date': '2026-03-10',
                'records': [
                    {'enrollment_id': self.enrollment.id, 'present': True},
                ],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('não letiva', str(response.data))


class AuthorizationHardeningTests(APITestCase):
    def setUp(self):
        self.guardian_user = User.objects.create_user(username='auth_guardian', password='123')
        self.other_guardian_user = User.objects.create_user(username='auth_guardian_other', password='123')
        self.teacher_user = User.objects.create_user(username='auth_teacher', password='123')
        self.coord_user = User.objects.create_user(username='auth_coord', password='123')

        prof_group, _ = Group.objects.get_or_create(name='Professores')
        coord_group, _ = Group.objects.get_or_create(name='Coordenacao')
        self.teacher_user.groups.add(prof_group)
        self.coord_user.groups.add(coord_group)

        self.guardian = Guardian.objects.create(
            user=self.guardian_user,
            name='Resp Auth',
            cpf='555.555.555-55',
            phone='11911111111',
            email='authg@example.com',
        )
        self.other_guardian = Guardian.objects.create(
            user=self.other_guardian_user,
            name='Resp Auth 2',
            cpf='666.666.666-66',
            phone='11922222222',
            email='authg2@example.com',
        )

        segment = Segment.objects.create(name='Seg Auth')
        self.classroom = ClassRoom.objects.create(name='AUTH1', year=2026, segment=segment)
        self.subject = Subject.objects.create(name='Matéria Auth')
        TeacherAssignment.objects.create(
            teacher=self.teacher_user,
            subject=self.subject,
            classroom=self.classroom,
        )

        self.student = Student.objects.create(name='Aluno Auth', registration_number='AUTH001')
        self.student.guardians.add(self.guardian)
        self.enrollment = Enrollment.objects.create(student=self.student, classroom=self.classroom, active=True)
        self.attendance = Attendance.objects.create(
            enrollment=self.enrollment,
            subject=self.subject,
            date=date(2026, 4, 15),
            present=False,
            justified=False,
        )

    def test_guardian_list_returns_only_own_profile(self):
        self.client.force_authenticate(user=self.guardian_user)
        response = self.client.get('/api/guardians/')
        self.assertEqual(response.status_code, 200)
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.guardian.id)

    def test_guardian_cannot_change_absence_status(self):
        justification = AbsenceJustification.objects.create(
            attendance=self.attendance,
            reason='Teste',
            status='PENDING',
        )
        self.client.force_authenticate(user=self.guardian_user)
        response = self.client.patch(
            f'/api/justifications/{justification.id}/',
            {'status': 'APPROVED'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_guardian_cannot_create_school_event(self):
        self.client.force_authenticate(user=self.guardian_user)
        response = self.client.post(
            '/api/calendar/',
            {
                'title': 'Evento indevido',
                'event_type': 'EVENT',
                'target_audience': 'ALL',
                'start_time': '2026-04-21T08:00:00Z',
                'end_time': '2026-04-21T09:00:00Z',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(SchoolEvent.objects.count(), 0)


class ReconcileLessonPlanGuardsCommandTests(APITestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='guard_cmd_teacher', password='pass12345')
        prof_group, _ = Group.objects.get_or_create(name='Professores')
        self.teacher.groups.add(prof_group)

        SchoolAccount.objects.create(
            name='Escola Guard Cmd',
            slug='escola-guard-cmd',
            enforce_lesson_plan_submission_guard=True,
        )

        segment = Segment.objects.create(name='Fundamental Cmd')
        classroom = ClassRoom.objects.create(name='7B', year=2026, segment=segment)
        subject = Subject.objects.create(name='Geografia')
        self.assignment = TeacherAssignment.objects.create(
            teacher=self.teacher,
            subject=subject,
            classroom=classroom,
        )

    def test_command_creates_single_block_for_same_week(self):
        call_command(
            'reconcile_lesson_plan_guards',
            week_start='2026-04-20',
            stdout=StringIO(),
        )
        self.assertEqual(
            LessonPlanSubmissionBlock.objects.filter(teacher=self.teacher, active=True).count(),
            1,
        )
        first_notifications = self.teacher.notifications.filter(
            title='Envio de Planejamento Bloqueado'
        ).count()
        self.assertEqual(first_notifications, 1)

        call_command(
            'reconcile_lesson_plan_guards',
            week_start='2026-04-20',
            stdout=StringIO(),
        )
        self.assertEqual(
            LessonPlanSubmissionBlock.objects.filter(teacher=self.teacher, active=True).count(),
            1,
        )
        second_notifications = self.teacher.notifications.filter(
            title='Envio de Planejamento Bloqueado'
        ).count()
        self.assertEqual(second_notifications, first_notifications)

    def test_command_dry_run_does_not_create_block(self):
        call_command(
            'reconcile_lesson_plan_guards',
            week_start='2026-04-20',
            dry_run=True,
            stdout=StringIO(),
        )
        self.assertEqual(LessonPlanSubmissionBlock.objects.count(), 0)

class CalendarXlsxImportTests(SimpleTestCase):
    def test_parse_range(self):
        from apps.academic.calendar_xlsx_import import parse_calendar_line

        evs = parse_calendar_line('02 a 14 - Recesso Escolar', 2026, 1)
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0].start_date, date(2026, 1, 2))
        self.assertEqual(evs[0].end_date, date(2026, 1, 14))
        self.assertEqual(evs[0].event_type, 'HOLIDAY')

    def test_parse_three_days(self):
        from apps.academic.calendar_xlsx_import import parse_calendar_line

        evs = parse_calendar_line('16, 17 e 18 - Recesso (Aulas Suspensas) - Carnaval', 2026, 2)
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0].start_date, date(2026, 2, 16))
        self.assertEqual(evs[0].end_date, date(2026, 2, 18))

    def test_parse_single_day_with_short_day(self):
        from apps.academic.calendar_xlsx_import import parse_calendar_line

        evs = parse_calendar_line('6 - Atividade Interna: Dia da Mulher', 2026, 3)
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0].start_date, date(2026, 3, 6))

    def test_invalid_day_in_month_returns_empty(self):
        from apps.academic.calendar_xlsx_import import parse_calendar_line

        self.assertEqual(parse_calendar_line('31 - Teste', 2026, 2), [])

    def test_skip_dias_letivos(self):
        from apps.academic.calendar_xlsx_import import parse_calendar_line

        self.assertEqual(parse_calendar_line('106 dias letivos', 2026, 6), [])

    def test_classify_meeting(self):
        from apps.academic.calendar_xlsx_import import classify_event

        self.assertEqual(classify_event('31 - Reunião de Pais (Letivo)'), ('MEETING', 'ALL'))

    def test_iter_workbook_when_file_and_openpyxl_exist(self):
        from pathlib import Path

        try:
            import openpyxl  # noqa: F401
        except ImportError:
            self.skipTest('openpyxl não instalado')
        from apps.academic.calendar_xlsx_import import iter_parsed_events

        # Mesmo critério que import_school_calendar_xlsx: raiz do repo / calendario 2026.xlsx
        p = Path(__file__).resolve().parents[3] / 'calendario 2026.xlsx'
        if not p.is_file():
            self.skipTest('calendario 2026.xlsx ausente')
        evs = list(iter_parsed_events(p, year=2026))
        self.assertGreater(len(evs), 40)
        titles = {e.title for e in evs}
        self.assertTrue(any('Recesso Escolar' in t for t in titles))
