from datetime import date

from django.core.management import call_command
from rest_framework.test import APITestCase

from core.models import Branch, User
from inventory.models import BookCopy, Category, Item
from students.models import Guardian, Student


class SchoolModulesTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo', verbosity=0)
        call_command('seed_school_data', verbosity=0)
        cls.nps = Branch.objects.get(code='NPS')
        cls.gss = Branch.objects.get(code='GSS')
        cls.kid = Guardian.objects.get(full_name='Mama Neema').students.first()
        cls.other_kid = Student.objects.filter(branch=cls.nps).exclude(guardians__isnull=False).first()

    def login(self, email, password='musabe123'):
        r = self.client.post('/api/auth/login/', {'email': email, 'password': password}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + r.data['access'])

    def ok(self, method, url, data=None, expect=200):
        r = getattr(self.client, method)(url, data, format='json')
        self.assertEqual(r.status_code, expect, f'{method} {url} -> {r.status_code} {r.content[:300]}')
        return r.data

    # ---- students, parents, scoping -------------------------------------------------------------
    def test_registration_and_school_scope(self):
        self.login('head.girls@musabe.test')
        room = self.gss.classrooms.first()
        s = self.ok('post', '/api/students/', {'branch': self.gss.id, 'admission_no': 'X1', 'full_name': 'Test Girl', 'gender': 'F',
                                                'classroom': room.id}, 201)
        self.ok('post', '/api/students/', {'branch': self.nps.id, 'admission_no': 'X2', 'full_name': 'Nope', 'gender': 'F'}, 403)
        self.ok('post', '/api/students/', {'branch': self.gss.id, 'admission_no': 'X1', 'full_name': 'Dup', 'gender': 'F'}, 400)
        self.ok('delete', f'/api/students/{s["id"]}/', expect=405)
        self.login('head.boys@musabe.test')
        self.ok('get', f'/api/students/{s["id"]}/', expect=404)         # other school's student
        self.login('teacher.girls@musabe.test')
        self.ok('post', '/api/students/', {'branch': self.gss.id, 'admission_no': 'X3', 'full_name': 'T', 'gender': 'F'}, 403)
        self.login('store@musabe.test')
        self.ok('get', '/api/students/', expect=403)

    def test_parent_sees_only_own_children_and_nothing_else(self):
        self.login('parent@musabe.test')
        mine = self.ok('get', '/api/students/')
        self.assertEqual(len(mine), 2)
        self.ok('get', f'/api/students/{self.other_kid.id}/', expect=404)
        self.ok('get', f'/api/reports/student/{self.other_kid.id}/', expect=404)
        self.ok('get', f'/api/reports/student/{self.kid.id}/')
        for url in ('/api/requests/', '/api/items/', '/api/staff/', '/api/audit/', '/api/reports/summary/', '/api/guardians/', '/api/issues/'):
            self.ok('get', url, expect=403)
        self.ok('post', '/api/students/', {'branch': self.nps.id, 'admission_no': 'P', 'full_name': 'P', 'gender': 'F'}, 403)
        self.ok('post', '/api/announcements/', {'title': 't', 'body': 'b'}, 403)
        self.assertEqual(self.ok('get', '/api/me/')['role'], 'PARENT')

    def test_parent_login_created_by_head_master(self):
        self.login('head.primary@musabe.test')
        g = self.ok('post', '/api/guardians/', {'full_name': 'Baba Joel', 'phone': '07', 'students': [self.other_kid.id]}, 201)
        self.ok('post', f'/api/guardians/{g["id"]}/create_login/', {'email': 'baba@x.test', 'password': 'longpassword1'})
        self.ok('post', f'/api/guardians/{g["id"]}/create_login/', {'email': 'baba@x.test', 'password': 'longpassword1'}, 400)
        self.login('teacher.primary@musabe.test')
        self.ok('post', f'/api/guardians/{g["id"]}/create_login/', {'email': 'q@x.test', 'password': 'longpassword1'}, 403)
        self.login('baba@x.test', 'longpassword1')
        self.assertEqual([s['id'] for s in self.ok('get', '/api/students/')], [self.other_kid.id])
        # the Admin cannot create a Parent through the normal staff form
        self.login('admin@musabe.test')
        self.ok('post', '/api/staff/', {'full_name': 'P', 'email': 'p@x.test', 'password': 'longpassword1', 'role': 'PARENT',
                                        'branches': [self.nps.id]}, 400)

    # ---- library link ---------------------------------------------------------------------------
    def test_library_link(self):
        item = Item.objects.create(branch=self.nps, name='Maths Std 1', category=Category.BOOK)
        copy = BookCopy.objects.create(item=item, branch=self.nps, code=BookCopy.next_codes(item, 1)[0])
        self.login('librarian.primary@musabe.test')
        self.ok('post', '/api/issues/', {'code': copy.code, 'student': Student.objects.filter(branch=self.gss).first().id}, 403)
        self.ok('post', '/api/issues/', {'code': copy.code, 'student': self.kid.id}, 201)
        loans = self.ok('get', f'/api/students/{self.kid.id}/loans/')
        self.assertEqual(loans[0]['borrower_name'], self.kid.full_name)
        self.login('parent@musabe.test')
        self.assertEqual(len(self.ok('get', f'/api/students/{self.kid.id}/loans/')), 1)
        self.ok('get', f'/api/students/{self.other_kid.id}/loans/', expect=404)

    # ---- academics ------------------------------------------------------------------------------
    def test_marks_attendance_and_report(self):
        room = self.kid.classroom
        term = self.nps.terms.first()
        subject = self.nps.subjects.get(name='Mathematics')
        self.login('teacher.primary@musabe.test')
        a = self.ok('post', '/api/assessments/', {'term': term.id, 'subject': subject.id, 'classroom': room.id, 'name': 'Midterm',
                                                   'max_score': 50}, 201)
        self.ok('post', f'/api/assessments/{a["id"]}/marks/', {'marks': [{'student': self.kid.id, 'score': 51}]}, 400)  # over max
        self.ok('post', f'/api/assessments/{a["id"]}/marks/', {'marks': [{'student': self.kid.id, 'score': 40}]})
        self.ok('post', f'/api/assessments/{a["id"]}/marks/', {'marks': [{'student': self.kid.id, 'score': 45}]})      # update, not duplicate
        self.ok('post', f'/api/assessments/{a["id"]}/marks/', {'marks': [{'student': self.other_kid.id, 'score': 10}]}, 400 if self.other_kid.classroom_id != room.id else 200)
        today = date.today().isoformat()
        self.ok('post', '/api/attendance/mark/', {'classroom': room.id, 'date': today, 'records': [{'student': self.kid.id, 'status': 'P'}]})
        self.ok('post', '/api/attendance/mark/', {'classroom': room.id, 'date': today, 'records': [{'student': self.kid.id, 'status': 'A'}]})
        self.login('teacher.girls@musabe.test')   # another school's teacher
        self.ok('post', f'/api/assessments/{a["id"]}/marks/', {'marks': []}, 404)
        self.login('parent@musabe.test')
        rep = self.ok('get', f'/api/reports/student/{self.kid.id}/')
        self.assertEqual(rep['terms'][0]['subjects'][0]['average'], 90.0)
        self.assertEqual(rep['attendance'], {'present': 0, 'late': 0, 'absent': 1, 'days': 1, 'percent': 0.0})
        self.ok('post', f'/api/assessments/{a["id"]}/marks/', {'marks': []}, 403)

    # ---- fees -----------------------------------------------------------------------------------
    def test_fees_flow(self):
        self.login('bursar@musabe.test')
        fee = self.nps.fees.first()
        n = Student.objects.filter(branch=self.nps, status='ACTIVE').count()
        self.assertEqual(self.ok('post', f'/api/fees/{fee.id}/generate/')['created'], n)
        self.assertEqual(self.ok('post', f'/api/fees/{fee.id}/generate/')['created'], 0)   # never billed twice
        inv = self.ok('get', f'/api/invoices/?student={self.kid.id}')[0]
        self.ok('post', f'/api/invoices/{inv["id"]}/pay/', {'amount': 999999999, 'method': 'CASH'}, 400)
        self.ok('post', f'/api/invoices/{inv["id"]}/pay/', {'amount': 100000, 'method': 'MOBILE', 'reference': 'M-PESA 1'})
        paid = self.ok('post', f'/api/invoices/{inv["id"]}/pay/', {'amount': 300000, 'method': 'BANK'})
        self.assertEqual(float(paid['balance']), 0.0)
        self.ok('post', f'/api/invoices/{inv["id"]}/pay/', {'amount': 1, 'method': 'CASH'}, 400)  # nothing left
        self.login('head.primary@musabe.test')
        self.ok('post', f'/api/invoices/{inv["id"]}/pay/', {'amount': 1, 'method': 'CASH'}, 403)
        self.login('head.girls@musabe.test')
        self.assertEqual(self.ok('get', '/api/invoices/'), [])
        self.login('parent@musabe.test')
        mine = self.ok('get', '/api/invoices/')
        self.assertEqual({i['student'] for i in mine}, {s.id for s in Guardian.objects.get(full_name='Mama Neema').students.all()})
        self.ok('post', f'/api/fees/', {'branch': self.nps.id, 'name': 'x', 'amount': 5}, 403)

    # ---- transport & announcements --------------------------------------------------------------
    def test_transport(self):
        route = self.nps.routes.first()
        self.login('head.primary@musabe.test')
        self.ok('post', '/api/transport/', {'student': self.kid.id, 'route': route.id, 'pickup_point': 'Nyegezi'}, 201)
        self.ok('post', '/api/transport/', {'student': self.kid.id, 'route': route.id}, 400)    # one route per student
        route.capacity = 1
        route.save()
        self.ok('post', '/api/transport/', {'student': self.other_kid.id, 'route': route.id}, 400)  # full
        self.login('head.girls@musabe.test')
        self.ok('post', '/api/transport/', {'student': Student.objects.filter(branch=self.gss).first().id, 'route': route.id}, 400)   # a school cannot use another school's bus
        self.login('parent@musabe.test')
        self.assertEqual(len(self.ok('get', '/api/routes/')), 1)
        self.ok('post', '/api/routes/', {'branch': self.nps.id, 'name': 'x'}, 403)

    def test_announcements_audiences(self):
        self.login('head.primary@musabe.test')
        self.ok('post', '/api/announcements/', {'title': 'Parents meeting', 'body': 'Friday', 'audience': 'PARENTS', 'branch': self.nps.id}, 201)
        self.ok('post', '/api/announcements/', {'title': 'Staff only', 'body': 'x', 'audience': 'STAFF', 'branch': self.nps.id}, 201)
        self.ok('post', '/api/announcements/', {'title': 'Other school', 'body': 'x', 'branch': self.gss.id}, 400)
        self.ok('post', '/api/announcements/', {'title': 'All schools', 'body': 'x'}, 400)   # only Central writes for everyone
        self.login('parent@musabe.test')
        titles = {a['title'] for a in self.ok('get', '/api/announcements/')}
        self.assertIn('Parents meeting', titles)
        self.assertNotIn('Staff only', titles)
        self.login('teacher.girls@musabe.test')
        self.assertNotIn('Parents meeting', {a['title'] for a in self.ok('get', '/api/announcements/')})
        self.login('manager@musabe.test')
        self.ok('post', '/api/announcements/', {'title': 'Closure', 'body': 'x', 'audience': 'ALL'}, 201)
