from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APITestCase


User = get_user_model()


class UserViewSetAuthorizationTests(APITestCase):
    def setUp(self):
        self.common_user = User.objects.create_user(username='common_user', password='pass12345')
        self.power_user = User.objects.create_user(username='power_user', password='pass12345')
        coord_group, _ = Group.objects.get_or_create(name='Coordenacao')
        self.power_user.groups.add(coord_group)

    def test_common_user_cannot_list_users(self):
        self.client.force_authenticate(user=self.common_user)
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, 403)

    def test_power_user_can_list_users(self):
        self.client.force_authenticate(user=self.power_user)
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, 200)
