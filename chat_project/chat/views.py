from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Room, Message
from .serializers import RoomSerializer, MessageSerializer


class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Room.objects.filter(members=self.request.user).distinct()

    def perform_create(self, serializer):
        room = serializer.save(owner=self.request.user)
        room.members.add(self.request.user)

    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        room = get_object_or_404(Room, pk=pk)
        room.members.add(request.user)
        return Response({"status": "joined", "room_id": room.id})

    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        room = get_object_or_404(Room, pk=pk, members=request.user)
        room.members.remove(request.user)
        return Response({"status": "left"})


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        room_id = self.request.query_params.get("room")
        if not room_id:
            return Message.objects.none()

        qs = (
            Message.objects.filter(
                room_id=room_id, room__members=self.request.user
            )
            .select_related("author")
            .order_by("-created_at")
        )

        before = self.request.query_params.get("before")
        if before:
            qs = qs.filter(id__lt=before)

        return list(reversed(qs[:50]))

    def perform_create(self, serializer):
        room = serializer.validated_data["room"]
        if not room.members.filter(id=self.request.user.id).exists():
            raise permissions.PermissionDenied("Не участник комнаты")
        serializer.save(author=self.request.user)

    def perform_destroy(self, instance):
        room = instance.room
        if instance.author != self.request.user and room.owner != self.request.user:
            raise permissions.PermissionDenied("Нет прав на удаление")
        instance.delete()