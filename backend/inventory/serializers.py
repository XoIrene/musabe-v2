from rest_framework import serializers

from .models import BookCopy, Issue, Item, Movement, ParentContribution, WriteOff


class ItemSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    on_hand = serializers.IntegerField(read_only=True)
    total_copies = serializers.SerializerMethodField()
    low = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = ['id', 'branch', 'branch_name', 'name', 'category', 'size', 'author', 'isbn',
                  'on_hand', 'total_copies', 'reorder_level', 'low']
        read_only_fields = ['quantity']

    def get_total_copies(self, obj):
        return obj.copies.exclude(status=BookCopy.Status.WRITTEN_OFF).count() if obj.category == 'BOOK' else None

    def get_low(self, obj):
        return obj.on_hand <= obj.reorder_level


class CopySerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    borrower = serializers.SerializerMethodField()

    class Meta:
        model = BookCopy
        fields = ['id', 'code', 'item', 'item_name', 'branch', 'status', 'borrower']

    def get_borrower(self, obj):
        loan = obj.issues.filter(returned_at__isnull=True).first()
        return loan.borrower_name if loan else None


class IssueSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    code = serializers.CharField(source='copy.code', default=None, read_only=True)
    issued_by_name = serializers.CharField(source='issued_by.full_name', read_only=True)
    admission_no = serializers.CharField(source='student.admission_no', default=None, read_only=True)

    class Meta:
        model = Issue
        fields = ['id', 'branch', 'item', 'item_name', 'copy', 'code', 'quantity', 'borrower_name', 'borrower_type',
                  'student', 'admission_no',
                  'issued_by_name', 'issued_at', 'due_date', 'returned_at', 'note']


class WriteOffSerializer(serializers.ModelSerializer):
    code = serializers.CharField(source='copy.code', read_only=True)
    item_name = serializers.CharField(source='copy.item.name', read_only=True)
    reported_by_name = serializers.CharField(source='reported_by.full_name', read_only=True)
    decided_by_name = serializers.CharField(source='decided_by.full_name', default=None, read_only=True)

    class Meta:
        model = WriteOff
        fields = ['id', 'branch', 'copy', 'code', 'item_name', 'kind', 'reason', 'status', 'reported_by_name',
                  'reported_at', 'decided_by_name', 'decided_at', 'decision_note']


class ContributionSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)

    class Meta:
        model = ParentContribution
        fields = ['id', 'branch', 'item', 'item_name', 'quantity', 'parent_name', 'created_at']


class MovementSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    code = serializers.CharField(source='copy.code', default=None, read_only=True)
    actor_name = serializers.CharField(source='actor.full_name', default='', read_only=True)
    type_label = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        model = Movement
        fields = ['id', 'branch', 'item', 'item_name', 'code', 'type', 'type_label', 'quantity', 'reference',
                  'actor_name', 'created_at']
