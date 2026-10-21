from rest_framework import serializers

from .models import Announcement


class AnnouncementSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.full_name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', default='All schools', read_only=True)

    class Meta:
        model = Announcement
        fields = ['id', 'title', 'body', 'audience', 'branch', 'branch_name', 'author_name', 'created_at']
