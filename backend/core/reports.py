"""Core reports for staff and management. Every report is scoped to the viewer's schools and can be
downloaded as CSV with ?export=csv. Filters: ?branch=<id>  ?from=YYYY-MM-DD  ?to=YYYY-MM-DD."""
import csv
from collections import Counter
from datetime import date

from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import Branch, Role

R = Role
STOCK_ROLES = (R.ADMIN, R.MANAGER, R.STOREKEEPER, R.HEAD_MASTER, R.ACADEMIC_MASTER, R.LIBRARIAN)
REQUEST_ROLES = (R.ADMIN, R.MANAGER, R.HEAD_MASTER, R.ACADEMIC_MASTER, R.LIBRARIAN)
FEE_ROLES = (R.ADMIN, R.MANAGER, R.BURSAR, R.HEAD_MASTER)


def _day(value, name):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValidationError({name: 'Use the format YYYY-MM-DD.'})


def _branches(request):
    """Schools the viewer may report on, optionally narrowed by ?branch=."""
    u, qs = request.user, Branch.objects.all()
    if not u.is_central:
        qs = qs.filter(pk__in=u.branch_ids())
    if request.query_params.get('branch'):
        qs = qs.filter(pk=request.query_params['branch'])
        if not qs:
            raise NotFound('No such school.')
    return qs


def _range(request):
    return _day(request.query_params.get('from'), 'from'), _day(request.query_params.get('to'), 'to')


def _stamp(dt):
    return timezone.localtime(dt).strftime('%Y-%m-%d %H:%M') if dt else ''


# ---------------------------------------------------------------------------------------------- reports
def overdue(request):
    from inventory.models import Issue
    today = date.today()
    loans = (Issue.objects.filter(branch__in=_branches(request), copy__isnull=False, returned_at__isnull=True,
                                  due_date__lt=today).select_related('item', 'copy', 'branch', 'student__classroom'))
    rows = [[l.copy.code, l.item.name, l.borrower_name, l.student.classroom.name if l.student and l.student.classroom else '',
             l.branch.name, l.issued_at.date().isoformat(), l.due_date.isoformat(), (today - l.due_date).days]
            for l in sorted(loans, key=lambda l: l.due_date)]
    return ('Overdue book loans', ['Book code', 'Title', 'Borrower', 'Class', 'School', 'Issued', 'Due', 'Days overdue'], rows,
            {'overdue_loans': len(rows)})


def requests_report(request):
    from procurement.models import Request
    from procurement.workflow import WAITING_ON
    start, end = _range(request)
    qs = Request.objects.filter(branch__in=_branches(request)).select_related('branch', 'requestor')
    if start:
        qs = qs.filter(created_at__date__gte=start)
    if end:
        qs = qs.filter(created_at__date__lte=end)
    p = request.query_params
    if p.get('kind'):
        qs = qs.filter(kind=p['kind'])
    if p.get('status'):
        qs = qs.filter(status=p['status'])
    now, rows, counts = timezone.now(), [], Counter()
    for r in qs:
        done = r.status in ('COMPLETED', 'REJECTED')
        counts[r.status] += 1
        rows.append([r.id, r.title, r.get_kind_display(), r.branch.name, r.requestor.full_name, r.status,
                     '' if done else WAITING_ON.get(r.status, ''), r.po_number, r.supplier, _stamp(r.created_at),
                     _stamp(r.updated_at), ((r.updated_at if done else now) - r.created_at).days])
    return ('Purchase requests', ['No.', 'Title', 'Kind', 'School', 'Requested by', 'Status', 'Waiting on', 'PO', 'Supplier',
                                  'Raised', 'Last update', 'Age (days)'], rows, {'total': len(rows), **counts})


def movements(request):
    from inventory.models import Movement
    start, end = _range(request)
    qs = Movement.objects.filter(branch__in=_branches(request)).select_related('item', 'copy', 'actor', 'branch')
    if start:
        qs = qs.filter(created_at__date__gte=start)
    if end:
        qs = qs.filter(created_at__date__lte=end)
    rows = [[_stamp(m.created_at), m.branch.name, m.item.name, m.copy.code if m.copy else '', m.get_type_display(), m.quantity,
             m.reference, m.actor.full_name if m.actor else ''] for m in qs[:5000]]
    return ('Stock movements', ['When', 'School', 'Item', 'Book code', 'Type', 'Quantity', 'Reference', 'By'], rows,
            {'movements': len(rows), 'in': sum(r[5] for r in rows if r[5] > 0), 'out': -sum(r[5] for r in rows if r[5] < 0)})


def stock(request):
    from inventory.models import Item
    rows = []
    for i in Item.objects.filter(branch__in=_branches(request)).select_related('branch').order_by('branch__name', 'name'):
        n = i.on_hand
        rows.append([i.branch.name, i.name, i.get_category_display(), i.size, n, i.reorder_level, 'LOW' if n <= i.reorder_level else ''])
    return ('Stock levels', ['School', 'Item', 'Category', 'Size', 'On hand', 'Reorder level', 'Flag'], rows,
            {'items': len(rows), 'low_stock': sum(1 for r in rows if r[6])})


def fees(request):
    from fees.models import Invoice
    invoices = Invoice.objects.filter(student__branch__in=_branches(request)).select_related(
        'student__branch', 'student__classroom', 'fee').prefetch_related('payments')
    start, end = _range(request)
    if start:
        invoices = invoices.filter(created_at__date__gte=start)
    if end:
        invoices = invoices.filter(created_at__date__lte=end)
    rows, billed, paid = [], 0, 0
    for i in invoices:
        bal = i.balance
        billed, paid = billed + i.amount, paid + i.paid
        if bal > 0:
            rows.append([i.student.branch.name, i.student.classroom.name if i.student.classroom else '', i.student.admission_no,
                         i.student.full_name, i.fee.name, float(i.amount), float(i.paid), float(bal),
                         i.fee.due_date.isoformat() if i.fee.due_date else ''])
    rows.sort(key=lambda r: -r[7])
    return ('Outstanding fees', ['School', 'Class', 'Adm. no.', 'Student', 'Fee', 'Billed', 'Paid', 'Balance', 'Due'], rows,
            {'billed': float(billed), 'collected': float(paid), 'outstanding': float(billed - paid), 'students_owing': len(rows)})


REPORTS = {'overdue': (overdue, STOCK_ROLES), 'requests': (requests_report, REQUEST_ROLES), 'movements': (movements, STOCK_ROLES),
           'stock': (stock, STOCK_ROLES), 'fees': (fees, FEE_ROLES)}


def _safe(cell):
    """Stop spreadsheet programs from running a cell that starts like a formula."""
    return "'" + cell if isinstance(cell, str) and cell[:1] in ('=', '+', '-', '@', '\t', '\r') else cell


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report(request, name):
    if name not in REPORTS:
        raise NotFound('No such report.')
    build, roles = REPORTS[name]
    if request.user.role not in roles:
        raise PermissionDenied('Your role cannot see this report.')
    title, columns, rows, summary = build(request)
    if request.query_params.get('export') == 'csv':
        res = HttpResponse(content_type='text/csv; charset=utf-8')
        res['Content-Disposition'] = f'attachment; filename="musabe-{name}-{date.today().isoformat()}.csv"'
        w = csv.writer(res)
        w.writerow(columns)
        w.writerows([[_safe(c) for c in row] for row in rows])
        return res
    return Response({'name': name, 'title': title, 'columns': columns, 'rows': rows, 'summary': summary,
                     'generated': _stamp(timezone.now())})
