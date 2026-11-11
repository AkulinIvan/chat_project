from channels.db import database_sync_to_async
from .models import Room


@database_sync_to_async
def is_room_member(user_id, room_id):
    return Room.objects.filter(id=room_id, members__id=user_id).exists()