from django.contrib import admin
from .models import Room, Message


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "owner", "created_at"]
    search_fields = ["name"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "room", "author", "content_preview", "created_at"]
    list_filter = ["room", "created_at"]
    search_fields = ["content"]

    def content_preview(self, obj):
        return obj.content[:60]
    content_preview.short_description = "Содержимое"