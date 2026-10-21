from rest_framework import serializers

from .models import ClassRoom, Guardian, Student


class ClassRoomSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    class_teacher_name = serializers.CharField(source='class_teacher.full_name', default=None, read_only=True)
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = ClassRoom
        fields = ['id', 'branch', 'branch_name', 'name', 'class_teacher', 'class_teacher_name', 'student_count']

    def get_student_count(self, obj):
        return obj.students.filter(status='ACTIVE').count()

    def validate(self, data):
        teacher, branch = data.get('class_teacher'), data.get('branch') or getattr(self.instance, 'branch', None)
        if teacher and (teacher.is_central or branch.pk not in teacher.branch_ids()):
            raise serializers.ValidationError({'class_teacher': 'The class teacher must be staff of this school.'})
        return data


class StudentSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    class_name = serializers.CharField(source='classroom.name', default=None, read_only=True)
    guardian_names = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ['id', 'branch', 'branch_name', 'admission_no', 'full_name', 'gender', 'date_of_birth',
                  'classroom', 'class_name', 'status', 'guardian_names']

    def get_guardian_names(self, obj):
        return [g.full_name for g in obj.guardians.all()]

    def validate(self, data):
        room = data.get('classroom')
        branch = data.get('branch') or getattr(self.instance, 'branch', None)
        if room and branch and room.branch_id != branch.pk:
            raise serializers.ValidationError({'classroom': 'That class belongs to a different school.'})
        return data


class GuardianSerializer(serializers.ModelSerializer):
    student_names = serializers.SerializerMethodField()
    has_login = serializers.SerializerMethodField()

    class Meta:
        model = Guardian
        fields = ['id', 'full_name', 'phone', 'email', 'relationship', 'students', 'student_names', 'has_login']

    def get_student_names(self, obj):
        return [s.full_name for s in obj.students.all()]

    def get_has_login(self, obj):
        return obj.user_id is not None
