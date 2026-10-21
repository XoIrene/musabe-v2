from .models import AuditLog


def log(actor, action, obj, detail='', branch=None):
    """Write one audit row. `obj` is any model instance with a pk."""
    AuditLog.objects.create(
        actor=actor,
        action=action,
        entity=obj.__class__.__name__,
        entity_id=obj.pk,
        branch=branch or getattr(obj, 'branch', None),
        detail=detail,
    )
