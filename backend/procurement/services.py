from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from core import audit
from inventory.models import BookCopy, Category, Item, Movement

from . import workflow as wf
from .models import Request, Step


@transaction.atomic
def create_request(user, branch, kind, title, justification, lines):
    req = Request.objects.create(branch=branch, kind=kind, title=title, justification=justification,
                                 requestor=user, status=wf.INITIAL_STATUS[kind])
    for line in lines:
        if kind == Request.Kind.BOOKS:
            line['category'] = Category.BOOK
        elif line.get('category') == Category.BOOK:
            raise ValidationError('Books must use the book-buying request.')
        req.lines.create(**line)
    Step.objects.create(request=req, action='create', from_status='', to_status=req.status, actor=user)
    audit.log(user, 'request.created', req, f'{kind}: {title}')
    return req


@transaction.atomic
def perform(user, req, action, note='', supplier=''):
    """Apply one workflow action. All role/branch/requestor rules live in workflow.can_act."""
    req = Request.objects.select_for_update().get(pk=req.pk)
    t = next((t for t in wf.TRANSITIONS[req.kind].get(req.status, []) if t.action == action), None)
    if t is None:
        raise ValidationError(f'"{action}" is not possible while the request is {req.status}.')
    if not wf.can_act(user, req, t):
        raise PermissionDenied('Your role cannot do this step on this request.')
    if t.needs_note and not note.strip():
        raise ValidationError({'note': 'A note is required for this step.'})
    if t.needs_supplier:
        if not supplier.strip():
            raise ValidationError({'supplier': 'Supplier name is required.'})
        req.supplier = supplier.strip()

    if action == 'submit_requisition':
        req.requisition_no = f'REQ-{req.pk:05d}'
    elif action == 'make_po':
        req.po_number = f'PO-{req.pk:05d}'

    old, req.status = req.status, t.to
    req.save()
    Step.objects.create(request=req, action=action, from_status=old, to_status=t.to, actor=user, note=note)
    audit.log(user, f'request.{action}', req, f'{old} -> {t.to}. {note}'.strip())

    if action == 'receive':
        _receive_into_store(user, req)
    return req


def _receive_into_store(user, req):
    """Librarian takes delivery into the school: books get a unique code each, other items add to stock."""
    for line in req.lines.all():
        item, _ = Item.objects.get_or_create(
            branch=req.branch, name=line.name, category=line.category, size=line.size,
            defaults={'author': line.author, 'isbn': line.isbn})
        if line.category == Category.BOOK:
            for code in BookCopy.next_codes(item, line.quantity):
                copy = BookCopy.objects.create(item=item, branch=req.branch, code=code)
                Movement.objects.create(branch=req.branch, item=item, copy=copy, type=Movement.Type.IN_PURCHASE,
                                        quantity=1, reference=req.po_number, actor=user)
        else:
            item.quantity += line.quantity
            item.save(update_fields=['quantity'])
            Movement.objects.create(branch=req.branch, item=item, type=Movement.Type.IN_PURCHASE,
                                    quantity=line.quantity, reference=req.po_number, actor=user)
