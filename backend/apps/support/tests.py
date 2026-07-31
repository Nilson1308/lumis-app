from datetime import date, time

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from apps.support.models import SupportTicket, SupportTicketReply

User = get_user_model()


class SupportTicketApiTests(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='support_a', password='pass12345')
        self.user_b = User.objects.create_user(username='support_b', password='pass12345')
        self.staff = User.objects.create_user(
            username='support_staff',
            password='pass12345',
            is_staff=True,
        )

    def test_user_can_create_ticket(self):
        self.client.force_authenticate(user=self.user_a)
        response = self.client.post(
            '/api/support-tickets/',
            {
                'occurred_date': '2026-05-10',
                'occurred_time': '14:30:00',
                'description': 'Não consigo acessar o diário de classe.',
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(SupportTicket.objects.filter(requester=self.user_a).count(), 1)

    def test_user_lists_only_own_tickets(self):
        SupportTicket.objects.create(
            requester=self.user_a,
            occurred_date=date(2026, 5, 10),
            occurred_time=time(10, 0),
            description='Chamado A',
        )
        SupportTicket.objects.create(
            requester=self.user_b,
            occurred_date=date(2026, 5, 11),
            occurred_time=time(11, 0),
            description='Chamado B',
        )

        self.client.force_authenticate(user=self.user_a)
        response = self.client.get('/api/support-tickets/')
        self.assertEqual(response.status_code, 200)
        data = response.data.get('results', response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['description'], 'Chamado A')

    def test_user_cannot_view_other_user_ticket(self):
        ticket = SupportTicket.objects.create(
            requester=self.user_b,
            occurred_date=date(2026, 5, 10),
            occurred_time=time(9, 0),
            description='Privado',
        )
        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(f'/api/support-tickets/{ticket.id}/')
        self.assertEqual(response.status_code, 404)

    def test_public_replies_visible_internal_hidden(self):
        ticket = SupportTicket.objects.create(
            requester=self.user_a,
            occurred_date=date(2026, 5, 10),
            occurred_time=time(9, 0),
            description='Com respostas',
        )
        SupportTicketReply.objects.create(
            ticket=ticket,
            author=self.staff,
            message='Resposta pública',
            is_internal=False,
        )
        SupportTicketReply.objects.create(
            ticket=ticket,
            author=self.staff,
            message='Nota interna',
            is_internal=True,
        )

        self.client.force_authenticate(user=self.user_a)
        response = self.client.get(f'/api/support-tickets/{ticket.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['replies']), 1)
        self.assertEqual(response.data['replies'][0]['message'], 'Resposta pública')

    def test_rejects_oversized_attachment(self):
        self.client.force_authenticate(user=self.user_a)
        big = SimpleUploadedFile('big.pdf', b'0' * (5 * 1024 * 1024 + 1), content_type='application/pdf')
        response = self.client.post(
            '/api/support-tickets/',
            {
                'occurred_date': '2026-05-10',
                'occurred_time': '10:00:00',
                'description': 'Com anexo grande',
                'attachment': big,
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, 400)
