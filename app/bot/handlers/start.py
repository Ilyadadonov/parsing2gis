from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from app.bot.keyboards import cities_keyboard
from app.db import async_session
from app.db.repository import UserRepo

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    async with async_session() as session:
        await UserRepo(session).get_or_create(
            user_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
        )
    await message.answer(
        "Привет! Я собираю базы потенциальных партнёров из 2ГИС.\n\n"
        "Введите название города текстом или выберите из списка:",
        reply_markup=cities_keyboard(),
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Доступные команды:\n"
        "/start — начать\n"
        "/export <город> — выгрузить сохранённую базу без повторного сбора\n\n"
        "Или просто напишите название города — бот начнёт сбор."
    )
