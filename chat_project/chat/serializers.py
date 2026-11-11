from rest_framework import serializers
from .models import Room, Message


class RoomSerializer(serializers.ModelSerializer):
    owner = serializers.StringRelatedField(read_only=True)
    members_count = serializers.IntegerField(source="members.count", read_only=True)

    class Meta:
        model = Room
        fields = ["id", "name", "owner", "members_count", "created_at"]

    def validate_name(self, value):
        qs = Room.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Комната с таким именем уже существует")
        return value


class MessageSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Message
        fields = ["id", "room", "author", "content", "client_id", "created_at"]
        read_only_fields = ["author", "created_at"]