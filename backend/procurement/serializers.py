from rest_framework import serializers

from core.models import SCHOOL_ROLES
from . import workflow as wf
from .models import Request, RequestLine, Step


class LineSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestLine
        fields = ['id', 'name', 'category', 'quantity', 'size', 'author', 'isbn', 'unit_price']


class StepSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.full_name', default='', read_only=True)
    actor_role = serializers.CharField(source='actor.get_role_display', default='', read_only=True)

    class Meta:
        model = Step
        fields = ['id', 'action', 'from_status', 'to_status', 'actor_name', 'actor_role', 'note', 'created_at']


class RequestSerializer(serializers.ModelSerializer):
    lines = LineSerializer(many=True)
    steps = StepSerializer(many=True, read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    requestor_name = serializers.CharField(source='requestor.full_name', read_only=True)
    waiting_on = serializers.SerializerMethodField()
    actions = serializers.SerializerMethodField()

    class Meta:
        model = Request
        fields = ['id', 'kind', 'branch', 'branch_name', 'title', 'justification', 'requestor', 'requestor_name',
                  'status', 'waiting_on', 'requisition_no', 'po_number', 'supplier', 'lines', 'steps', 'actions',
                  'created_at', 'updated_at']
        read_only_fields = ['requestor', 'status', 'requisition_no', 'po_number', 'supplier']

    def get_waiting_on(self, obj):
        return wf.WAITING_ON.get(obj.status, '')

    def get_actions(self, obj):
        user = self.context['request'].user
        return [{'action': t.action, 'label': t.label, 'needs_note': t.needs_note,
                 'needs_supplier': t.needs_supplier, 'danger': t.action in ('reject', 'dispute')}
                for t in wf.available_actions(user, obj)]

    def validate(self, data):
        user = self.context['request'].user
        if user.role not in SCHOOL_ROLES:
            raise serializers.ValidationError('Requests are raised by school staff.')
        if data['branch'].id not in user.branch_ids():
            raise serializers.ValidationError({'branch': 'You do not belong to that branch.'})
        if not data.get('lines'):
            raise serializers.ValidationError({'lines': 'Add at least one item.'})
        return data
