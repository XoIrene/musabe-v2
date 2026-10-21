from rest_framework import serializers

from .models import Route, TransportAssignment


class RouteSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    riders = serializers.SerializerMethodField()

    class Meta:
        model = Route
        fields = ['id', 'branch', 'branch_name', 'name', 'vehicle', 'driver_name', 'driver_phone', 'capacity',
                  'stops', 'riders']

    def get_riders(self, obj):
        return obj.assignments.count()


class AssignmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    admission_no = serializers.CharField(source='student.admission_no', read_only=True)
    route_name = serializers.CharField(source='route.name', read_only=True)

    class Meta:
        model = TransportAssignment
        fields = ['id', 'student', 'student_name', 'admission_no', 'route', 'route_name', 'pickup_point']

    def validate(self, d):
        student, route = d.get('student') or self.instance.student, d.get('route') or self.instance.route
        if student.branch_id != route.branch_id:
            raise serializers.ValidationError('The student and the route belong to different schools.')
        taken = route.assignments.exclude(pk=getattr(self.instance, 'pk', None)).count()
        if taken >= route.capacity:
            raise serializers.ValidationError({'route': 'This route is full.'})
        return d
