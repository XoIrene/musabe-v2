from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APITestCase

from core.models import Branch


class SchoolAPITestCase(APITestCase):
    """Seeds the demo schools and gives tests short login/request helpers."""

    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo', verbosity=0)
        call_command('seed_school_data', verbosity=0)
        cls.nps = Branch.objects.get(code='NPS')
        cls.gss = Branch.objects.get(code='GSS')
        cls.bss = Branch.objects.get(code='BSS')

    def setUp(self):
        cache.clear()   # login throttling counters live in the cache

    def login(self, email, password='musabe123'):
        r = self.client.post('/api/auth/login/', {'email': email, 'password': password}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + r.data['access'])

    def call(self, method, url, data=None, expect=200):
        r = getattr(self.client, method)(url, data, format='json')
        self.assertEqual(r.status_code, expect, f'{method} {url} -> {r.status_code} {r.content[:300]}')
        return r.data if r.get('Content-Type', '').startswith('application/json') else r

    def act(self, rid, action, expect=200, **extra):
        return self.call('post', f'/api/requests/{rid}/act/', {'action': action, **extra}, expect)
