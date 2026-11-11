from django.conf import settings
from django.db import models


class Room(models.Model):
    name = models.CharField(max_length=255, unique=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_rooms"
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="rooms", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Message(models.Model):
    room = models.ForeignKey(Room, related_name="messages", on_delete=models.CASCADE)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messages"
    )
    content = models.TextField()
    client_id = models.CharField(max_length=64, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["room", "-created_at"])]

    def __str__(self):
        return f"{self.author}: {self.content[:40]}"