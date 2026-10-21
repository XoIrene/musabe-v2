from datetime import date, timedelta

from core.tests.base import SchoolAPITestCase
from inventory.models import BookCopy, Category, Item, Movement


class StoreRulesTests(SchoolAPITestCase):
    """Issuing, returns, write-offs and parent contributions (proposal section 8)."""

    def make_book(self, branch):
        item = Item.objects.create(branch=branch, name='Physics F1', category=Category.BOOK)
        return BookCopy.objects.create(item=item, branch=branch, code=BookCopy.next_codes(item, 1)[0])

    def test_only_the_librarian_issues_and_returns(self):
        copy = self.make_book(self.gss)
        for who in ('head.girls@musabe.test', 'academic.girls@musabe.test', 'teacher.girls@musabe.test', 'manager@musabe.test'):
            self.login(who); self.call('post', '/api/issues/', {'code': copy.code, 'borrower_name': 'X'}, 403)
        self.login('librarian.boys@musabe.test')
        self.call('post', '/api/issues/', {'code': copy.code, 'borrower_name': 'X'}, 403)   # another school's library
        self.login('librarian.girls@musabe.test')
        issue = self.call('post', '/api/issues/', {'code': copy.code, 'borrower_name': 'Neema'}, 201)
        self.call('post', '/api/issues/', {'code': copy.code, 'borrower_name': 'Joel'}, 400)  # already out
        self.login('head.girls@musabe.test'); self.call('post', f'/api/issues/{issue["id"]}/return/', expect=403)
        self.login('librarian.girls@musabe.test'); self.call('post', f'/api/issues/{issue["id"]}/return/')
        self.call('post', f'/api/issues/{issue["id"]}/return/', expect=400)                   # not twice
        copy.refresh_from_db()
        self.assertEqual(copy.status, 'AVAILABLE')
        self.assertEqual(list(Movement.objects.filter(copy=copy).values_list('type', flat=True).order_by('id')), ['OUT_ISSUE', 'IN_RETURN'])

    def test_write_off_needs_the_head_master(self):
        copy = self.make_book(self.gss)
        self.login('head.girls@musabe.test')
        self.call('post', '/api/writeoffs/', {'code': copy.code, 'kind': 'LOST', 'reason': 'x'}, 403)   # Head Master does not start reports
        self.login('librarian.girls@musabe.test')
        self.call('post', '/api/writeoffs/', {'code': copy.code, 'kind': 'LOST', 'reason': ''}, 400)    # reason needed
        w = self.call('post', '/api/writeoffs/', {'code': copy.code, 'kind': 'LOST', 'reason': 'Lost on bus'}, 201)
        self.call('post', '/api/writeoffs/', {'code': copy.code, 'kind': 'DAMAGED', 'reason': 'again'}, 400)  # one report per copy
        self.call('post', f'/api/writeoffs/{w["id"]}/decide/', {'approve': True}, 403)           # Librarian cannot approve own report
        self.login('head.boys@musabe.test'); self.call('post', f'/api/writeoffs/{w["id"]}/decide/', {'approve': True}, 404)
        self.login('head.girls@musabe.test')
        self.call('post', f'/api/writeoffs/{w["id"]}/decide/', {'approve': True})
        self.call('post', f'/api/writeoffs/{w["id"]}/decide/', {'approve': True}, 400)           # already decided
        copy.refresh_from_db()
        self.assertEqual(copy.status, 'WRITTEN_OFF')
        self.assertTrue(Movement.objects.filter(copy=copy, type='OUT_WRITEOFF').exists())

    def test_rejected_write_off_restores_the_copy(self):
        copy = self.make_book(self.gss)
        self.login('librarian.girls@musabe.test')
        w = self.call('post', '/api/writeoffs/', {'code': copy.code, 'kind': 'DAMAGED', 'reason': 'Torn cover'}, 201)
        self.login('head.girls@musabe.test'); self.call('post', f'/api/writeoffs/{w["id"]}/decide/', {'approve': False, 'note': 'Repair it'})
        copy.refresh_from_db()
        self.assertEqual(copy.status, 'AVAILABLE')

    def test_a_lost_book_on_loan_closes_the_loan_when_written_off(self):
        copy = self.make_book(self.gss)
        self.login('librarian.girls@musabe.test')
        self.call('post', '/api/issues/', {'code': copy.code, 'borrower_name': 'Neema'}, 201)
        w = self.call('post', '/api/writeoffs/', {'code': copy.code, 'kind': 'LOST', 'reason': 'Never returned'}, 201)
        self.login('head.girls@musabe.test'); self.call('post', f'/api/writeoffs/{w["id"]}/decide/', {'approve': True})
        self.login('librarian.girls@musabe.test')
        self.assertEqual(self.call('get', '/api/issues/?open=1'), [])

    def test_parent_contributions_are_primary_only(self):
        self.login('librarian.primary@musabe.test')
        self.call('post', '/api/contributions/', {'branch': self.nps.id, 'name': 'Soap', 'quantity': 0}, 400)
        self.call('post', '/api/contributions/', {'branch': self.nps.id, 'name': 'Soap', 'quantity': 20, 'parent_name': 'Mama X'}, 201)
        self.call('post', '/api/contributions/', {'branch': self.nps.id, 'name': 'Soap', 'quantity': 5}, 201)
        soap = Item.objects.get(branch=self.nps, name='Soap')
        self.assertEqual(soap.on_hand, 25)                                                   # stock goes up
        self.assertEqual(Movement.objects.filter(item=soap, type='IN_PARENT').count(), 2)   # and is recorded
        self.login('librarian.girls@musabe.test')
        self.call('post', '/api/contributions/', {'branch': self.gss.id, 'name': 'Soap', 'quantity': 5}, 400)
        self.call('post', '/api/contributions/', {'branch': self.nps.id, 'name': 'Soap', 'quantity': 5}, 403)  # not their school
        self.login('head.primary@musabe.test')
        self.call('post', '/api/contributions/', {'branch': self.nps.id, 'name': 'Soap', 'quantity': 5}, 403)  # only the Librarian records

    def test_loans_with_due_dates(self):
        copy = self.make_book(self.nps)
        self.login('librarian.primary@musabe.test')
        due = (date.today() - timedelta(days=3)).isoformat()
        self.call('post', '/api/issues/', {'code': copy.code, 'borrower_name': 'Late Larry', 'due_date': due}, 201)
        self.assertEqual(self.call('get', '/api/issues/?open=1')[0]['due_date'], due)
