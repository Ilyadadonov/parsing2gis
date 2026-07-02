from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from app.config import settings


class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        allowed = settings.allowed_ids
        if allowed and (user is None or user.id not in allowed):
            if hasattr(event, "message") and event.message:
                await event.message.answer("У вас нет доступа к этому боту.")
            elif hasattr(event, "callback_query") and event.callback_query:
                await event.callback_query.answer("У вас нет доступа к этому боту.", show_alert=True)
            return
        return await handler(event, data)
