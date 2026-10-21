from django.core.management import call_command
from rest_framework.test import APITestCase

from core.models import Branch, User
from inventory.models import BookCopy, Item


class FlowTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo', verbosity=0)
        cls.girls = Branch.objects.get(code='GSS')
        cls.primary = Branch.objects.get(code='NPS')

    def login(self, email):
        r = self.client.post('/api/auth/login/', {'email': email, 'password': 'musabe123'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + r.data['access'])

    def act(self, rid, action, expect=200, **extra):
        r = self.client.post(f'/api/requests/{rid}/act/', {'action': action, **extra}, format='json')
        self.assertEqual(r.status_code, expect, r.content)
        return r.data

    def test_book_buying_full_chain(self):
        self.login('teacher.girls@musabe.test')
        r = self.client.post('/api/requests/', {'kind': 'BOOKS', 'branch': self.girls.id, 'title': 'Form 1 Biology',
                             'lines': [{'name': 'Biology Form 1', 'author': 'TIE', 'quantity': 3}]}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        rid = r.data['id']
        # wrong role cannot jump ahead
        self.login('librarian.girls@musabe.test'); self.act(rid, 'submit_requisition', 400)
        self.login('academic.girls@musabe.test'); self.act(rid, 'approve')
        self.login('academic.boys@musabe.test'); self.act(rid, 'approve', 404)   # other school cannot even see it
        self.login('head.boys@musabe.test'); self.act(rid, 'approve', 404)        # other school's head
        self.login('head.girls@musabe.test'); self.act(rid, 'approve')
        self.login('librarian.girls@musabe.test'); self.act(rid, 'submit_requisition')
        self.login('bursar@musabe.test'); self.act(rid, 'make_po')
        self.login('manager@musabe.test'); self.act(rid, 'approve')
        self.login('store@musabe.test'); self.act(rid, 'place_order', 400)         # supplier required
        self.act(rid, 'place_order', supplier='Mkuki na Nyota')
        self.act(rid, 'record_delivery')
        self.login('bursar@musabe.test'); self.act(rid, 'pay', 400)               # cannot pay before verification
        self.login('librarian.girls@musabe.test'); self.act(rid, 'verify', 403)    # not the requestor
        self.login('teacher.girls@musabe.test'); self.act(rid, 'verify')
        self.login('bursar@musabe.test'); self.act(rid, 'pay')
        self.login('store@musabe.test'); self.act(rid, 'dispatch')
        self.login('librarian.girls@musabe.test'); self.act(rid, 'receive')
        self.assertEqual(BookCopy.objects.filter(branch=self.girls).count(), 3)
        codes = list(BookCopy.objects.values_list('code', flat=True))
        self.assertEqual(len(set(codes)), 3)

        # issue a book, then lose it and have it written off
        code = codes[0]
        r = self.client.post('/api/issues/', {'code': code, 'borrower_name': 'Neema'}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        r2 = self.client.post('/api/issues/', {'code': code, 'borrower_name': 'Joel'}, format='json')
        self.assertEqual(r2.status_code, 400)  # already issued
        w = self.client.post('/api/writeoffs/', {'code': code, 'kind': 'LOST', 'reason': 'Student left'}, format='json')
        self.assertEqual(w.status_code, 201, w.content)
        self.login('head.girls@musabe.test')
        d = self.client.post(f'/api/writeoffs/{w.data["id"]}/decide/', {'approve': True}, format='json')
        self.assertEqual(d.status_code, 200, d.content)
        self.assertEqual(BookCopy.objects.get(code=code).status, 'WRITTEN_OFF')
        self.assertTrue(self.client.get('/api/audit/').data)

    def test_other_items_and_parent_contribution(self):
        self.login('teacher.primary@musabe.test')
        r = self.client.post('/api/requests/', {'kind': 'OTHER', 'branch': self.primary.id, 'title': 'Chalk',
                             'lines': [{'name': 'Chalk box', 'category': 'STATIONERY', 'quantity': 20}]}, format='json')
        rid = r.data['id']
        self.login('head.primary@musabe.test'); self.act(rid, 'approve')   # Head OR Academic is enough
        self.login('librarian.primary@musabe.test'); self.act(rid, 'forward')
        self.login('bursar@musabe.test'); self.act(rid, 'forward')
        self.login('manager@musabe.test'); self.act(rid, 'approve')
        self.login('store@musabe.test'); self.act(rid, 'place_order', supplier='ABC'); self.act(rid, 'record_delivery')
        self.login('teacher.primary@musabe.test'); self.act(rid, 'verify')
        self.login('bursar@musabe.test'); self.act(rid, 'pay')
        self.login('store@musabe.test'); self.act(rid, 'dispatch')
        self.login('librarian.primary@musabe.test'); self.act(rid, 'receive')
        self.assertEqual(Item.objects.get(name='Chalk box').quantity, 20)
        r = self.client.post('/api/issues/', {'item': Item.objects.get(name='Chalk box').id, 'quantity': 5,
                             'borrower_name': 'Class 3A'}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Item.objects.get(name='Chalk box').quantity, 15)
        r = self.client.post('/api/contributions/', {'branch': self.primary.id, 'name': 'Soap', 'quantity': 40}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        # not allowed in a secondary school
        self.login('librarian.girls@musabe.test')
        r = self.client.post('/api/contributions/', {'branch': self.girls.id, 'name': 'Soap', 'quantity': 4}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_admin_registration_and_scoping(self):
        self.login('admin@musabe.test')
        r = self.client.post('/api/staff/', {'full_name': 'New Lib', 'email': 'new@musabe.test', 'password': 'longpass123',
                             'role': 'LIBRARIAN', 'branches': [self.girls.id, self.primary.id]}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        bad = self.client.post('/api/staff/', {'full_name': 'X', 'email': 'x@musabe.test', 'password': 'longpass123',
                               'role': 'BURSAR', 'branches': [self.girls.id]}, format='json')
        self.assertEqual(bad.status_code, 400)
        self.login('teacher.girls@musabe.test')
        self.assertEqual(self.client.get('/api/staff/').status_code, 403)
        self.assertEqual(self.client.post('/api/branches/', {'name': 'Z', 'code': 'Z', 'type': 'PRIMARY'}).status_code, 403)
