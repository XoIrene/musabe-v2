from rest_framework import serializers

from .models import Fee, Invoice, Payment


class FeeSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    class_name = serializers.CharField(source='classroom.name', default=None, read_only=True)
    invoiced = serializers.SerializerMethodField()

    class Meta:
        model = Fee
        fields = ['id', 'branch', 'branch_name', 'name', 'amount', 'classroom', 'class_name', 'due_date', 'invoiced']

    def get_invoiced(self, obj):
        return obj.invoices.count()

    def validate(self, d):
        room, branch = d.get('classroom'), d.get('branch')
        if room and branch and room.branch_id != branch.pk:
            raise serializers.ValidationError({'classroom': 'That class belongs to a different school.'})
        if d.get('amount') is not None and d['amount'] <= 0:
            raise serializers.ValidationError({'amount': 'Must be above zero.'})
        return d


class PaymentSerializer(serializers.ModelSerializer):
    receipt_no = serializers.CharField(read_only=True)
    received_by_name = serializers.CharField(source='received_by.full_name', read_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'receipt_no', 'amount', 'method', 'reference', 'received_by_name', 'created_at']


class InvoiceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    admission_no = serializers.CharField(source='student.admission_no', read_only=True)
    branch_name = serializers.CharField(source='student.branch.name', read_only=True)
    fee_name = serializers.CharField(source='fee.name', read_only=True)
    due_date = serializers.DateField(source='fee.due_date', read_only=True)
    paid = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = ['id', 'student', 'student_name', 'admission_no', 'branch_name', 'fee', 'fee_name', 'due_date',
                  'amount', 'paid', 'balance', 'payments']
