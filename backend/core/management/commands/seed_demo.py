from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import Branch, Role, User

PASSWORD = 'musabe123'

CENTRAL = [('admin@musabe.test', 'Amani Admin', Role.ADMIN), ('manager@musabe.test', 'Mariam Manager', Role.MANAGER),
           ('bursar@musabe.test', 'Baraka Bursar', Role.BURSAR), ('store@musabe.test', 'Salma Storekeeper', Role.STOREKEEPER)]
BRANCHES = [('Nursery & Primary', 'NPS', 'PRIMARY', 'primary'), ('Girls Secondary', 'GSS', 'SECONDARY', 'girls'),
            ('Boys Secondary', 'BSS', 'SECONDARY', 'boys')]
SCHOOL = [(Role.HEAD_MASTER, 'head'), (Role.ACADEMIC_MASTER, 'academic'), (Role.LIBRARIAN, 'librarian'), (Role.STAFF, 'teacher')]


class Command(BaseCommand):
    help = 'Create demo branches and one user per role (password: musabe123).'

    def add_arguments(self, parser):
        parser.add_argument('--password', default=PASSWORD, help='Password for every demo account (default is public: demo only!)')

    def handle(self, *args, **opts):
        global PASSWORD
        PASSWORD = opts['password']
        if PASSWORD == 'musabe123' and not settings.TESTING:
            self.stderr.write('WARNING: demo accounts use the public password "musabe123". Never seed this on a live system; pass --password.')
        for email, name, role in CENTRAL:
            User.objects.update_or_create(email=email, defaults={'full_name': name, 'role': role, 'is_staff': role == Role.ADMIN,
                                                                  'is_superuser': role == Role.ADMIN}) [0].set_password(PASSWORD)
            u = User.objects.get(email=email); u.set_password(PASSWORD); u.save()
        for name, code, typ, slug in BRANCHES:
            b, _ = Branch.objects.get_or_create(code=code, defaults={'name': name, 'type': typ})
            for role, label in SCHOOL:
                u, _ = User.objects.get_or_create(email=f'{label}.{slug}@musabe.test', defaults={
                    'full_name': f'{role.label.split(" /")[0]} - {name}', 'role': role})
                u.set_password(PASSWORD); u.save(); u.branches.set([b])
        self.stdout.write(self.style.SUCCESS(f'Seeded. Log in with e.g. admin@musabe.test / {PASSWORD}'))
