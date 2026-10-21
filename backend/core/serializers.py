from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import AuditLog, Branch, CENTRAL_ROLES, Role, User


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ['id', 'name', 'code', 'type']


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    role_label = serializers.CharField(source='get_role_display', read_only=True)
    branch_names = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'password', 'role', 'role_label',
                  'branches', 'branch_names', 'is_active']

    def get_branch_names(self, obj):
        return [b.name for b in obj.branches.all()]

    def validate_password(self, value):
        validate_password(value)   # Django's rules: length, not too common, not all digits
        return value

    def validate(self, data):
        role = data.get('role', getattr(self.instance, 'role', None))
        branches = data.get('branches', None)
        if branches is None and self.instance:
            branches = list(self.instance.branches.all())
        if role == Role.PARENT and not self.context.get('allow_parent'):
            raise serializers.ValidationError('Parent logins are created from the student\'s guardian record.')
        if role in CENTRAL_ROLES and branches:
            raise serializers.ValidationError('Central Administration roles cannot be tied to a school branch.')
        if role not in CENTRAL_ROLES and not branches:
            raise serializers.ValidationError('School roles need at least one branch.')
        if not self.instance and not data.get('password'):
            raise serializers.ValidationError({'password': 'Password is required.'})
        return data

    def create(self, validated):
        branches = validated.pop('branches', [])
        password = validated.pop('password')
        user = User.objects.create_user(password=password, **validated)
        user.branches.set(branches)
        return user

    def update(self, instance, validated):
        password = validated.pop('password', None)
        branches = validated.pop('branches', None)
        for k, v in validated.items():
            setattr(instance, k, v)
        if password:
            instance.set_password(password)
        instance.save()
        if branches is not None:
            instance.branches.set(branches)
        return instance


class LoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data


class AuditSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.full_name', default='system', read_only=True)
    branch_name = serializers.CharField(source='branch.name', default=None, read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'actor_name', 'action', 'entity', 'entity_id', 'branch_name', 'detail', 'created_at']
