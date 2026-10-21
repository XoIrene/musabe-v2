from django.contrib import admin
from .models import AuditLog, Branch, User

admin.site.register(Branch)
admin.site.register(User)
admin.site.register(AuditLog)
