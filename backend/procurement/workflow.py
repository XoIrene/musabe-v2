"""The approval chains from the proposal, as data.

Books (sec. 6):  Teacher -> Academic Master -> Head Master -> Librarian (requisition)
                 -> Bursar (PO) -> Manager -> Storekeeper (order) -> Supplier -> Storekeeper (receive)
                 -> Requestor (verify) -> Bursar (pay) -> Storekeeper (send) -> Librarian (catalogue)
Other (sec. 7):  Staff -> Academic Master OR Head Master -> Librarian -> Bursar -> Manager
                 -> Storekeeper (order) -> Supplier -> Storekeeper (receive) -> Requestor (verify)
                 -> Bursar (pay) -> Storekeeper (send) -> Librarian (store)
"""
from dataclasses import dataclass

from core.models import Role

R = Role


class S:
    PENDING_ACADEMIC = 'PENDING_ACADEMIC'
    PENDING_HEAD = 'PENDING_HEAD'
    PENDING_APPROVAL = 'PENDING_APPROVAL'      # other items: Academic OR Head Master
    PENDING_REQUISITION = 'PENDING_REQUISITION'
    PENDING_LIBRARIAN = 'PENDING_LIBRARIAN'
    PENDING_PO = 'PENDING_PO'                  # books: Bursar makes the PO
    PENDING_BURSAR = 'PENDING_BURSAR'          # other items: Bursar passes to Manager
    PENDING_MANAGER = 'PENDING_MANAGER'
    PENDING_ORDER = 'PENDING_ORDER'
    ORDERED = 'ORDERED'
    DELIVERED = 'DELIVERED'
    VERIFIED = 'VERIFIED'
    PAID = 'PAID'
    DISPATCHED = 'DISPATCHED'
    COMPLETED = 'COMPLETED'
    REJECTED = 'REJECTED'


@dataclass(frozen=True)
class T:
    action: str
    label: str
    roles: tuple
    to: str
    requestor_only: bool = False
    needs_note: bool = False
    needs_supplier: bool = False


def _reject(*roles):
    return T('reject', 'Reject', roles, S.REJECTED, needs_note=True)


# Steps shared by both paths once the request reaches Central Administration's Manager.
_TAIL = {
    S.PENDING_MANAGER: [T('approve', 'Approve purchase', (R.MANAGER,), S.PENDING_ORDER), _reject(R.MANAGER)],
    S.PENDING_ORDER: [T('place_order', 'Order from supplier', (R.STOREKEEPER,), S.ORDERED, needs_supplier=True)],
    S.ORDERED: [T('record_delivery', 'Record delivery from supplier', (R.STOREKEEPER,), S.DELIVERED)],
    S.DELIVERED: [
        T('verify', 'Items match the request', (R.ADMIN, R.MANAGER, R.BURSAR, R.STOREKEEPER, R.HEAD_MASTER,
                                                R.ACADEMIC_MASTER, R.LIBRARIAN, R.STAFF), S.VERIFIED, requestor_only=True),
        T('dispute', 'Items do NOT match', (R.ADMIN, R.MANAGER, R.BURSAR, R.STOREKEEPER, R.HEAD_MASTER,
                                            R.ACADEMIC_MASTER, R.LIBRARIAN, R.STAFF), S.ORDERED,
          requestor_only=True, needs_note=True),
    ],
    S.VERIFIED: [T('pay', 'Pay supplier', (R.BURSAR,), S.PAID)],
    S.PAID: [T('dispatch', 'Send goods to school', (R.STOREKEEPER,), S.DISPATCHED)],
}

TRANSITIONS = {
    'BOOKS': {
        S.PENDING_ACADEMIC: [T('approve', 'Approve (academic)', (R.ACADEMIC_MASTER,), S.PENDING_HEAD), _reject(R.ACADEMIC_MASTER)],
        S.PENDING_HEAD: [T('approve', 'Approve (Head Master)', (R.HEAD_MASTER,), S.PENDING_REQUISITION), _reject(R.HEAD_MASTER)],
        S.PENDING_REQUISITION: [T('submit_requisition', 'Write & send Purchase Requisition', (R.LIBRARIAN,), S.PENDING_PO)],
        S.PENDING_PO: [T('make_po', 'Make Purchase Order', (R.BURSAR,), S.PENDING_MANAGER), _reject(R.BURSAR)],
        **_TAIL,
        S.DISPATCHED: [T('receive', 'Receive, give each book a code', (R.LIBRARIAN,), S.COMPLETED)],
    },
    'OTHER': {
        S.PENDING_APPROVAL: [T('approve', 'Approve', (R.ACADEMIC_MASTER, R.HEAD_MASTER), S.PENDING_LIBRARIAN), _reject(R.ACADEMIC_MASTER, R.HEAD_MASTER)],
        S.PENDING_LIBRARIAN: [T('forward', 'Pass to Central Administration', (R.LIBRARIAN,), S.PENDING_BURSAR)],
        S.PENDING_BURSAR: [T('forward', 'Pass to Manager', (R.BURSAR,), S.PENDING_MANAGER), _reject(R.BURSAR)],
        **_TAIL,
        S.DISPATCHED: [T('receive', 'Receive into the school store', (R.LIBRARIAN,), S.COMPLETED)],
    },
}

INITIAL_STATUS = {'BOOKS': S.PENDING_ACADEMIC, 'OTHER': S.PENDING_APPROVAL}

# Roles that act inside a school and must belong to the request's branch.
_SCHOOL = {R.HEAD_MASTER, R.ACADEMIC_MASTER, R.LIBRARIAN, R.STAFF}
# Which school role has to act for each status, used for "waiting on" labels.
WAITING_ON = {
    S.PENDING_ACADEMIC: 'Academic Master', S.PENDING_HEAD: 'Head Master', S.PENDING_APPROVAL: 'Academic / Head Master',
    S.PENDING_REQUISITION: 'Librarian', S.PENDING_LIBRARIAN: 'Librarian', S.PENDING_PO: 'Bursar',
    S.PENDING_BURSAR: 'Bursar', S.PENDING_MANAGER: 'Manager', S.PENDING_ORDER: 'Storekeeper',
    S.ORDERED: 'Storekeeper (delivery)', S.DELIVERED: 'Requestor (verify)', S.VERIFIED: 'Bursar (pay)',
    S.PAID: 'Storekeeper (dispatch)', S.DISPATCHED: 'Librarian (receive)', S.COMPLETED: '', S.REJECTED: '',
}


def can_act(user, req, t: T) -> bool:
    if user.role not in t.roles:
        return False
    if t.requestor_only and req.requestor_id != user.id:
        return False
    if user.role in _SCHOOL and req.branch_id not in user.branch_ids():
        return False
    return True


def available_actions(user, req):
    return [t for t in TRANSITIONS[req.kind].get(req.status, []) if can_act(user, req, t)]
