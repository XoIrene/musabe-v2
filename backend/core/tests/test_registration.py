from unittest import mock

from rest_framework.throttling import SimpleRateThrottle

from core.models import User
from core.tests.base import SchoolAPITestCase


class RegistrationAndSecurityTests(SchoolAPITestCase):
    """Proposal section 5: the Admin registers branches and staff; everyone sees only what their role allows."""

    def staff(self, **over):
        return {'full_name': 'New Person', 'email': 'new@musabe.test', 'password': 'Strong-pass-77', 'role': 'LIBRARIAN',
                'branches': [self.gss.id], **over}

    def test_admin_registers_branches(self):
        self.login('admin@musabe.test')
        b = self.call('post', '/api/branches/', {'name': 'Annex', 'code': 'ANX', 'type': 'PRIMARY'}, 201)
        self.call('post', '/api/branches/', {'name': 'Annex 2', 'code': 'ANX', 'type': 'PRIMARY'}, 400)   # codes are unique
        self.call('post', '/api/branches/', {'name': 'Odd', 'code': 'ODD', 'type': 'COLLEGE'}, 400)       # Primary or Secondary only
        self.login('head.girls@musabe.test')
        self.call('post', '/api/branches/', {'name': 'Mine', 'code': 'MNE', 'type': 'PRIMARY'}, 403)
        self.assertIn(b['id'], [x['id'] for x in self.call('get', '/api/branches/')])                     # but everyone can read them

    def test_admin_registers_staff_with_role_and_places(self):
        self.login('admin@musabe.test')
        multi = self.call('post', '/api/staff/', self.staff(branches=[self.gss.id, self.bss.id]), 201)
        self.assertEqual(sorted(multi['branches']), sorted([self.gss.id, self.bss.id]))                   # several branches
        self.call('post', '/api/staff/', self.staff(email='b@musabe.test', role='BURSAR', branches=[]), 201)   # central place
        self.call('post', '/api/staff/', self.staff(email='c@musabe.test', role='BURSAR'), 400)           # central role with a school
        self.call('post', '/api/staff/', self.staff(email='d@musabe.test', branches=[]), 400)             # school role needs a school
        self.call('post', '/api/staff/', self.staff(), 400)                                               # duplicate email
        self.call('post', '/api/staff/', self.staff(email='e@musabe.test', role='PARENT'), 400)           # parents come via guardians
        self.call('post', '/api/staff/', self.staff(email='f@musabe.test', password='short'), 400)
        self.call('post', '/api/staff/', self.staff(email='g@musabe.test', password='12345678'), 400)     # too easy to guess
        self.call('post', '/api/staff/', self.staff(email='h@musabe.test', password=''), 400)             # password required
        # the new staff member can log in and has a restricted view
        self.login('new@musabe.test', 'Strong-pass-77')
        self.assertEqual(self.call('get', '/api/me/')['role'], 'LIBRARIAN')
        self.call('get', '/api/staff/', expect=403)

    def test_nobody_but_the_admin_manages_staff(self):
        for who in ('manager@musabe.test', 'head.girls@musabe.test', 'bursar@musabe.test', 'teacher.girls@musabe.test'):
            self.login(who)
            self.call('post', '/api/staff/', self.staff(), 403)
            self.call('get', '/api/staff/', expect=403)

    def test_passwords_are_stored_hashed_and_never_returned(self):
        self.login('admin@musabe.test')
        r = self.call('post', '/api/staff/', self.staff(), 201)
        self.assertNotIn('password', r)
        self.assertNotEqual(User.objects.get(email='new@musabe.test').password, 'Strong-pass-77')

    def test_deactivated_staff_cannot_log_in(self):
        self.login('admin@musabe.test')
        r = self.call('post', '/api/staff/', self.staff(), 201)
        self.call('patch', f'/api/staff/{r["id"]}/', {'is_active': False})
        self.client.credentials()
        resp = self.client.post('/api/auth/login/', {'email': 'new@musabe.test', 'password': 'Strong-pass-77'}, format='json')
        self.assertEqual(resp.status_code, 401)

    def test_login_is_rate_limited(self):
        with mock.patch.dict(SimpleRateThrottle.THROTTLE_RATES, {'login': '3/min'}):
            codes = [self.client.post('/api/auth/login/', {'email': 'admin@musabe.test', 'password': 'wrong'}, format='json').status_code
                     for _ in range(5)]
        self.assertEqual(codes[:3], [401, 401, 401])
        self.assertEqual(codes[3:], [429, 429])

    def test_endpoints_need_a_token(self):
        self.client.credentials()
        for url in ('/api/me/', '/api/requests/', '/api/items/', '/api/students/', '/api/reports/stock/', '/api/audit/'):
            self.assertEqual(self.client.get(url).status_code, 401, url)

    def test_audit_trail_records_registration_and_is_read_only(self):
        self.login('admin@musabe.test')
        r = self.call('post', '/api/staff/', self.staff(), 201)
        actions = {(a['action'], a['entity_id']) for a in self.call('get', '/api/audit/')}
        self.assertIn(('staff.registered', r['id']), actions)
        self.call('post', '/api/audit/', {'action': 'x'}, 405)
        self.call('delete', '/api/audit/1/', expect=405)
