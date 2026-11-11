import json
import time
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from django.contrib.auth import get_user_model
from .models import Room, Message
from .serializers import MessageSerializer
from .middleware import is_room_member

User = get_user_model()

MAX_LEN = 4000
RATE_LIMIT = 10
RATE_WINDOW = 10


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.group_name = f"chat_{self.room_id}"
        user = self.scope["user"]

        if not user.is_authenticated:
            await self.close(code=4401)
            return

        if not await is_room_member(user.id, self.room_id):
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name, self.channel_name
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        if data.get("type") == "ping":
            await self.send(json.dumps({"type": "pong"}))
            return

        if data.get("type") == "typing":
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "typing.event",
                    "user": str(self.scope["user"].id),
                },
            )
            return

        content = (data.get("content") or "").strip()
        if not content:
            return
        if len(content) > MAX_LEN:
            await self.send(json.dumps({"type": "error", "code": "too_long"}))
            return

        user = self.scope["user"]
        if not await self.check_rate_limit(user.id):
            await self.send(json.dumps({"type": "error", "code": "rate_limited"}))
            return

        client_id = data.get("client_id", "")
        msg = await self.create_message(self.room_id, user.id, content, client_id)

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat.message",
                "message": MessageSerializer(msg).data,
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))

    async def typing_event(self, event):
        await self.send(
            text_data=json.dumps({"type": "typing", "user": event["user"]})
        )

    @database_sync_to_async
    def check_rate_limit(self, user_id):
        key = f"rl:msg:{user_id}"
        now = int(time.time() * 1000)
        pipe = cache._cache.pipeline() if hasattr(cache, "_cache") else None
        # Используем Redis напрямую через Django cache
        from django.core.cache import cache as django_cache
        # Simple sliding window через sorted set
        import redis
        from django.conf import settings
        r = redis.from_url(settings.CACHES["default"]["LOCATION"])
        pipe = r.pipeline()
        pipe.zremrangebyscore(key, 0, now - RATE_WINDOW * 1000)
        pipe.zadd(key, {f"{now}:{user_id}": now})
        pipe.zcard(key)
        pipe.expire(key, RATE_WINDOW + 1)
        _, _, count, _ = pipe.execute()
        return count <= RATE_LIMIT

    @database_sync_to_async
    def create_message(self, room_id, user_id, content, client_id=""):
        user = User.objects.get(id=user_id)
        return Message.objects.create(
            room_id=room_id, author=user, content=content, client_id=client_id
        )