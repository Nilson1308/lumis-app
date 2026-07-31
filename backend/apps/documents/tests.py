from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.academic.models import (
    ClassRoom, Enrollment, Guardian, Segment, Student, Subject, TeacherAssignment,
)
from apps.core.models import Notification, User
from apps.documents.models import SharedDocument, SharedDocumentReadStatus
from apps.documents.services import publish_document


class SharedDocumentAuthorizationTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin_doc', email='admin@doc.test', password='pass12345'
        )
        self.secretary = User.objects.create_user(username='sec_doc', password='pass12345')
        self.teacher = User.objects.create_user(username='teach_doc', password='pass12345')
        self.teacher_other = User.objects.create_user(username='teach_other', password='pass12345')
        self.guardian_user = User.objects.create_user(username='guard_doc', password='pass12345')

        Group.objects.get_or_create(name='Secretaria')
        Group.objects.get_or_create(name='Professores')
        Group.objects.get_or_create(name='Responsaveis')

        self.secretary.groups.add(Group.objects.get(name='Secretaria'))
        self.teacher.groups.add(Group.objects.get(name='Professores'))
        self.teacher_other.groups.add(Group.objects.get(name='Professores'))
        self.guardian_user.groups.add(Group.objects.get(name='Responsaveis'))

        self.segment_a = Segment.objects.create(name='Fundamental I')
        self.segment_b = Segment.objects.create(name='Fundamental II')
        self.classroom = ClassRoom.objects.create(name='1º Ano A', year=2026, segment=self.segment_a)
        self.classroom_b = ClassRoom.objects.create(name='8º Ano B', year=2026, segment=self.segment_b)
        subject = Subject.objects.create(name='Matemática')
        TeacherAssignment.objects.create(
            teacher=self.teacher, subject=subject, classroom=self.classroom
        )
        TeacherAssignment.objects.create(
            teacher=self.teacher_other, subject=subject, classroom=self.classroom_b
        )

        self.guardian = Guardian.objects.create(
            name='Pai Teste', cpf='11122233344', phone='11999999999', user=self.guardian_user
        )
        self.student = Student.objects.create(
            name='Aluno Teste', birth_date='2015-01-01', registration_number='DOC-001'
        )
        self.student.guardians.add(self.guardian)
        Enrollment.objects.create(student=self.student, classroom=self.classroom)

        self.doc_all = SharedDocument.objects.create(
            title='Doc Geral',
            target_audience='ALL',
            external_link='https://example.com/all',
            uploaded_by=self.admin,
        )
        self.doc_teachers = SharedDocument.objects.create(
            title='Doc Professores',
            target_audience='TEACHERS',
            external_link='https://example.com/teachers',
            uploaded_by=self.admin,
        )
        self.doc_guardians = SharedDocument.objects.create(
            title='Doc Pais',
            target_audience='GUARDIANS',
            external_link='https://example.com/guardians',
            uploaded_by=self.admin,
        )
        self.doc_classroom = SharedDocument.objects.create(
            title='Doc Turma',
            target_audience='CLASSROOM',
            classroom=self.classroom,
            external_link='https://example.com/class',
            uploaded_by=self.admin,
        )
        self.doc_segment = SharedDocument.objects.create(
            title='Doc Segmento FI',
            target_audience='SEGMENT',
            segment=self.segment_a,
            external_link='https://example.com/segment',
            uploaded_by=self.admin,
        )
        self.doc_segment_b = SharedDocument.objects.create(
            title='Doc Segmento FII',
            target_audience='SEGMENT',
            segment=self.segment_b,
            external_link='https://example.com/segment-b',
            uploaded_by=self.admin,
        )
        self.doc_inactive = SharedDocument.objects.create(
            title='Doc Inativo',
            target_audience='ALL',
            external_link='https://example.com/inactive',
            uploaded_by=self.admin,
            is_active=False,
        )

    def test_teacher_sees_audience_scoped_documents(self):
        self.client.force_authenticate(user=self.teacher)
        res = self.client.get(reverse('shared-documents-list'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = {item['title'] for item in res.data['results']}
        self.assertIn('Doc Geral', titles)
        self.assertIn('Doc Professores', titles)
        self.assertIn('Doc Turma', titles)
        self.assertIn('Doc Segmento FI', titles)
        self.assertNotIn('Doc Pais', titles)
        self.assertNotIn('Doc Segmento FII', titles)
        self.assertNotIn('Doc Inativo', titles)

    def test_guardian_sees_audience_scoped_documents(self):
        self.client.force_authenticate(user=self.guardian_user)
        res = self.client.get(reverse('shared-documents-list'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        titles = {item['title'] for item in res.data['results']}
        self.assertIn('Doc Geral', titles)
        self.assertIn('Doc Pais', titles)
        self.assertIn('Doc Turma', titles)
        self.assertIn('Doc Segmento FI', titles)
        self.assertNotIn('Doc Professores', titles)
        self.assertNotIn('Doc Segmento FII', titles)
        self.assertNotIn('Doc Inativo', titles)

    def test_teacher_cannot_create_document(self):
        self.client.force_authenticate(user=self.teacher)
        res = self.client.post(reverse('shared-documents-list'), {
            'title': 'Tentativa',
            'target_audience': 'ALL',
            'external_link': 'https://example.com/x',
        })
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_secretary_can_create_document(self):
        self.client.force_authenticate(user=self.secretary)
        res = self.client.post(reverse('shared-documents-list'), {
            'title': 'Novo doc',
            'target_audience': 'ALL',
            'external_link': 'https://example.com/new',
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_admin_sees_inactive_documents(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(reverse('shared-documents-list'))
        titles = {item['title'] for item in res.data['results']}
        self.assertIn('Doc Inativo', titles)

    def test_publish_creates_notifications(self):
        doc = SharedDocument.objects.create(
            title='Doc Notify',
            target_audience='TEACHERS',
            external_link='https://example.com/n',
            uploaded_by=self.admin,
            is_active=True,
        )
        created = publish_document(doc, self.admin)
        self.assertGreaterEqual(created, 1)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.teacher,
                link__contains=f'doc={doc.id}',
            ).exists()
        )
        self.assertTrue(
            SharedDocumentReadStatus.objects.filter(document=doc, user=self.teacher).exists()
        )

    def test_teacher_can_mark_read(self):
        publish_document(self.doc_all, self.admin)
        self.client.force_authenticate(user=self.teacher)
        url = reverse('shared-documents-mark-read', kwargs={'pk': self.doc_all.pk})
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        status_obj = SharedDocumentReadStatus.objects.get(document=self.doc_all, user=self.teacher)
        self.assertIsNotNone(status_obj.read_at)

        list_res = self.client.get(reverse('shared-documents-list'))
        item = next(i for i in list_res.data['results'] if i['id'] == self.doc_all.id)
        self.assertTrue(item['is_read'])

    def test_teacher_cannot_access_read_report(self):
        self.client.force_authenticate(user=self.teacher)
        url = reverse('shared-documents-read-report', kwargs={'pk': self.doc_all.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_access_read_report(self):
        publish_document(self.doc_all, self.admin)
        self.client.force_authenticate(user=self.admin)
        url = reverse('shared-documents-read-report', kwargs={'pk': self.doc_all.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data), 1)

    def test_filter_by_segment(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(reverse('shared-documents-list'), {'segment': self.segment_a.id})
        titles = {item['title'] for item in res.data['results']}
        self.assertIn('Doc Segmento FI', titles)
        self.assertNotIn('Doc Segmento FII', titles)
