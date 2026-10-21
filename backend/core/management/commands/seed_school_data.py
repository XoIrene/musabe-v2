from datetime import date, timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand

from academics.models import Subject, Term
from announcements.models import Announcement
from core.models import Branch, Role, User
from fees.models import Fee
from students.models import ClassRoom, Guardian, Student
from transport.models import Route

PASSWORD = 'musabe123'
ROOMS = {'NPS': ['Standard 1A', 'Standard 4A'], 'GSS': ['Form 1 Blue', 'Form 2 Blue'], 'BSS': ['Form 1 Red', 'Form 2 Red']}
SUBJECTS = {'PRIMARY': ['Kiswahili', 'English', 'Mathematics', 'Science', 'Social Studies'],
            'SECONDARY': ['Kiswahili', 'English', 'Mathematics', 'Biology', 'Chemistry', 'Physics', 'Geography', 'History']}
NAMES = {'F': ['Neema', 'Amina', 'Zawadi', 'Rehema', 'Upendo', 'Grace'], 'M': ['Juma', 'Baraka', 'Elias', 'Joel', 'Hamisi', 'Daudi']}


class Command(BaseCommand):
    help = 'Demo data for Version 1.1 and later modules (run seed_demo first). Parent login: parent@musabe.test / musabe123'

    def add_arguments(self, parser):
        parser.add_argument('--password', default=PASSWORD, help='Password for the demo parent login')

    def handle(self, *args, **opts):
        password = opts['password']
        if not Branch.objects.exists():
            call_command('seed_demo', verbosity=0, password=password)
        today = date.today()
        for b in Branch.objects.all():
            for name in SUBJECTS[b.type]:
                Subject.objects.get_or_create(branch=b, name=name)
            Term.objects.get_or_create(branch=b, name=f'Term {1 + (today.month > 6)} {today.year}', defaults={
                'start_date': date(today.year, 1 if today.month <= 6 else 7, 6), 'end_date': date(today.year, 6 if today.month <= 6 else 12, 5)})
            teacher = User.objects.filter(role=Role.STAFF, branches=b).first()
            gender = 'F' if b.code == 'GSS' else 'M' if b.code == 'BSS' else None
            for i, room_name in enumerate(ROOMS[b.code]):
                room, _ = ClassRoom.objects.get_or_create(branch=b, name=room_name, defaults={'class_teacher': teacher if i == 0 else None})
                for n in range(6):
                    g = gender or ('F' if n % 2 else 'M')
                    Student.objects.get_or_create(branch=b, admission_no=f'{b.code}/{today.year}/{i * 6 + n + 1:03d}', defaults={
                        'full_name': f'{NAMES[g][n]} {["Mwakyusa", "Kisanga", "Massawe", "Lyimo"][(n + i) % 4]}', 'gender': g, 'classroom': room})
            Fee.objects.get_or_create(branch=b, name='School fees', classroom=None, defaults={'amount': 400000 if b.type == 'PRIMARY' else 650000})
            Route.objects.get_or_create(branch=b, name='Buhongwa - Igoma', defaults={'vehicle': 'T 123 ABC', 'driver_name': 'Mzee Omari',
                                        'driver_phone': '0712 000 111', 'capacity': 25, 'stops': 'Buhongwa\nNyegezi\nIgoma'})
        kids = list(Student.objects.filter(branch__code='NPS')[:2])
        g, _ = Guardian.objects.get_or_create(full_name='Mama Neema', defaults={'phone': '0713 222 333', 'email': 'parent@musabe.test'})
        g.students.set(kids)
        if not g.user_id:
            u = User.objects.create_user('parent@musabe.test', password, full_name=g.full_name, role=Role.PARENT)
            u.branches.set({k.branch for k in kids})
            g.user = u
            g.save()
        admin = User.objects.get(email='admin@musabe.test')
        Announcement.objects.get_or_create(title='Welcome to the Musabe Schools system', defaults={
            'body': 'Requests, stock, students, fees and transport are now managed in one place.', 'author': admin})
        self.stdout.write(self.style.SUCCESS('School data seeded. Parent login: parent@musabe.test'))
