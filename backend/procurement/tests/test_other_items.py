from core.tests.base import SchoolAPITestCase
from inventory.models import Item, Movement


class OtherItemsFlowTests(SchoolAPITestCase):
    """Section 7 of the proposal: the shorter, 9-step path for stationery, uniforms, vitambaa and Primary items."""

    def raise_request(self, who='teacher.primary@musabe.test'):
        self.login(who)
        r = self.call('post', '/api/requests/', {'kind': 'OTHER', 'branch': self.nps.id, 'title': 'Uniforms',
                      'lines': [{'name': 'Uniform shirt', 'category': 'UNIFORM', 'size': 'M', 'quantity': 10}]}, 201)
        self.assertEqual(r['status'], 'PENDING_APPROVAL')
        return r['id']

    def run_to_manager(self, rid, approver='academic.primary@musabe.test'):
        self.login(approver); self.act(rid, 'approve')
        self.login('librarian.primary@musabe.test'); self.act(rid, 'forward')
        self.login('bursar@musabe.test'); self.act(rid, 'forward')

    def test_full_chain_and_stock(self):
        rid = self.raise_request()
        self.login('bursar@musabe.test'); self.act(rid, 'forward', 404)          # Central does not even see it until the school is done
        self.login('store@musabe.test'); self.act(rid, 'place_order', 404)
        self.run_to_manager(rid)
        self.login('manager@musabe.test'); self.act(rid, 'approve')
        self.login('store@musabe.test')
        self.act(rid, 'place_order', 400)                                        # supplier name required
        self.act(rid, 'place_order', supplier='Dar Uniforms')
        self.act(rid, 'record_delivery')
        self.login('bursar@musabe.test'); self.act(rid, 'pay', 400)             # not before the requestor checks
        self.login('librarian.primary@musabe.test'); self.act(rid, 'verify', 403)
        self.login('teacher.primary@musabe.test'); self.act(rid, 'verify')
        self.login('bursar@musabe.test'); self.act(rid, 'pay')
        self.login('store@musabe.test'); self.act(rid, 'dispatch')
        self.login('librarian.primary@musabe.test')
        self.assertEqual(self.act(rid, 'receive')['status'], 'COMPLETED')
        item = Item.objects.get(branch=self.nps, name='Uniform shirt', size='M')
        self.assertEqual(item.on_hand, 10)
        self.assertTrue(Movement.objects.filter(item=item, type='IN_PURCHASE', quantity=10).exists())
        # issued by size/quantity, never more than is in stock
        self.call('post', '/api/issues/', {'item': item.id, 'quantity': 3, 'borrower_name': 'Pupil'}, 201)
        self.call('post', '/api/issues/', {'item': item.id, 'quantity': 8, 'borrower_name': 'Pupil'}, 400)
        item.refresh_from_db()
        self.assertEqual(item.on_hand, 7)

    def test_head_master_can_approve_instead_of_academic_master(self):
        rid = self.raise_request()
        self.run_to_manager(rid, approver='head.primary@musabe.test')
        self.assertEqual(self.client.get(f'/api/requests/{rid}/').data['status'], 'PENDING_MANAGER')

    def test_rejection_stops_the_request(self):
        rid = self.raise_request()
        self.login('academic.primary@musabe.test')
        self.act(rid, 'reject', 400)                                             # a reason is required
        self.assertEqual(self.act(rid, 'reject', note='Not needed')['status'], 'REJECTED')
        self.login('librarian.primary@musabe.test'); self.act(rid, 'forward', 400)

    def test_other_schools_cannot_approve_or_see_it(self):
        rid = self.raise_request()
        for who in ('academic.girls@musabe.test', 'head.boys@musabe.test'):
            self.login(who); self.act(rid, 'approve', 404)

    def test_disputed_delivery_goes_back_to_ordered(self):
        rid = self.raise_request()
        self.run_to_manager(rid)
        self.login('manager@musabe.test'); self.act(rid, 'approve')
        self.login('store@musabe.test'); self.act(rid, 'place_order', supplier='X'); self.act(rid, 'record_delivery')
        self.login('teacher.primary@musabe.test')
        self.act(rid, 'dispute', 400)                                            # needs a note
        self.assertEqual(self.act(rid, 'dispute', note='Only 6 shirts')['status'], 'ORDERED')
