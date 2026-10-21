from datetime import date, timedelta

from core.tests.base import SchoolAPITestCase
from fees.models import Fee
from inventory.models import BookCopy, Category, Item


class ReportTests(SchoolAPITestCase):
    def setUp(self):
        super().setUp()
        item = Item.objects.create(branch=self.gss, name='Chem F1', category=Category.BOOK)
        self.copy = BookCopy.objects.create(item=item, branch=self.gss, code=BookCopy.next_codes(item, 1)[0])
        Item.objects.create(branch=self.gss, name='Chalk', category=Category.STATIONERY, quantity=2, reorder_level=5)

    def rows(self, url):
        return self.call('get', url)['rows']

    def test_overdue_loans(self):
        self.login('librarian.girls@musabe.test')
        past = (date.today() - timedelta(days=4)).isoformat()
        self.call('post', '/api/issues/', {'code': self.copy.code, 'borrower_name': 'Neema', 'due_date': past}, 201)
        r = self.call('get', '/api/reports/overdue/')
        self.assertEqual(r['summary']['overdue_loans'], 1)
        self.assertEqual((r['rows'][0][0], r['rows'][0][7]), (self.copy.code, 4))
        self.call('post', f'/api/issues/{self.call("get", "/api/issues/?open=1")[0]["id"]}/return/')
        self.assertEqual(self.rows('/api/reports/overdue/'), [])                      # returned books drop off
        self.login('librarian.boys@musabe.test')
        self.assertEqual(self.rows('/api/reports/overdue/'), [])                      # and other schools never see it

    def test_overdue_scoping(self):
        self.login('librarian.girls@musabe.test')
        self.call('post', '/api/issues/', {'code': self.copy.code, 'borrower_name': 'N', 'due_date': '2020-01-01'}, 201)
        self.login('librarian.boys@musabe.test')
        self.assertEqual(self.rows('/api/reports/overdue/'), [])
        self.call('get', f'/api/reports/overdue/?branch={self.gss.id}', expect=404)  # cannot ask for another school
        self.login('manager@musabe.test')
        self.assertEqual(len(self.rows('/api/reports/overdue/')), 1)

    def test_stock_flags_low_items(self):
        self.login('librarian.girls@musabe.test')
        r = self.call('get', '/api/reports/stock/')
        self.assertEqual(r['summary']['low_stock'], 2)             # the book title (1 copy) and the chalk
        chalk = [row for row in r['rows'] if row[1] == 'Chalk'][0]
        self.assertEqual((chalk[4], chalk[6]), (2, 'LOW'))
        self.assertTrue(all(row[0] == self.gss.name for row in r['rows']))

    def test_requests_report_filters_and_waiting_on(self):
        self.login('teacher.girls@musabe.test')
        self.call('post', '/api/requests/', {'kind': 'BOOKS', 'branch': self.gss.id, 'title': 'Bio', 'lines': [{'name': 'Bio', 'quantity': 1}]}, 201)
        self.login('head.girls@musabe.test')
        r = self.call('get', '/api/reports/requests/')
        self.assertEqual(r['summary']['total'], 1)
        self.assertEqual(r['rows'][0][6], 'Academic Master')
        self.assertEqual(self.rows('/api/reports/requests/?status=COMPLETED'), [])
        self.assertEqual(self.rows('/api/reports/requests/?kind=OTHER'), [])
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        self.assertEqual(self.rows(f'/api/reports/requests/?from={tomorrow}'), [])
        self.call('get', '/api/reports/requests/?from=yesterday', expect=400)
        self.login('head.boys@musabe.test')
        self.assertEqual(self.rows('/api/reports/requests/'), [])

    def test_movements_report(self):
        self.login('librarian.girls@musabe.test')
        self.call('post', '/api/issues/', {'code': self.copy.code, 'borrower_name': 'N'}, 201)
        r = self.call('get', '/api/reports/movements/')
        self.assertEqual((r['summary']['movements'], r['summary']['out']), (1, 1))
        self.assertEqual(self.rows('/api/reports/movements/?to=2000-01-01'), [])

    def test_fees_report(self):
        fee = Fee.objects.get(branch=self.nps)
        self.login('bursar@musabe.test')
        self.call('post', f'/api/fees/{fee.id}/generate/')
        inv = self.call('get', '/api/invoices/')[0]
        self.call('post', f'/api/invoices/{inv["id"]}/pay/', {'amount': 100000, 'method': 'CASH'})
        s = self.call('get', f'/api/reports/fees/?branch={self.nps.id}')['summary']
        self.assertEqual(s['collected'], 100000.0)
        self.assertEqual(s['outstanding'], s['billed'] - 100000.0)
        self.assertEqual(s['students_owing'], 12)
        self.login('head.girls@musabe.test')
        self.assertEqual(self.call('get', '/api/reports/fees/')['summary']['billed'], 0.0)   # sees only own school

    def test_who_can_open_which_report(self):
        cases = {'fees': ['admin', 'manager', 'bursar', 'head.girls'], 'requests': ['admin', 'manager', 'head.girls', 'librarian.girls'],
                 'stock': ['admin', 'store', 'librarian.girls'], 'overdue': ['manager', 'librarian.girls']}
        denied = {'fees': ['librarian.girls', 'teacher.girls', 'store', 'parent'], 'requests': ['bursar', 'store', 'teacher.girls', 'parent'],
                  'stock': ['bursar', 'teacher.girls', 'parent'], 'overdue': ['bursar', 'teacher.girls', 'parent']}
        for name, who in cases.items():
            for w in who:
                self.login(f'{w}@musabe.test'); self.call('get', f'/api/reports/{name}/')
        for name, who in denied.items():
            for w in who:
                self.login(f'{w}@musabe.test'); self.call('get', f'/api/reports/{name}/', expect=403)
        self.call('get', '/api/reports/nonsense/', expect=404)

    def test_csv_export_and_formula_safety(self):
        self.login('librarian.girls@musabe.test')
        self.call('post', '/api/issues/', {'code': self.copy.code, 'borrower_name': '=HYPERLINK("http://evil")', 'due_date': '2020-01-01'}, 201)
        res = self.client.get('/api/reports/overdue/?export=csv')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res['Content-Type'].startswith('text/csv'))
        self.assertIn('attachment', res['Content-Disposition'])
        body = res.content.decode()
        self.assertTrue(body.startswith('Book code,Title,Borrower'))
        self.assertIn("'=HYPERLINK", body)           # defused: a spreadsheet will show it as text
        self.assertNotIn(',=HYPERLINK', body)
