from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class Role(models.TextChoices):
    # Central Administration
    ADMIN = 'ADMIN', 'Admin'
    MANAGER = 'MANAGER', 'Manager'
    BURSAR = 'BURSAR', 'Bursar'
    STOREKEEPER = 'STOREKEEPER', 'Storekeeper'
    # Inside a school
    HEAD_MASTER = 'HEAD_MASTER', 'Head Master / Headmistress'
    ACADEMIC_MASTER = 'ACADEMIC_MASTER', 'Academic Master'
    LIBRARIAN = 'LIBRARIAN', 'Librarian'
    STAFF = 'STAFF', 'Requesting Staff'
    # Outside the school staff (Version 1.1): sees only their own children
    PARENT = 'PARENT', 'Parent / Guardian'


CENTRAL_ROLES = {Role.ADMIN, Role.MANAGER, Role.BURSAR, Role.STOREKEEPER}
SCHOOL_ROLES = {Role.HEAD_MASTER, Role.ACADEMIC_MASTER, Role.LIBRARIAN, Role.STAFF}


class Branch(models.Model):
    class Type(models.TextChoices):
        PRIMARY = 'PRIMARY', 'Primary'
        SECONDARY = 'SECONDARY', 'Secondary'

    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=10, unique=True)  # used in book codes, e.g. NPS-0001-003
    type = models.CharField(max_length=10, choices=Type.choices)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError('Email is required')
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('role', Role.ADMIN)
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STAFF)
    # Central roles have no branches; school roles belong to one or several.
    branches = models.ManyToManyField(Branch, blank=True, related_name='staff')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']
    objects = UserManager()

    @property
    def is_central(self):
        return self.role in CENTRAL_ROLES

    def branch_ids(self):
        return list(self.branches.values_list('id', flat=True))

    def __str__(self):
        return f'{self.full_name} ({self.get_role_display()})'


class AuditLog(models.Model):
    """Append-only record of every request, approval, receipt and issue."""
    actor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='+')
    action = models.CharField(max_length=60)
    entity = models.CharField(max_length=60)
    entity_id = models.PositiveIntegerField()
    branch = models.ForeignKey(Branch, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
