from rest_framework import serializers

from .models import Assessment, Subject, Term


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'branch', 'name']


class TermSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = Term
        fields = ['id', 'branch', 'branch_name', 'name', 'start_date', 'end_date']

    def validate(self, d):
        if d['end_date'] < d['start_date']:
            raise serializers.ValidationError('The term cannot end before it starts.')
        return d


class AssessmentSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    class_name = serializers.CharField(source='classroom.name', read_only=True)
    term_name = serializers.CharField(source='term.name', read_only=True)
    marked = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = ['id', 'branch', 'term', 'term_name', 'subject', 'subject_name', 'classroom', 'class_name',
                  'name', 'max_score', 'date', 'marked']
        read_only_fields = ['branch']

    def get_marked(self, obj):
        return obj.marks.count()

    def validate(self, d):
        term, subject, room = d.get('term'), d.get('subject'), d.get('classroom')
        if term and subject and room and not (term.branch_id == subject.branch_id == room.branch_id):
            raise serializers.ValidationError('Term, subject and class must all belong to the same school.')
        if d.get('max_score') == 0:
            raise serializers.ValidationError({'max_score': 'Must be above zero.'})
        return d
